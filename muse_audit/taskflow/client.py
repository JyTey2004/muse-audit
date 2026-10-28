"""Client that calls the read-only taskflow review through a real subprocess, then writes outputs itself.

Daily-use tasks must use this path, not a direct Python review presented
as a server review. The server stays strictly read-only: it never
writes a receipt or a snapshot. This client retains method and result
observations, then, outside the server process, writes an immutable
readable receipt, the machine receipt, the observations, and a byte
snapshot of the reviewed artifact into a fresh output directory.
"""

import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..io import canonical, read_json
from .receipt import render_readable_receipt
from .tasks import (TaskBlocked, load_frozen, resolve_task, review_task,
                    _blocked_receipt, _file_problem)


def _unpack(response):
    if getattr(response, "isError", False):
        raise TaskBlocked("The verification service could not complete this check.")
    if getattr(response, "structuredContent", None) is not None:
        return response.structuredContent
    if response.content:
        return json.loads(response.content[0].text)
    raise ValueError("Server returned an empty result.")


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


async def _run_review(store_root, task_id):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    store = Path(store_root).resolve()
    resolve_task(store, task_id)
    entry = Path(__file__).resolve().parent / "run_mcp.py"
    observations = []
    stderr_path = None
    params = StdioServerParameters(
        command=sys.executable,
        args=["-B", str(entry), "--workspace", str(store)],
        env={},
        cwd=str(Path(__file__).resolve().parents[2]),
    )
    # Stderr is captured to a temporary file only for debugging; it is
    # not part of the readable receipt.
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as errlog_file:
        stderr_path = errlog_file.name
        with open(stderr_path, "w") as errlog:
            async with stdio_client(params, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as client:
                    initialized = await client.initialize()
                    observations.append(
                        {"method": "initialize", "result": initialized.model_dump(mode="json")}
                    )
                    tools = await client.list_tools()
                    observations.append({"method": "tools/list", "result": tools.model_dump(mode="json")})
                    if sorted(t.name for t in tools.tools) != ["taskflow_capabilities", "taskflow_recheck", "taskflow_review"] or not all(t.annotations and t.annotations.readOnlyHint for t in tools.tools):
                        raise TaskBlocked("The verification service exposes an unexpected tool inventory.")
                    capabilities = await client.call_tool("taskflow_capabilities", {})
                    observations.append(
                        {
                            "method": "tools/call",
                            "params": {"name": "taskflow_capabilities", "arguments": {}},
                            "result": _unpack(capabilities),
                            "raw_result": capabilities.model_dump(mode="json"),
                        }
                    )
                    review = await client.call_tool("taskflow_review", {"task_id": task_id})
                    receipt = _unpack(review)
                    observations.append(
                        {
                            "method": "tools/call",
                            "params": {"name": "taskflow_review", "arguments": {"task_id": task_id}},
                            "result": receipt,
                            "raw_result": review.model_dump(mode="json"),
                        }
                    )
        observations.append({"method": "server-stderr", "diagnostic": True,
                             "text": Path(stderr_path).read_text(encoding="utf-8")})
    return receipt, observations


def mcp_review(store_root, task_id, output_dir):
    """Run a real server review, then write immutable outputs outside the server.

    output_dir must be a new directory. It is created by this function;
    an existing directory is refused so prior evidence is never overwritten.
    Returns a dict with the receipt, the output directory, and the
    observation count, kept out of the readable receipt.
    """
    store = Path(store_root).resolve()
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise ValueError("Output must be a NEW directory; no overwrite is permitted.")
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt, observations = asyncio.run(asyncio.wait_for(_run_review(store, task_id), 45))
    task_dir = resolve_task(store, task_id)
    # Revalidate the complete binding after the server returns. A source,
    # contract, dependency or implementation change cannot be hidden by an
    # unchanged artifact. This guard is outside the read-only MCP server.
    current = review_task(store, task_id, write_outputs=False)
    semantic_keys = ('receipt_schema', 'task_id', 'title', 'request', 'binding',
                     'checks', 'counts', 'decision', 'coverage')
    export_problem = None
    if canonical({k: current.get(k) for k in semantic_keys}) != canonical({k: receipt.get(k) for k in semantic_keys}):
        export_problem = "Inputs changed after verification. Restore the original input or request a new check."
    artifact_data = None
    artifact_path = None
    if not export_problem and receipt.get('decision') != 'BLOCKED':
        frozen = load_frozen(task_dir)
        relative = frozen['artifact']['relative_path']
        export_problem = _file_problem(task_dir, relative)
        if not export_problem:
            artifact_path = task_dir / relative
            artifact_data = artifact_path.read_bytes()
            if receipt.get('binding', {}).get('artifact', {}).get('sha256') != _sha_bytes(artifact_data):
                export_problem = "The delivered file changed after verification. Request a fresh check."
    if export_problem:
        # The original service response remains unchanged in observations.
        receipt = _blocked_receipt(task_id, export_problem, False)
        receipt['execution'] = {'origin': 'client_export_guard', 'server_response_retained': True}
        artifact_data = None
    output.mkdir()
    receipt_path = output / "receipt.json"
    readable_path = output / "receipt.md"
    observations_path = output / "observations.json"
    snapshot_path = output / f"artifact-snapshot{artifact_path.suffix}" if artifact_data is not None else None
    receipt_path.write_text(canonical(receipt) + "\n", encoding="utf-8")
    readable_path.write_text(render_readable_receipt(receipt), encoding="utf-8")
    observations_path.write_text(canonical({"observations": observations}) + "\n", encoding="utf-8")
    stderr_file = output / 'server-stderr.txt'
    stderr_file.write_text('\n'.join(o.get('text', '') for o in observations if o.get('method') == 'server-stderr'), encoding='utf-8')
    retained = [receipt_path, readable_path, observations_path, stderr_file]
    if snapshot_path is not None:
        snapshot_path.write_bytes(artifact_data)
        retained.append(snapshot_path)
    for path in retained:
        try:
            path.chmod(0o444)
        except OSError:
            pass
    return {
        "task_id": task_id,
        "output_dir": str(output),
        "receipt": receipt,
        "observation_count": len(observations),
    }


def mcp_review_timestamped(store_root, task_id, parent_dir=None):
    """Create a fresh timestamped output directory, then run mcp_review into it."""
    parent = Path(parent_dir) if parent_dir is not None else Path(store_root) / "tasks" / task_id / "mcp-outputs"
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = parent / stamp
    suffix = 0
    while target.exists():
        suffix += 1
        target = parent / f"{stamp}-{suffix}"
    return mcp_review(store_root, task_id, target)
