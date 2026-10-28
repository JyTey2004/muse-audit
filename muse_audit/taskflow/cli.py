"""CLI for the taskflow layer.

Prepare freezes a task before generation. Review writes a new
timestamped receipt directory and never overwrites prior receipts.
Repair creates a new task copy under the original requirements.
Recheck recomputes everything and reports freshness.
"""

import argparse
import json
from pathlib import Path

from ..io import canonical, read_json
from .receipt import render_readable_receipt
from .tasks import prepare_task, recheck_task, repair_task, review_task


def _load_json_file(path):
    return read_json(Path(path))


def _parse_source(spec):
    if "=" not in spec:
        raise ValueError("Source must be given as id=path.")
    source_id, path = spec.split("=", 1)
    if not source_id or not path:
        raise ValueError("Source must be given as id=path.")
    return source_id, Path(path), Path(path).name


def main(argv=None):
    parser = argparse.ArgumentParser(prog="taskflow")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Freeze a fresh task before generation.")
    prepare.add_argument("--store", type=Path, required=True)
    prepare.add_argument("--request", default=None)
    prepare.add_argument("--request-file", type=Path, default=None)
    prepare.add_argument("--requirements-json", type=Path, required=True)
    prepare.add_argument("--source", action="append", default=[], dest="sources")
    prepare.add_argument("--artifact-name", required=True)
    prepare.add_argument("--artifact-kind", required=True, choices=["text", "markdown", "json", "csv", "xlsx", "docx"])
    prepare.add_argument("--title", default=None)

    review = sub.add_parser("review", help="Review a frozen task and write a new receipt.")
    review.add_argument("--store", type=Path, required=True)
    review.add_argument("--task-id", required=True)

    recheck = sub.add_parser("recheck", help="Recompute a frozen task against a prior receipt.")
    recheck.add_argument("--store", type=Path, required=True)
    recheck.add_argument("--task-id", required=True)
    recheck.add_argument("--prior-receipt", type=Path, required=True)

    repair = sub.add_parser("repair", help="Create a new task copy under the original requirements.")
    repair.add_argument("--store", type=Path, required=True)
    repair.add_argument("--task-id", required=True)
    repair.add_argument("--repair-scope-json", type=Path, required=True)

    render = sub.add_parser("render", help="Render a readable receipt from a machine receipt.")
    render.add_argument("--receipt", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "prepare":
        if args.request is not None:
            request = args.request
        elif args.request_file is not None:
            request = args.request_file.read_text(encoding="utf-8")
        else:
            raise ValueError("Provide --request or --request-file.")
        requirements = _load_json_file(args.requirements_json)
        sources = [_parse_source(spec) for spec in args.sources]
        result = prepare_task(args.store, request, requirements, sources, args.artifact_name, args.artifact_kind, title=args.title)
        print(canonical({"task_id": result["task_id"], "task_dir": result["task_dir"]}))
    elif args.command == "review":
        receipt = review_task(args.store, args.task_id, write_outputs=True)
        print(canonical(receipt))
    elif args.command == "recheck":
        prior = _load_json_file(args.prior_receipt)
        print(canonical(recheck_task(args.store, args.task_id, prior)))
    elif args.command == "repair":
        repair_scope = _load_json_file(args.repair_scope_json)
        result = repair_task(args.store, args.task_id, repair_scope)
        print(canonical({"task_id": result["task_id"], "task_dir": result["task_dir"], "repaired_from": args.task_id}))
    elif args.command == "render":
        receipt = _load_json_file(args.receipt)
        print(render_readable_receipt(receipt))


if __name__ == "__main__":
    main()
