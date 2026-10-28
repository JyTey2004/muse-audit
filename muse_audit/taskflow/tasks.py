"""Prepare, review, recheck, and repair for fresh tasks.

Rules enforced here, not in prose:

- Prepare freezes the request, the model-interpreted checklist, and the
  selected source bytes before any deliverable is generated. An ordinary
  drafting request already authorizes its explicit requirements, so
  prepare does not demand a second technical approval.
- Model-interpreted coverage is never claimed to be independently
  complete. Only listed requirements are checked.
- Reviews resolve only task IDs inside the launch-scoped store. A task
  ID outside that store, a traversal path, or a missing task is blocked.
- Frozen bindings are verified before and after checking. Tampering,
  missing sources, a missing artifact, a symlink, or an oversized input
  blocks passing.
- Changed artifact, frozen-hash record, or checker bytes stale old
  assurance on recheck. Checker code changed after process start blocks
  review instead of binding new disk bytes while running old code.
- Prior outputs and receipts are never overwritten. Each review writes
  a new timestamped output directory with a byte snapshot of the
  reviewed artifact, so later edits cannot erase the older output.
- Repairs create a new task copy under the original requirements, only
  with an explicitly reviewed repair scope, and only for sources that
  scope explicitly adopts. They never edit the original task, artifact,
  or receipt.
- Dynamic tasks never inherit old budget numbers, cells, caps, artifact
  hashes, or verdicts. Every fresh task starts from its own frozen
  record.
"""

import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .. import core as kernel
from .. import task_backend  # Captures loaded project sources at process load.
from ..io import canonical, digest, read_json
from . import checks as checkers
from .receipt import render_readable_receipt

TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")
RESERVED_NAMES = {"frozen.json", "frozen.sha256", "receipt.json", "receipt.md", "repair-plan.json"}
MAX_FILE = 5_000_000


class TaskBlocked(ValueError):
    """A task cannot be accepted because a bound input is missing or changed."""


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _sha_file(path):
    return _sha_bytes(Path(path).read_bytes())


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def checker_identity():
    """Reuse the existing full project identity: all project Python, dependency declarations, and runtime package versions."""
    from ..task_backend.identity import implementation

    return implementation()


def checker_hash():
    try:
        return digest(checker_identity())
    except Exception:
        return None


def _checker_changed():
    try:
        identity = checker_identity()
    except Exception:
        return True, None
    return bool(identity.get("source_changed_since_process_start")), identity


def _symlink_chain(task_dir, relative_path):
    """True if any component of a task-internal path, including its parent dirs, is a symlink."""
    current = Path(task_dir)
    for part in Path(relative_path).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _file_problem(task_dir, relative_path):
    """Return a problem string for a task-internal file, or None if it is a plain readable file within the size limit."""
    if _symlink_chain(task_dir, relative_path):
        return "Symlinked input is refused."
    path = Path(task_dir) / relative_path
    if not path.is_file():
        return "Input file is missing."
    try:
        if path.stat().st_size > MAX_FILE:
            return "Input exceeds the 5 MB limit."
    except OSError as exc:
        return f"Input cannot be read: {exc}"
    return None


def resolve_task(store_root, task_id):
    if not isinstance(task_id, str) or not TASK_ID_RE.fullmatch(task_id):
        raise TaskBlocked("Task ID is not authorized for this store.")
    store = Path(store_root).resolve()
    tasks_dir = store / "tasks"
    if tasks_dir.is_symlink():
        raise TaskBlocked("Task store is not authorized.")
    task_dir = tasks_dir / task_id
    if task_dir.is_symlink() or not task_dir.is_dir():
        raise TaskBlocked("Task is not found under this store.")
    resolved = task_dir.resolve()
    if not resolved.is_relative_to(store):
        raise TaskBlocked("Task is outside this store.")
    return resolved


