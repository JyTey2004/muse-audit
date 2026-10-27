"""Real MCP SDK protocol with OFFLINE collector double; no Claude/model execution."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from fixture import collect,BAD
from muse_audit.claude_adapter.review import record_receipt
ROOT=Path(__file__).resolve().parents[1]
def unpack(r):
 if r.isError:raise AssertionError(str(r.content))
 return r.structuredContent if r.structuredContent is not None else json.loads(r.content[0].text)
async def protocol():
 with tempfile.TemporaryDirectory() as d:
  root,work,run=collect(d);record_receipt(root,'owner',run,'Done')
  params=StdioServerParameters(command=sys.executable,args=['-m','muse_audit.claude_adapter.server','--store',str(root),'--principal','owner'],env={**os.environ,'PYTHONPATH':str(ROOT)},cwd='/tmp')
  async with stdio_client(params) as (read,write):
   async with ClientSession(read,write) as client:
    initialized=await client.initialize();listed=await client.list_tools()
    assert [t.name for t in listed.tools]==['review_run'];assert listed.tools[0].annotations.readOnlyHint
    properties=listed.tools[0].inputSchema['properties'];assert set(properties)=={'run_id','claimed_outcome'}
    path=root/'claude-runs.sqlite3';before=hashlib.sha256(path.read_bytes()).hexdigest()
    first=unpack(await client.call_tool('review_run',{'run_id':run,'claimed_outcome':'Done'}))
    assert first['counts']=={'PASS':4,'FAIL':0,'UNKNOWN':2,'PENDING':0},first
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    (work/'app.mjs').write_text(BAD)
    second=unpack(await client.call_tool('review_run',{'run_id':run,'claimed_outcome':'Done'}))
    assert second['conditions'][0]['status']=='FAIL';assert second['freshness']['prior_assurance']=='STALE'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    foreign=await client.call_tool('review_run',{'run_id':'a'*32,'claimed_outcome':'Done'});assert foreign.isError
    traversal=await client.call_tool('review_run',{'run_id':'../app','claimed_outcome':'Done'});assert traversal.isError
    return {'protocol':initialized.protocolVersion,'tools':[t.name for t in listed.tools],'input_properties':list(properties),
     'first':first['counts'],'changed_app_same_claim':second['counts'],'prior':second['freshness'],
     'database_bytes':'UNCHANGED','foreign_and_traversal':'REJECTED','host':'OFFLINE collector double; NOT Claude','model_calls':0}
class ProtocolTests(unittest.TestCase):
 def test_real_initialize_list_call_readonly_and_current_state(self):asyncio.run(asyncio.wait_for(protocol(),45))
if __name__=='__main__':print(json.dumps(asyncio.run(asyncio.wait_for(protocol(),45)),indent=2))
