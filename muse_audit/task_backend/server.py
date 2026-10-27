"""Five read-only MCP tools: four unchanged native-file tools plus review_run."""
import argparse
from pathlib import Path
from mcp.types import ToolAnnotations
from ..server import create_server as native_server
from .store import Store
from .provider import Provider
from .review import review_run as execute_review


def create_server(workspace, store_root, principal):
    Store(store_root, readonly=True)
    Provider(store_root, readonly=True)
    if not principal or len(principal) > 200:
        raise ValueError('Configure one explicit local principal')
    server = native_server(workspace)
    readonly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False)

    @server.tool(annotations=readonly)
    def review_run(run_id: str, claimed_outcome: str) -> dict:
        """Execute bounded acceptance against the authorized ORIGINAL contract and current synthetic state. Claim is untrusted. No writes or hidden host logs."""
        return execute_review(store_root, principal, run_id, claimed_outcome)

    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--principal', required=True, help='Trusted local harness scope, not an authentication credential')
    args = parser.parse_args()
    create_server(args.workspace, args.store, args.principal).run(transport='stdio')


if __name__ == '__main__':
    main()