def _validate_requirements(requirements):
    if not isinstance(requirements, list) or not 1 <= len(requirements) <= 100:
        raise ValueError("Provide 1 through 100 explicit requirements.")
    seen = set()
    for req in requirements:
        if not isinstance(req, dict) or set(req) != {"id", "kind", "description", "mode", "config"}:
            raise ValueError("Each requirement needs id, kind, description, mode, and config.")
        if not isinstance(req["id"], str) or not req["id"] or req["id"] in seen:
            raise ValueError("Requirement IDs must be distinct and nonempty.")
        if not isinstance(req["kind"], str) or not req["kind"]:
            raise ValueError("Requirement kind must be nonempty text.")
        if not isinstance(req["description"], str) or not req["description"]:
            raise ValueError("Requirement description must be nonempty text.")
        if req["mode"] not in ("must_change", "must_preserve", "unknown"):
            raise ValueError("Requirement mode is not supported.")
        if not isinstance(req["config"], dict):
            raise ValueError("Requirement config must be an object.")
        seen.add(req["id"])


def prepare_task(store_root, request, requirements, sources, artifact_name, artifact_kind, title=None):
    """Freeze a fresh task before its deliverable is generated.

    sources is a list of (source_id, source_path, display_name). Source
    bytes are copied into the task, never referenced from outside it.
    """
    if not isinstance(request, str) or not request.strip() or len(request) > 10000:
        raise ValueError("Request must be bounded nonempty text.")
    _validate_requirements(requirements)
    if not isinstance(artifact_name, str) or not artifact_name:
        raise ValueError("Artifact name must be nonempty.")
    if artifact_name in RESERVED_NAMES or "/" in artifact_name or "\\" in artifact_name or artifact_name.startswith("."):
        raise ValueError("Artifact name is reserved or is not a plain file name.")
    if artifact_kind not in ("text", "markdown", "json", "csv", "xlsx", "docx"):
        raise ValueError("Artifact kind is not supported.")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 20:
        raise ValueError("Provide 1 through 20 selected sources.")
    task_id = "task-" + uuid.uuid4().hex[:16]
    store = Path(store_root).resolve()
    task_dir = store / "tasks" / task_id
    if task_dir.exists():
        raise ValueError("Fresh task ID already exists; prepare a new task.")
    (task_dir / "sources").mkdir(parents=True)
    (task_dir / "artifacts").mkdir()
    (task_dir / "outputs").mkdir()
    frozen_sources = []
    seen_ids = set()
    seen_names = set()
    for source_id, source_path, display_name in sources:
        if source_id in seen_ids:
            raise ValueError("Source IDs must be distinct.")
        seen_ids.add(source_id)
        if not isinstance(display_name, str) or not display_name or "/" in display_name or "\\" in display_name:
            raise ValueError("Source file name must be a plain file name.")
        if display_name in seen_names:
            raise ValueError("Source file names must be distinct inside the task.")
        seen_names.add(display_name)
        origin = Path(source_path)
        if origin.is_symlink() or not origin.is_file():
            raise ValueError(f"Selected source is missing: {source_id}")
        data = origin.read_bytes()
        if len(data) > MAX_FILE:
            raise ValueError("Selected source exceeds the 5 MB limit.")
        destination = task_dir / "sources" / display_name
        destination.write_bytes(data)
        frozen_sources.append(
            {
                "id": source_id,
                "name": display_name,
                "sha256": _sha_bytes(data),
                "bytes": len(data),
            }
        )
    frozen = {
        "schema_version": 1,
        "task_id": task_id,
        "title": title or request.strip().splitlines()[0][:200],
        "request": request,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requirements": requirements,
        "sources": frozen_sources,
        "artifact": {
            "name": artifact_name,
            "relative_path": f"artifacts/{artifact_name}",
            "kind": artifact_kind,
            "version": "v1",
        },
        "coverage_note": (
            "Model-interpreted checklist is not independently verified as complete. "
            "Only the listed requirements were checked."
        ),
    }
    frozen_text = canonical(frozen) + "\n"
    (task_dir / "frozen.json").write_text(frozen_text, encoding="utf-8")
    (task_dir / "frozen.sha256").write_text(_sha_bytes(frozen_text.encode("utf-8")) + "\n", encoding="utf-8")
    return {"task_id": task_id, "task_dir": str(task_dir), "frozen": frozen}


