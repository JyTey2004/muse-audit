"""Real subprocess MCP stdio initialize/list/call smoke test, not direct calls."""
import asyncio
import json
import os
from pathlib import Path
import sys
import unittest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def unpack(result):
    if result.isError:
        raise AssertionError(str(result.content))
    if result.structuredContent is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)


async def smoke(absolute_entrypoint=False):
    args = [str(ROOT/'run_mcp.py')] if absolute_entrypoint else ['-m','muse_audit.server']
    env = {key:value for key,value in os.environ.items() if key != 'PYTHONPATH'} if absolute_entrypoint else {**os.environ,'PYTHONPATH':str(ROOT)}
    parameters = StdioServerParameters(command=sys.executable,args=args+['--workspace',str(ROOT/'examples')], env=env,cwd='/tmp' if absolute_entrypoint else ROOT)
    async with stdio_client(parameters) as (read,write):
        async with ClientSession(read,write) as client:
            initialized = await client.initialize()
            listed = await client.list_tools()
            names = sorted(tool.name for tool in listed.tools)
            assert names == ['audit_capabilities','audit_job','prepare_repair','recheck_job'], names
            assert all(tool.annotations.readOnlyHint for tool in listed.tools)
            cap = unpack(await client.call_tool('audit_capabilities',{}))
            assert cap['model_adapter']['calls_made'] == 0
            receipt = unpack(await client.call_tool('audit_job',{'job_path':'home_office/job.json'}))
            assert receipt['counts']['FAIL'] == 1, receipt
            assert receipt['counts']['UNKNOWN'] == 1
            plan = unpack(await client.call_tool('prepare_repair',{'job_path':'home_office/job.json'}))
            assert len(plan['operations']) == 1
            rechecked = unpack(await client.call_tool('recheck_job',{'job_path':'home_office/job.json','prior_receipt':receipt}))
            assert rechecked['status'] == 'FRESH'
            study = unpack(await client.call_tool('audit_job',{'job_path':'study_summary/job.json'}))
            assert study['counts']['FAIL'] == 1 and study['counts']['UNKNOWN'] == 1, study
            invalid = await client.call_tool('audit_job',{'job_path':'../README.md'})
            assert invalid.isError
            valid_again = unpack(await client.call_tool('audit_job',{'job_path':'study_summary/job.json'}))
            assert valid_again['counts'] == study['counts']
            return {'protocol_version':initialized.protocolVersion,'server':initialized.serverInfo.model_dump(mode='json'),'tools':names,'initialize':'PASS','tools_list':'PASS','tools_call':'PASS','path_traversal_rejected':True,'repeat_after_error':'PASS','model_calls':0,'muse_host_tested':False}


class ProtocolTests(unittest.TestCase):
    def test_absolute_path_entrypoint_from_other_cwd(self):
        result = asyncio.run(asyncio.wait_for(smoke(True),30))
        self.assertEqual(result['tools_call'],'PASS')

    def test_real_stdio(self):
        result = asyncio.run(asyncio.wait_for(smoke(),30))
        self.assertEqual(result['tools_call'],'PASS')


if __name__ == '__main__':
    result = asyncio.run(asyncio.wait_for(smoke(),30))
    print(json.dumps(result,indent=2))
