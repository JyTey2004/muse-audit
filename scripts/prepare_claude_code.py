"""Prepare a local, synthetic-only MCP workspace without changing host settings."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def prepare(destination):
    destination = Path(destination).absolute()
    if destination.is_symlink():
        raise ValueError("Local setup destination cannot be a symlink")
    marker = destination / "setup.json"
    if destination.exists():
        if not marker.is_file():
            raise ValueError("Existing unmanaged directory; choose a new destination")
        saved = json.loads(marker.read_text())
        if saved.get("project") != str(ROOT) or saved.get("kind") != "muse-audit-synthetic":
            raise ValueError("Existing setup belongs to a different project")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".claude-setup-", dir=destination.parent) as tmp:
            staging = Path(tmp) / "setup"
            staging.mkdir()
            shutil.copytree(ROOT / "examples", staging / "sandbox" / "inputs")
            originals = {
                str(p.relative_to(ROOT / "examples")): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "examples").rglob("*")) if p.is_file()
            }
            (staging / "setup.json").write_text(json.dumps({
                "kind": "muse-audit-synthetic", "project": str(ROOT),
                "fixture_sha256": originals,
                "consumer_muse": "NOT_RUN / UNTESTED",
            }, indent=2) + "\n")
            staging.rename(destination)
    python = ROOT / ".venv" / "bin" / "python"
    if not python.is_file():
        raise ValueError("Set up .venv first; see QUICKSTART-MAC.md")
    sandbox = destination / "sandbox"
    if sandbox.is_symlink() or not sandbox.is_dir():
        raise ValueError("Expected the existing synthetic sandbox; no replacement was made")
    config = {
        "mcpServers": {
            "muse_audit": {
                "type": "stdio",
                "command": str(python),
                "args": [str(ROOT / "run_mcp.py"), "--workspace", str(sandbox)],
            }
        }
    }
    config_path = destination / "mcp.json"
    if config_path.is_symlink():
        raise ValueError("Local MCP config cannot be a symlink")
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return {"config": str(config_path), "workspace": str(sandbox)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".local" / "claude-code")
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), indent=2))


if __name__ == "__main__":
    main()
