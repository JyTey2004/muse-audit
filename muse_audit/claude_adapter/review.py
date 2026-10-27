"""Execute current artifact checks; host history alone never supplies an outcome PASS."""
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from .contract import CONTRACT, FILES
from .identity import digest, sha, implementation
from .store import Store

def snapshot(workspace):
 root=Path(workspace)
 if root.is_symlink() or root.resolve()!=root:raise ValueError('Workspace changed through symlink')
 result={}
 for name in FILES:
  p=root/name
  if not p.exists():result[name]=None;continue
  if p.is_symlink() or not p.is_file() or p.stat().st_size>2_000_000:raise ValueError('Unsupported artifact type/size')
  result[name]=sha(p.read_bytes())
 return result

def execute(workspace, before, timeout=10):
 # Execute only the fixed checker against a copied current app. Sibling imports abstain.
 app=Path(workspace)/'app.mjs'
 if before.get('app.mjs') is None:return {'status':'UNKNOWN','reason':'Missing app.mjs'}
 with tempfile.TemporaryDirectory(prefix='stardive-node-') as d:
  dest=Path(d)/'app.mjs';dest.write_bytes(app.read_bytes())
  if sha(dest.read_bytes())!=before['app.mjs']:return {'status':'UNKNOWN','reason':'Artifact raced snapshot'}
  try:
   p=subprocess.run(['node','--experimental-vm-modules',str(Path(__file__).with_name('verifier.mjs')),str(dest)],cwd=d,
     env={'PATH':os.environ.get('PATH',''),'HOME':d},capture_output=True,text=True,timeout=timeout)
  except subprocess.TimeoutExpired:return {'status':'UNKNOWN','reason':'Checker execution timed out'}
  except OSError as e:return {'status':'UNKNOWN','reason':f'Node unavailable: {e}'}
  if p.returncode!=0:return {'status':'UNKNOWN','reason':'Verifier process failed','exit_code':p.returncode,'stderr':p.stderr[-2000:]}
  try:
   output=json.loads(p.stdout)
   assert output['schema']=='stardive.fixed-node.v1'
   assert set(output['tests'])=={'arithmetic','persistence','validation'}
   assert all(v['status'] in ('PASS','FAIL','UNKNOWN') for v in output['tests'].values())
  except (ValueError,KeyError,AssertionError,TypeError):return {'status':'UNKNOWN','reason':'Malformed checker output'}
  return {'status':'EXECUTED','tests':output['tests'],'exit_code':p.returncode}

def host_files_valid(root,run,h):
 try:
  from .collector import parse_stream, paths_valid
  folder=root/run
  text=(folder/'build-stream.jsonl').read_text()
  err=(folder/'build-stderr.txt').read_text()
  if digest(text)!=h.get('stream_hash') or digest(err)!=h.get('stderr_hash') or digest((folder/'build-mcp.json').read_text())!=h.get('config_hash'):return False
  parsed=parse_stream(text,h['session_id'])
  return (parsed['completed'] and h.get('exit_code')==0 and not h.get('timed_out')
    and any(b.get('name') in ('Write','Edit') for b in parsed['calls'].values())
    and all(b.get('name') in CONTRACT['allowed_actions'] for b in parsed['calls'].values())
    and paths_valid(parsed,h['workspace']))
 except (KeyError,ValueError,OSError):return False

