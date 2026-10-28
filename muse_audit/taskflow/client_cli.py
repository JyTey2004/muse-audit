"""Command line for the real server review client.

This command calls the read-only server, retains observations, and
writes an immutable readable receipt plus an artifact snapshot outside
the server process. It never presents a direct Python review as a
server review.
"""

import argparse
from pathlib import Path

from ..io import canonical
from .client import mcp_review, mcp_review_timestamped


def main(argv=None):
    parser = argparse.ArgumentParser(prog="taskflow-mcp-review")
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", type=Path, default=None, help="New output directory. If omitted, a timestamped directory is created.")
    args = parser.parse_args(argv)
    if args.output is not None:
        result = mcp_review(args.store, args.task_id, args.output)
    else:
        result = mcp_review_timestamped(args.store, args.task_id)
    print(canonical({"task_id": result["task_id"], "output_dir": result["output_dir"], "decision": result["receipt"].get("decision")}))


if __name__ == "__main__":
    main()
