"""Two explicit phases. Never imports agent-written evidence as host observations."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
from .contract import CONTRACT
from .identity import digest, implementation
from .review import snapshot, review_run, record_receipt
from .store import Store

TOOL='mcp__stardive__review_run'

def paths_valid(parsed,workspace):
 from .contract import FILES
 root=Path(workspace).resolve()
 try:
  for block in parsed['calls'].values():
   inputs=block.get('input')
   if not isinstance(inputs,dict):return False
   raw=inputs.get('file_path')
   if not isinstance(raw,str):return False
   p=Path(raw)
   resolved=(root/p).resolve() if not p.is_absolute() else p.resolve()
   if resolved.parent!=root or resolved.name not in FILES:return False
  return True
 except (ValueError,OSError,TypeError):return False

def parse_stream(text,session):
 events=[];calls={};results={};terminal=None;issues=[]
 try:
  for line in text.splitlines():
   if not line.strip():continue
   e=json.loads(line)
   if not isinstance(e,dict):raise ValueError('Object event required')
   if terminal:issues.append('Events after terminal result')
   events.append(e)
   if e.get('session_id') and e['session_id']!=session:issues.append('Foreign session')
   typ=e.get('type')
   if typ in ('assistant','user'):
    if e.get('session_id')!=session:issues.append('Missing message session')
    for block in e.get('message',{}).get('content',[]):
     if not isinstance(block,dict):continue
     if block.get('type')=='tool_use':
      if typ!='assistant':issues.append('Tool use outside assistant')
      ident=block.get('id')
      if not ident or ident in calls:issues.append('Duplicate/missing tool use ID')
      calls[ident]=block
     elif block.get('type')=='tool_result':
      if typ!='user':issues.append('Tool result outside user')
      ident=block.get('tool_use_id')
      if ident not in calls or ident in results:issues.append('Unmatched/duplicate tool result')
      results[ident]=block
   elif typ=='result':
    if terminal:issues.append('Multiple terminal events')
    terminal=e
 except (ValueError,TypeError,AttributeError):issues.append('Malformed stream JSON')
 if any(i not in results for i in calls):issues.append('Missing tool result')
 if any(b.get('is_error') for b in results.values()):issues.append('Tool error observed')
 completed=bool(terminal and terminal.get('session_id')==session and terminal.get('subtype')=='success' and not terminal.get('is_error') and not issues)
 return {'events':events,'calls':calls,'results':results,'terminal':terminal,'issues':issues,'completed':completed}

def command(phase,session,config,prompt):
 tools='Read,Write,Edit' if phase=='build' else ''
 allowed=tools if phase=='build' else TOOL
 return ['claude','--restricted','-p',prompt,'--output-format','stream-json','--verbose','--session-id',session,
  '--no-session-persistence','--setting-sources','','--settings','{"disableAllHooks":true}',
  '--strict-mcp-config','--mcp-config',str(config),'--tools',tools,'--allowedTools',allowed,
  '--permission-mode','dontAsk','--max-turns','24' if phase=='build' else '4']

def launch(argv,cwd,timeout):
 # A process group is killed on timeout, including spawned MCP children.
 p=subprocess.Popen(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 try:out,err=p.communicate(timeout=timeout);return p.returncode,out,err,False
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate();return p.returncode,out,err,True

def build(root,principal,run,timeout=600):
 s=Store(root);c=s.original(run,principal)
 approved=s.records(run,principal,'approval')
 if not any(a['contract_hash']==c['contract_hash'] and a['decision']=='approved' for a in approved):raise ValueError('Approve exact contract before execution')
 if s.records(run,principal,'host'):raise ValueError('Run already started; prepare new run instead of overwriting')
 if any(Path(c['workspace']).iterdir()):raise ValueError('Build requires empty dedicated workspace')
 impl=implementation()
 if impl['restart_required']:raise ValueError('Restart after source changes')
 session=str(uuid.uuid4());started=time.time()
 base={'origin':'collector-subprocess','run_id':run,'principal':principal,'root':str(s.root),'contract_hash':c['contract_hash'],
  'workspace':c['workspace'],'session_id':session,'started_at':started,'contract_approved_before_execution':True,'implementation':impl}
 s.append('host',run,principal,{**base,'status':'pending'})
 folder=s.root/run;folder.mkdir(exist_ok=False)
 config=folder/'build-mcp.json';config.write_text('{"mcpServers":{}}')
 prompt='Create these files in the CURRENT empty directory. Do not write evidence/receipts or invoke external commands/services. Contract:\n'+json.dumps(c['contract'])
 argv=command('build',session,config,prompt)
 try:
  version=subprocess.run(['claude','--version'],capture_output=True,text=True,timeout=10,check=True).stdout.strip()
  code,out,err,timed=launch(argv,c['workspace'],timeout)
 except (OSError,subprocess.SubprocessError) as e:
  code,out,err,timed=-1,'',str(e),False;version='unavailable'
 (folder/'build-stream.jsonl').write_text(out);(folder/'build-stderr.txt').write_text(err)
 parsed=parse_stream(out,session)
 valid_tools=paths_valid(parsed,c['workspace']) and bool(parsed['calls']) and any(t.get('name') in ('Write','Edit') for t in parsed['calls'].values()) and all(t.get('name') in CONTRACT['allowed_actions'] for t in parsed['calls'].values())
 try:artifacts=snapshot(c['workspace'])
 except (ValueError,OSError):artifacts={}
 body={**base,'status':'completed' if code==0 and parsed['completed'] and valid_tools and not timed else 'failed',
  'finished_at':time.time(),'exit_code':code,'timed_out':timed,'claude_version':version,'argv':argv,
  'stream_hash':digest(out),'stderr_hash':digest(err),'config_hash':digest(config.read_text()),'parsed':parsed,'artifact_hashes':artifacts,'tools_allowed':valid_tools}
 if artifacts:
  archive=folder/'build-artifacts';archive.mkdir()
  for name,expected in artifacts.items():
   if expected:
    data=(Path(c['workspace'])/name).read_bytes()
    from .identity import sha
    if sha(data)!=expected:body['status']='failed';body['artifact_archive_error']='Artifact raced finalization';break
    (archive/name).write_bytes(data)
 s.append('host',run,principal,body)
 return body

def review_phase(root,principal,run,claim='The app is done',timeout=180):
 s=Store(root);c=s.original(run,principal)
 host=s.records(run,principal,'host')
 if not host or host[-1]['status']!='completed':raise ValueError('Finalize successful host evidence before review session')
 folder=s.root/run;session=str(uuid.uuid4())
 config=folder/'review-mcp.json'
 config.write_text(json.dumps({'mcpServers':{'stardive':{'command':sys.executable,'args':['-m','muse_audit.claude_adapter.server','--store',str(s.root),'--principal',principal], 'env':{'PYTHONPATH':str(Path(__file__).resolve().parents[2])}}}}))
 cwd=folder/'review-session';cwd.mkdir(exist_ok=False)
 prompt=f'Call {TOOL} exactly once with run_id={run!r} and claimed_outcome={claim!r}. Do not invent evidence. Report the returned completion receipt and required unknowns. This review is advisory.'
 argv=command('review',session,config,prompt)
 before=s.path.read_bytes();code,out,err,timed=launch(argv,cwd,timeout)
 (folder/'review-stream.jsonl').write_text(out);(folder/'review-stderr.txt').write_text(err)
 unchanged=s.path.read_bytes()==before
 parsed=parse_stream(out,session)
 calls=[(ident,b) for ident,b in parsed['calls'].items() if b.get('name')==TOOL and b.get('input')=={'run_id':run,'claimed_outcome':claim}]
 good=(code==0 and not timed and parsed['completed'] and len(calls)==1 and len(parsed['calls'])==1 and unchanged)
 if not good:raise ValueError('Review session did not demonstrate one successful read-only review_run call; inspect preserved stream')
 result=parsed['results'][calls[0][0]].get('content')
 try:
  if isinstance(result,list):result=''.join(b.get('text','') for b in result if b.get('type')=='text')
  observed=json.loads(result) if isinstance(result,str) else result
  # FastMCP may wrap structured content in a result field on some host versions.
  if isinstance(observed,dict) and 'result' in observed and 'schema' not in observed:observed=observed['result']
  current=review_run(root,principal,run,claim)
  if (not isinstance(observed,dict) or observed.get('schema')!=current['schema'] or observed.get('run_id')!=run
      or observed.get('bindings')!=current['bindings'] or observed.get('conditions')!=current['conditions']):raise ValueError('MCP tool result does not match fresh independent receipt')
 except (ValueError,TypeError,KeyError) as e:raise ValueError('Missing/malformed/stale MCP receipt in actual tool_result') from e
 # Recompute locally; never turn model-emitted JSON into authoritative observed proof.
 receipt=review_run(root,principal,run,claim)
 if receipt['bindings']!=observed['bindings'] or receipt['conditions']!=observed['conditions']:raise ValueError('State changed after MCP review; receipt withheld, review again explicitly')
 Store(root).append('receipt',run,principal,receipt)
 receipt['claude_review_observation']={'session_id':session,'tool_use_id':calls[0][0],'stream_hash':digest(out),'database_unchanged_during_review':unchanged,'advisory':True,'argv':argv,'config_hash':digest(config.read_text()),'implementation':implementation()}
 receipt['claude_review_observation_hash']=digest(receipt['claude_review_observation'])
 (folder/'completion-receipt.json').write_text(json.dumps(receipt,indent=2))
 return receipt
