"""OFFLINE test doubles only: no claim of real Claude/model execution."""
import json
from pathlib import Path
from unittest.mock import patch
from muse_audit.claude_adapter.contract import CONTRACT,FILES
from muse_audit.claude_adapter.store import prepare,approve
from muse_audit.claude_adapter.collector import build
GOOD = '''export function createExpenseStore(storage) {
 let rows=JSON.parse(storage.getItem('stardive.expenses.v1')||'[]');
 let next=rows.reduce((n,r)=>Math.max(n,r.id),0)+1;
 const save=()=>storage.setItem('stardive.expenses.v1',JSON.stringify(rows));
 const valid=x=>{if(!Number.isSafeInteger(x)||x<0)throw Error('Invalid cents')};
 return {add(label,cents){valid(cents);let id=next++;rows.push({id,label,cents});save();return id},
 edit(id,cents){valid(cents);rows.find(r=>r.id===id).cents=cents;save()},
 remove(id){rows=rows.filter(r=>r.id!==id);save()},list(){return rows.map(r=>({...r}))},total(){return rows.reduce((n,r)=>n+r.cents,0)}};
}'''
BAD=GOOD.replace('rows.find(r=>r.id===id).cents=cents','rows.find(r=>r.id===id).cents+=cents')
def stream(session,tool='Write',error=False):
 return '\n'.join(json.dumps(e) for e in [
 {'type':'assistant','session_id':session,'message':{'content':[{'type':'tool_use','id':'tool1','name':tool,'input':{'file_path':'app.mjs','content':'test-double'}}]}},
 {'type':'user','session_id':session,'message':{'content':[{'type':'tool_result','tool_use_id':'tool1','is_error':error,'content':'file written'}]}},
 {'type':'result','subtype':'success','is_error':False,'session_id':session,'result':'Done'}])
def collect(tmp,code=GOOD,principal='owner',contract=CONTRACT):
 # Match prepare()'s canonical workspace on macOS, where /var aliases /private/var.
 base=Path(tmp).resolve();root=base/'store';work=base/'app'
 c=prepare(root,principal,work,contract);approve(root,principal,c['run_id'],c['contract_hash'])
 def fake_launch(argv,cwd,timeout):
  for f in FILES:(Path(cwd)/f).write_text(code if f=='app.mjs' else 'OFFLINE fixture; browser NOT tested')
  return 0,stream(argv[argv.index('--session-id')+1]),'',False
 with patch('muse_audit.claude_adapter.collector.launch',side_effect=fake_launch),patch('muse_audit.claude_adapter.collector.subprocess.run') as version:
  version.return_value.stdout='OFFLINE TEST DOUBLE; not Claude';build(root,principal,c['run_id'])
 return root,work,c['run_id']
