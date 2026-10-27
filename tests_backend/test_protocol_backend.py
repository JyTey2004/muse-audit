"""Real official SDK stdio initialize/list/call, including no-write and isolation assertions."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from muse_audit.task_backend.runner import Runner
from muse_audit.task_backend.contracts import create_contract, approve_contract, expense_contract
from muse_audit.task_backend.provider import execute_tracker

ROOT = Path(__file__).resolve().parents[1]


def unpack(result):
    if result.isError:
        raise AssertionError(str(result.content))
    return result.structuredContent if result.structuredContent is not None else json.loads(result.content[0].text)


def pins(root):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).glob('*.sqlite3')}


async def protocol_smoke():
    with tempfile.TemporaryDirectory() as d:
        runner = Runner(d)
        c = create_contract(runner.store, runner.owner, expense_contract())
        approve_contract(runner.store, runner.owner, c['contract_id'], c['contract_hash'], reviewed=True)
        run_id = runner.start(c['contract_id'])
        runner.review(run_id)
        foreign = Runner(d, 'other-principal')
        fc = create_contract(foreign.store, foreign.owner, expense_contract())
        approve_contract(foreign.store, foreign.owner, fc['contract_id'], fc['contract_hash'], reviewed=True)
        foreign_id = foreign.start(fc['contract_id'])
        params = StdioServerParameters(command=sys.executable, args=['-m','muse_audit.task_backend.server','--workspace',str(ROOT/'examples'),'--store',d,'--principal',runner.owner], env={**os.environ,'PYTHONPATH':str(ROOT)}, cwd='/tmp')
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                initialized = await client.initialize()
                listed = await client.list_tools()
                names = sorted(t.name for t in listed.tools)
                assert names == ['audit_capabilities','audit_job','prepare_repair','recheck_job','review_run'], names
                assert all(t.annotations.readOnlyHint for t in listed.tools)
                before = pins(d)
                first = unpack(await client.call_tool('review_run', {'run_id': run_id, 'claimed_outcome': 'Done'}))
                assert first['counts'] == {'FAIL': 2, 'PASS': 2, 'UNKNOWN': 1}, first
                assert pins(d) == before, 'Read-only review wrote to persisted state'
                # Same narrative, independently changed provider state; server has no log injection input.
                runner.mutate(run_id, 'result', execute_tracker(expense_contract()['source'], True))
                before = pins(d)
                second = unpack(await client.call_tool('review_run', {'run_id': run_id, 'claimed_outcome': 'Done'}))
                assert second['counts'] == {'PASS': 4, 'UNKNOWN': 1}, second
                assert second['freshness']['prior_assurance'] == 'STALE'
                assert pins(d) == before
                assert (await client.call_tool('review_run', {'run_id': foreign_id, 'claimed_outcome': 'Done'})).isError
                assert (await client.call_tool('review_run', {'run_id': '../runs.sqlite3', 'claimed_outcome': 'Done'})).isError
                native = unpack(await client.call_tool('audit_job', {'job_path':'home_office/job.json'}))
                assert native['counts']['FAIL'] == 1 and native['counts']['UNKNOWN'] == 1
                return {'protocol_version': initialized.protocolVersion, 'initialize': 'PASS', 'tools_list': names,
                        'review_run_before': first['counts'], 'review_run_after_same_claim': second['counts'], 'read_only_database_hashes': 'UNCHANGED',
                        'cross_principal_and_path_rejected': True, 'legacy_native_budget': native['counts'],
                        'muse_tested': False, 'transport': 'official MCP Python SDK 1.29.0 subprocess stdio', 'model_calls': 0}


class BackendProtocolTests(unittest.TestCase):
    def test_real_readonly_stdio_and_authorized_run_resolution(self):
        result = asyncio.run(asyncio.wait_for(protocol_smoke(), 45))
        self.assertEqual(result['initialize'], 'PASS')


if __name__ == '__main__':
    result = asyncio.run(asyncio.wait_for(protocol_smoke(), 45))
    print(json.dumps(result, indent=2))