def load_frozen(task_dir):
    task_dir = Path(task_dir)
    for name in ("frozen.json", "frozen.sha256"):
        problem = _file_problem(task_dir, name)
        if problem is not None:
            raise TaskBlocked(f"Frozen task record cannot be read: {problem}")
    frozen_path = task_dir / "frozen.json"
    hash_path = task_dir / "frozen.sha256"
    frozen_text = frozen_path.read_text(encoding="utf-8")
    try:
        frozen = read_json(frozen_path)
    except (OSError, ValueError) as exc:
        raise TaskBlocked("Frozen task record cannot be parsed.") from exc
    expected = hash_path.read_text(encoding="utf-8").strip()
    if _sha_bytes(frozen_text.encode("utf-8")) != expected:
        raise TaskBlocked("Frozen task record does not match its frozen binding.")
    if not isinstance(frozen, dict) or frozen.get("schema_version") != 1:
        raise TaskBlocked("Frozen task record has an unsupported schema.")
    if frozen.get("task_id") != task_dir.name:
        raise TaskBlocked("Frozen task record does not belong to this task.")
    try:
        _validate_requirements(frozen.get("requirements"))
    except ValueError as exc:
        raise TaskBlocked("Frozen task requirements are invalid.") from exc
    return frozen


def verify_sources(task_dir, frozen):
    problems = []
    pins = {}
    for source in frozen.get("sources", []):
        relative = f"sources/{source['name']}"
        problem = _file_problem(task_dir, relative)
        if problem is not None:
            problems.append(f"Source is refused or missing: {source['id']} ({problem})")
            pins[source["id"]] = {"sha256": None, "bytes": None, "available": False}
            continue
        path = Path(task_dir) / relative
        data = path.read_bytes()
        pin = {"sha256": _sha_bytes(data), "bytes": len(data), "available": True}
        pins[source["id"]] = pin
        if pin["sha256"] != source.get("sha256") or pin["bytes"] != source.get("bytes"):
            problems.append(f"Source changed after freezing: {source['id']}")
    return problems, pins


def _blocked_check(req, reason):
    return {
        "requirement_id": req["id"],
        "status": "BLOCKED",
        "reason": reason,
        "observed": None,
        "expected": None,
        "description": req.get("description", ""),
        "mode": req.get("mode", "must_change"),
        "locations": [],
    }


def _native_job(task_dir, frozen, native_requirements):
    artifact = frozen["artifact"]
    sources = [
        {"id": source["id"], "path": f"sources/{source['name']}", "version": "v1"}
        for source in frozen["sources"]
    ]
    return {
        "schema_version": 1,
        "job_id": frozen["task_id"],
        "title": frozen["title"],
        "intent": frozen["request"],
        "contract_version": "taskflow-v1",
        "artifact": {
            "path": artifact["relative_path"],
            "version": artifact["version"],
            "kind": "xlsx_budget" if artifact["kind"] == "xlsx" else "docx_report",
        },
        "sources": sources,
        "requirements": native_requirements,
    }


def _decision(checks):
    statuses = [check["status"] for check in checks]
    if any(status == "BLOCKED" for status in statuses):
        return "BLOCKED"
    if any(status == "FAIL" for status in statuses):
        return "REVISE"
    if any(status in ("UNKNOWN", "STALE") for status in statuses):
        return "UNRESOLVED"
    return "SELECTED_CHECKS_PASS"