def review_run(root,principal,run_id,claimed_outcome):
 if not isinstance(claimed_outcome,str) or len(claimed_outcome)>10000:raise ValueError('Bounded claim string required')
 s=Store(root,readonly=True);c=s.original(run_id,principal)
 approvals=s.records(run_id,principal,'approval')
 host=s.records(run_id,principal,'host')
 impl=implementation();before={};after={};problem=None
 try:before=snapshot(c['workspace'])
 except (ValueError,OSError) as e:problem=str(e)
 h=host[-1] if host else None
 valid_approval=any(a.get('contract_hash')==c['contract_hash'] and a.get('decision')=='approved' for a in approvals)
 host_valid=(h and h.get('origin')=='collector-subprocess' and h.get('contract_hash')==c['contract_hash'] and h.get('run_id')==run_id and h.get('principal')==principal and h.get('root')==str(s.root))
 status='UNKNOWN';reason='Missing trusted collector execution record';check={'status':'NOT_EXECUTED'}
 if not valid_approval:reason='Missing exact original-contract approval'
 elif not host_valid:pass
 elif h.get('status')=='pending':status='PENDING';reason='Host execution not finalized'
 elif h.get('status')!='completed':reason='Host execution failed, withheld or incomplete'
 elif h.get('contract_approved_before_execution') is not True or not any(a.get('approved_at',float('inf'))<=h.get('started_at',0) for a in approvals):reason='Approval ordering missing'
 elif not host_files_valid(s.root,run_id,h):reason='Missing, changed or invalid finalized host stream evidence'
 elif c['contract']!=CONTRACT:reason='Unsupported contract; fresh approval does not manufacture checker coverage'
 elif problem:reason=problem
 elif impl['restart_required']:reason='Acceptance source changed since process start; restart required'
 else:
  check=execute(c['workspace'],before)
  status='EXECUTED';reason='Independent fixed Node execution against current artifact snapshot'
 try:after=snapshot(c['workspace'])
 except (ValueError,OSError) as e:problem=str(e)
 after_impl=implementation()
 stable=not problem and before==after and impl==after_impl
 impl=after_impl
 if not stable:status='UNKNOWN';reason='Artifact changed during verification or unavailable';check={'status':'NOT_ACCEPTED'}
 conditions=[]
 for req,text in c['contract'].get('requirements',{}).items():
  verdict='UNKNOWN';detail=reason;executed=False
  if req in ('browser','privacy'):detail=text
  elif status=='PENDING':verdict='PENDING'
  elif status=='EXECUTED':
   if req in ('arithmetic','persistence','validation'):
    r=check.get('tests',{}).get(req,{})
    verdict=r.get('status','UNKNOWN');detail=r.get('detail',check.get('reason','Not executed'));executed=check.get('status')=='EXECUTED' and verdict in ('PASS','FAIL')
   elif req=='delivery':
    verdict='PASS' if all(before.get(f) for f in FILES) else 'FAIL';detail='Required file presence only; browser behavior remains unknown';executed=True
  conditions.append({'id':req,'status':verdict,'explanation':detail,'checker_executed':executed})
 bindings={'run_id':run_id,'root':str(s.root),'principal':principal,'contract_hash':c['contract_hash'],
  'approval_hash':digest(approvals),'host_hash':digest(host),'artifact_hashes':after,'implementation':impl}
 prior=s.records(run_id,principal,'receipt')
 freshness='NONE' if not prior else ('FRESH' if prior[-1]['bindings']==bindings else 'STALE')
 return {'schema':'stardive.claude-receipt.v1','run_id':run_id,'claim':{'origin':'agent-untrusted','text':claimed_outcome},
  'observed_at':time.time(),'conditions':conditions,'counts':{k:sum(x['status']==k for x in conditions) for k in ('PASS','FAIL','UNKNOWN','PENDING')},
  'decision':'UNRESOLVED' if any(x['status'] in ('UNKNOWN','PENDING') for x in conditions) else ('FAILED' if any(x['status']=='FAIL' for x in conditions) else 'SELECTED_CHECKS_PASSED'),
  'completion_certified':False,'freshness':{'prior_assurance':freshness,'observation':'Explicit review only; no continuous observer'},
  'bindings':bindings,'execution':{'before':before,'after':after,'stable':stable,'checker':check,'timeout_seconds':10},
  'scope':'Advisory fixed local API checks, not browser/security certification. Trusted-local generated code execution, not hostile-code sandbox. Host collector sees only its own subprocess; imported JSON cannot supply observed proof.'}

def record_receipt(root,principal,run,claim):
 receipt=review_run(root,principal,run,claim)
 Store(root).append('receipt',run,principal,receipt)
 return receipt
