"""Actual MCP stdio transport. No stdout logging and no mutation tools."""
import argparse
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from . import core


def create_server(workspace):
    root = Path(workspace).resolve(strict=True)
    server = FastMCP('Muse audit prototype', instructions='Audit only user-selected local bundles. Results cover declared deterministic checks, not universal truth. No model calls. Repair tools only prepare diffs; no mutation tool is exposed.', log_level='WARNING')
    readonly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

    @server.tool(annotations=readonly)
    def audit_capabilities() -> dict:
        """Describe real check coverage, unsupported formats and disabled model adapter."""
        return core.capabilities()

    @server.tool(annotations=readonly)
    def audit_job(job_path: str) -> dict:
        """Fully check one selected job.json relative to the configured workspace."""
        return core.audit_job(root, job_path)

    @server.tool(annotations=readonly)
    def recheck_job(job_path: str, prior_receipt: dict) -> dict:
        """Compare previous evidence bindings and recompute ALL checks, never trust old PASS values."""
        return core.recheck(root, job_path, prior_receipt)

    @server.tool(annotations=readonly)
    def prepare_repair(job_path: str) -> dict:
        """Return exact reviewable before/after operations. Does NOT edit any files."""
        return core.prepare_repair(root, job_path)

    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True,help='Explicit local directory containing selected audit bundles')
    args = parser.parse_args()
    create_server(args.workspace).run(transport='stdio')


if __name__ == '__main__':
    main()