def _frozen_hash_file_pin(task_dir):
    relative = "frozen.sha256"
    problem = _file_problem(task_dir, relative)
    if problem is not None:
        return {"sha256": None, "bytes": None, "available": False, "recorded": None}
    path = Path(task_dir) / relative
    data = path.read_bytes()
    return {
        "sha256": _sha_bytes(data),
        "bytes": len(data),
        "available": True,
        "recorded": data.decode("utf-8", errors="replace").strip(),
    }


def _binding(task_dir, frozen, artifact_path, source_pins):
    if artifact_path is not None:
        problem = _file_problem(task_dir, frozen["artifact"]["relative_path"])
        if problem is None:
            data = Path(artifact_path).read_bytes()
            artifact_pin = {"sha256": _sha_bytes(data), "bytes": len(data), "available": True}
        else:
            artifact_pin = {"sha256": None, "bytes": None, "available": False}
    else:
        artifact_pin = {"sha256": None, "bytes": None, "available": False}
    frozen_text = (Path(task_dir) / "frozen.json").read_text(encoding="utf-8") if (Path(task_dir) / "frozen.json").is_file() else ""
    identity = None
    try:
        identity = checker_identity()
    except Exception:
        identity = None
    return {
        "frozen_sha256": _sha_bytes(frozen_text.encode("utf-8")) if frozen_text else None,
        "frozen_hash_file": _frozen_hash_file_pin(task_dir),
        "sources": source_pins,
        "artifact": artifact_pin,
        "checker_hash": digest(identity) if identity is not None else None,
        "checker_identity": identity,
    }


def _blocked_receipt(task_id, reason, write_outputs, task_dir=None):
    receipt = {
        "receipt_schema": 1,
        "task_id": task_id,
        "title": "Blocked task",
        "request": "",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "binding": {
            "frozen_sha256": None,
            "frozen_hash_file": {"sha256": None, "bytes": None, "available": False, "recorded": None},
            "sources": {},
            "artifact": {"sha256": None, "bytes": None, "available": False},
            "checker_hash": checker_hash(),
            "checker_identity": None,
        },
        "checks": [],
        "counts": {"PASS": 0, "FAIL": 0, "UNKNOWN": 0, "STALE": 0, "BLOCKED": 1},
        "decision": "BLOCKED",
        "coverage": {
            "declared_requirements": 0,
            "warning": "Only the listed requirements were checked. Model-interpreted coverage is not independently verified as complete. No global certification.",
        },
        "block_reason": reason,
    }
    if write_outputs and task_dir is not None:
        _write_outputs(task_dir, receipt, None)
    return receipt


