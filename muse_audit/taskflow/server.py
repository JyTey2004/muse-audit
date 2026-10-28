"""Strictly read-only taskflow server over stdio.

No tool here writes, repairs, or generates a deliverable. Review and
recheck only read frozen tasks and return receipts. Preparation, repair,
generation, and writing a readable receipt plus an artifact snapshot
stay outside this server, in the client flow.
"""

import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import checks as checkers
from .tasks import recheck_task, review_task


def create_server(store_root):
    root = Path(store_root).resolve(strict=True)
    server = FastMCP(
        "Muse taskflow prototype",
        instructions="Review only frozen tasks in the launch-scoped store. Results cover listed deterministic checks, not universal truth. No model calls. No repair or generation tool is exposed.",
        log_level="WARNING",
    )
    readonly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

    @server.tool(annotations=readonly)
    def taskflow_capabilities() -> dict:
        """Describe real taskflow check coverage and what stays unverified."""
        return {
            "version": "taskflow-0.1",
            "supported": sorted(checkers.SUPPORTED_KINDS),
            "unsupported": [
                "semantic claims",
                "web claims",
                "privacy claims",
                "sent or delivered messages",
                "provider state",
                "arbitrary shell or URL evaluation",
            ],
            "coverage_warning": (
                "Only listed requirements are checked. Model-interpreted coverage "
                "is not independently verified as complete. No global certification."
            ),
            "read_only": True,
        }

    @server.tool(annotations=readonly)
    def taskflow_review(task_id: str) -> dict:
        """Review one frozen task in this store, without writing a receipt file."""
        return review_task(root, task_id, write_outputs=False)

    @server.tool(annotations=readonly)
    def taskflow_recheck(task_id: str, prior_receipt: dict) -> dict:
        """Recompute a frozen task and compare it with a prior receipt, never trusting old values."""
        return recheck_task(root, task_id, prior_receipt)

    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True, help="Launch-scoped store containing frozen tasks")
    args = parser.parse_args()
    create_server(args.workspace).run(transport="stdio")


if __name__ == "__main__":
    main()