def review_task(store_root, task_id, write_outputs=True):
    task_dir = resolve_task(store_root, task_id)
    changed, identity = _checker_changed()
    if changed:
        try:
            frozen = load_frozen(task_dir)
            checks = [
                _blocked_check(req, "Checker code changed after process start; restart is required.")
                for req in frozen["requirements"]
            ]
            receipt = {
                "receipt_schema": 1,
                "task_id": task_id,
                "title": frozen["title"],
                "request": frozen["request"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "binding": _binding(task_dir, frozen, task_dir / frozen["artifact"]["relative_path"], {}),
                "checks": checks,
                "counts": {"PASS": 0, "FAIL": 0, "UNKNOWN": 0, "STALE": 0, "BLOCKED": len(checks)},
                "decision": "BLOCKED",
                "coverage": {
                    "declared_requirements": len(frozen["requirements"]),
                    "warning": "Only the listed requirements were checked. Model-interpreted coverage is not independently verified as complete. No global certification.",
                },
                "block_reason": "Checker code changed after process start; restart is required.",
            }
        except TaskBlocked as exc:
            receipt = _blocked_receipt(task_id, str(exc), False)
        if write_outputs:
            _write_outputs(task_dir, receipt, None)
        return receipt

    try:
        frozen = load_frozen(task_dir)
    except TaskBlocked as exc:
        return _blocked_receipt(task_id, str(exc), write_outputs, task_dir)

    artifact_path = task_dir / frozen["artifact"]["relative_path"]
    artifact_problem = _file_problem(task_dir, frozen["artifact"]["relative_path"])
    source_problems, source_pins = verify_sources(task_dir, frozen)
    before = _binding(task_dir, frozen, artifact_path, source_pins)

    # Native checks go through the existing kernel once, preserving archive
    # guards, extraction coverage, and source and native preconditions.
    native_checks = {}
    native_extras = []
    artifact_kind = frozen["artifact"]["kind"]
    native_kinds_for_artifact = (
        {"xlsx.source_amount", "xlsx.sum", "xlsx.cap", "xlsx.preserve_cell"}
        if artifact_kind == "xlsx"
        else {"docx.quote", "docx.preserve_paragraph"}
        if artifact_kind == "docx"
        else set()
    )
    native_requirements = [req for req in frozen["requirements"] if req["kind"] in native_kinds_for_artifact]
    if native_requirements and artifact_problem is None and not source_problems:
        try:
            native_receipt = kernel.audit(task_dir, _native_job(task_dir, frozen, native_requirements))
            for result in native_receipt.get("checks", []):
                converted = {
                    "requirement_id": result["requirement_id"],
                    "status": result["status"],
                    "reason": result["reason"],
                    "observed": result.get("observed"),
                    "expected": result.get("expected"),
                    "description": "",
                    "mode": "must_change",
                    "locations": result.get("locations", []),
                }
                if result["requirement_id"].startswith("__"):
                    native_extras.append(converted)
                else:
                    native_checks[result["requirement_id"]] = converted
        except Exception as exc:
            for req in native_requirements:
                native_checks[req["id"]] = _blocked_check(req, f"Native check could not run: {exc}")

    checks = []
    if source_problems:
        for req in frozen["requirements"]:
            checks.append(_blocked_check(req, "; ".join(source_problems) + ". Passing is blocked."))
    elif artifact_problem is not None:
        for req in frozen["requirements"]:
            checks.append(_blocked_check(req, f"Deliverable cannot be accepted: {artifact_problem}"))
    else:
        for req in frozen["requirements"]:
            kind = req["kind"]
            if checkers.is_unsupported(kind):
                checks.append(
                    {
                        "requirement_id": req["id"],
                        "status": "UNKNOWN",
                        "reason": checkers.unsupported_reason(kind),
                        "observed": None,
                        "expected": None,
                        "description": req.get("description", ""),
                        "mode": req.get("mode", "must_change"),
                        "locations": [],
                    }
                )
            elif kind not in checkers.SUPPORTED_KINDS:
                checks.append(
                    {
                        "requirement_id": req["id"],
                        "status": "UNKNOWN",
                        "reason": f"No supported checker for {kind!r}. A model opinion is not evidence.",
                        "observed": None,
                        "expected": None,
                        "description": req.get("description", ""),
                        "mode": req.get("mode", "must_change"),
                        "locations": [],
                    }
                )
            elif kind in native_kinds_for_artifact:
                converted = native_checks.get(req["id"])
                if converted is None:
                    checks.append(
                        {
                            "requirement_id": req["id"],
                            "status": "UNKNOWN",
                            "reason": f"No supported checker for {kind!r} in the native adapter.",
                            "observed": None,
                            "expected": None,
                            "description": req.get("description", ""),
                            "mode": req.get("mode", "must_change"),
                            "locations": [],
                        }
                    )
                else:
                    checks.append({**converted, "description": req.get("description", ""), "mode": req.get("mode", "must_change")})
            elif kind in (
                "text.required_exact",
                "text.forbidden_exact",
                "text.word_limit",
                "markdown.required_exact",
                "markdown.forbidden_exact",
                "markdown.word_limit",
            ):
                if artifact_kind not in ("text", "markdown"):
                    checks.append(_blocked_check(req, "Text check needs a text deliverable."))
                else:
                    try:
                        artifact_text = artifact_path.read_text(encoding="utf-8")
                    except (OSError, UnicodeError) as exc:
                        checks.append(_blocked_check(req, f"Deliverable cannot be read as text: {exc}"))
                    else:
                        checks.append(checkers.check_text(req, artifact_text))
            elif kind == "json.field_exact":
                checks.append(checkers.check_json(req, artifact_path))
            elif kind in ("csv.columns", "csv.rows_exact", "csv.total_cap"):
                checks.append(checkers.check_csv(req, artifact_path, task_dir, frozen))
            else:
                checks.append(
                    {
                        "requirement_id": req["id"],
                        "status": "UNKNOWN",
                        "reason": f"No supported checker for {kind!r}. A model opinion is not evidence.",
                        "observed": None,
                        "expected": None,
                        "description": req.get("description", ""),
                        "mode": req.get("mode", "must_change"),
                        "locations": [],
                    }
                )
        for extra in native_extras:
            checks.append({**extra, "description": "Native-format coverage boundary", "mode": "unknown"})

    _after_problems, after_pins = verify_sources(task_dir, frozen)
    after = _binding(task_dir, frozen, artifact_path, after_pins)
    if canonical(before) != canonical(after):
        checks = [
            {**check, "status": "STALE", "reason": "Inputs changed during the review; no current evidence was established."}
            for check in checks
        ]
        if not checks:
            checks = [_blocked_check({"id": "__task__", "description": "Task inputs", "mode": "unknown"}, "Inputs changed during the review.")]
    counts = {"PASS": 0, "FAIL": 0, "UNKNOWN": 0, "STALE": 0, "BLOCKED": 0}
    for check in checks:
        if check["status"] in counts:
            counts[check["status"]] += 1
    receipt = {
        "receipt_schema": 1,
        "task_id": task_id,
        "title": frozen["title"],
        "request": frozen["request"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "binding": before,
        "checks": checks,
        "counts": counts,
        "decision": _decision(checks),
        "coverage": {
            "declared_requirements": len(frozen["requirements"]),
            "warning": "Only the listed requirements were checked. Model-interpreted coverage is not independently verified as complete. No global certification.",
        },
    }
    if write_outputs:
        _write_outputs(task_dir, receipt, artifact_path if artifact_problem is None else None)
    return receipt


def _write_outputs(task_dir, receipt, artifact_path=None):
    outputs = Path(task_dir) / "outputs"
    outputs.mkdir(exist_ok=True)
    stamp = _timestamp()
    target = outputs / stamp
    suffix = 0
    while target.exists():
        suffix += 1
        target = outputs / f"{stamp}-{suffix}"
    target.mkdir()
    receipt_path = target / "receipt.json"
    receipt_path.write_text(canonical(receipt) + "\n", encoding="utf-8")
    readable_path = target / "receipt.md"
    readable_path.write_text(render_readable_receipt(receipt), encoding="utf-8")
    snapshot_path = None
    if artifact_path is not None:
        source_path = Path(artifact_path)
        if source_path.is_file() and not source_path.is_symlink():
            data = source_path.read_bytes()
            # Snapshot only if it matches the receipt binding, so a later
            # edit cannot silently replace the reviewed bytes.
            bound = receipt.get("binding", {}).get("artifact", {})
            if bound.get("sha256") == _sha_bytes(data):
                snapshot_path = target / f"artifact-snapshot{source_path.suffix}"
                snapshot_path.write_bytes(data)
    for path in (receipt_path, readable_path, snapshot_path):
        if path is not None and path.is_file():
            try:
                path.chmod(0o444)
            except OSError:
                pass
    return target


def recheck_task(store_root, task_id, prior_receipt):
    fresh = review_task(store_root, task_id, write_outputs=False)
    if not isinstance(prior_receipt, dict) or prior_receipt.get("receipt_schema") != 1 or not isinstance(prior_receipt.get("binding"), dict):
        return {"status": "INVALID_EVIDENCE", "changed_bindings": [], "previous_results_verified": False, "fresh": fresh}
    changed = [
        key
        for key in fresh["binding"]
        if canonical(prior_receipt["binding"].get(key)) != canonical(fresh["binding"][key])
    ]

    def _semantic(receipt):
        return {
            "task_id": receipt.get("task_id"),
            "title": receipt.get("title"),
            "request": receipt.get("request"),
            "coverage": receipt.get("coverage"),
            "checks": receipt.get("checks"),
            "counts": receipt.get("counts"),
            "decision": receipt.get("decision"),
        }

    matches = canonical(_semantic(prior_receipt)) == canonical(_semantic(fresh))
    return {
        "status": "STALE" if changed else "FRESH" if matches else "INVALID_EVIDENCE",
        "changed_bindings": changed,
        "previous_results_verified": not changed and matches,
        "fresh": fresh,
    }


def _validate_repair_scope(repair_scope, frozen):
    if not isinstance(repair_scope, dict):
        raise TaskBlocked("Repair requires an explicitly reviewed repair scope.")
    if repair_scope.get("reviewed") is not True:
        raise TaskBlocked("Repair scope has not been explicitly reviewed.")
    scope_text = repair_scope.get("scope_text")
    if not isinstance(scope_text, str) or not scope_text.strip() or len(scope_text) > 2000:
        raise TaskBlocked("Repair scope text must be nonempty bounded text.")
    adopted = repair_scope.get("adopted_source_ids")
    if not isinstance(adopted, list):
        raise TaskBlocked("Repair scope must explicitly list adopted source IDs.")
    original_ids = {source["id"] for source in frozen.get("sources", [])}
    if len(set(adopted)) != len(adopted):
        raise TaskBlocked("Repair scope adopted source IDs must be distinct.")
    for source_id in adopted:
        if source_id not in original_ids:
            raise TaskBlocked("Repair scope adopts a source that is not in the original task.")
    return adopted


def repair_task(store_root, task_id, repair_scope=None):
    """Create a new task copy under the original requirements.

    The original task, artifact, and receipts are untouched. Only
    sources explicitly adopted by the reviewed repair scope are copied.
    The new task has no deliverable and no receipt until it is
    generated and reviewed under its own fresh review.
    """
    changed, _identity = _checker_changed()
    if changed:
        raise TaskBlocked("Checker code changed after process start; restart is required.")
    task_dir = resolve_task(store_root, task_id)
    frozen = load_frozen(task_dir)
    problems, _pins = verify_sources(task_dir, frozen)
    if problems:
        raise TaskBlocked("Repair is blocked because a frozen source is missing or changed.")
    adopted = _validate_repair_scope(repair_scope, frozen)
    new_id = "task-" + uuid.uuid4().hex[:16]
    store = Path(store_root).resolve()
    new_dir = store / "tasks" / new_id
    (new_dir / "sources").mkdir(parents=True)
    (new_dir / "artifacts").mkdir()
    (new_dir / "outputs").mkdir()
    adopted_sources = []
    for source in frozen["sources"]:
        if source["id"] in adopted:
            shutil.copyfile(task_dir / "sources" / source["name"], new_dir / "sources" / source["name"])
            adopted_sources.append(source)
    new_frozen = {
        **frozen,
        "task_id": new_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repaired_from": task_id,
        "repair_scope": repair_scope,
        "sources": adopted_sources,
    }
    frozen_text = canonical(new_frozen) + "\n"
    (new_dir / "frozen.json").write_text(frozen_text, encoding="utf-8")
    (new_dir / "frozen.sha256").write_text(_sha_bytes(frozen_text.encode("utf-8")) + "\n", encoding="utf-8")
    return {"task_id": new_id, "task_dir": str(new_dir), "frozen": new_frozen}
