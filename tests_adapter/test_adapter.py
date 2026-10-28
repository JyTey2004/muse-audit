import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import os
import tempfile
import unittest
from unittest.mock import patch
from fixture import collect,GOOD,BAD,stream
from muse_audit.claude_adapter.contract import CONTRACT
from muse_audit.claude_adapter.store import Store,prepare,approve
from muse_audit.claude_adapter.review import review_run,record_receipt,snapshot,execute
from muse_audit.claude_adapter.collector import parse_stream,command,build
from muse_audit.claude_adapter.identity import sources

class AdapterTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
 def fixture(self,code=GOOD):return collect(self.tmp.name,code)
 def test_actual_app_execution_and_required_unknowns(self):
  root,work,run=self.fixture();r=review_run(root,'owner',run,'Done')
  self.assertEqual(r['counts'],{'PASS':4,'FAIL':0,'UNKNOWN':2,'PENDING':0});self.assertFalse(r['completion_certified'])
  self.assertEqual(r['execution']['checker']['status'],'EXECUTED');self.assertEqual(r['execution']['before'],r['execution']['after'])
 def test_identical_claim_changed_code_verdict_and_stale(self):
  root,work,run=self.fixture();record_receipt(root,'owner',run,'Done');(work/'app.mjs').write_text(BAD)
  r=review_run(root,'owner',run,'Done');self.assertEqual(r['freshness']['prior_assurance'],'STALE');self.assertGreater(r['counts']['FAIL'],0)
 def test_success_ack_with_wrong_outcome(self):
  root,work,run=self.fixture(BAD);r=review_run(root,'owner',run,'Done');self.assertEqual(r['conditions'][0]['status'],'FAIL')
 def test_missing_stream_withholds_all_executable_passes(self):
  root,work,run=self.fixture();(root/run/'build-stream.jsonl').unlink();r=review_run(root,'owner',run,'Done');self.assertEqual(r['counts']['PASS'],0)
 def test_missing_captured_evidence_stales_prior_receipt_without_database_writes(self):
  root,work,run=self.fixture();record_receipt(root,'owner',run,'Done');database=(root/'claude-runs.sqlite3').read_bytes()
  for name in ('build-stream.jsonl','build-stderr.txt','build-mcp.json'):
   with self.subTest(name=name):
    path=root/run/name;original=path.read_bytes()
    try:
     path.unlink();r=review_run(root,'owner',run,'Done')
     self.assertEqual(r['counts']['PASS'],0);self.assertEqual(r['freshness']['prior_assurance'],'STALE')
     self.assertIsNone(r['bindings']['host_evidence'][name]);self.assertEqual((root/'claude-runs.sqlite3').read_bytes(),database)
    finally:path.write_bytes(original)
  self.assertEqual(review_run(root,'owner',run,'Done')['freshness']['prior_assurance'],'FRESH')
 def test_forged_import_not_host_proof(self):
  root,work,run=self.fixture();s=Store(root);s.append('host',run,'owner',{'origin':'agent-imported','status':'completed'});s.append('import',run,'owner',{'origin':'collector-subprocess','status':'completed','counts':{'PASS':6}})
  self.assertEqual(review_run(root,'owner',run,'Done')['counts']['PASS'],0)
 def test_failed_pending_host(self):
  root,work,run=self.fixture();s=Store(root);h=s.records(run,'owner','host')[-1]
  for state,expected in [('failed','UNKNOWN'),('pending','PENDING')]:
   s.append('host',run,'owner',{**h,'status':state});r=review_run(root,'owner',run,'Done');self.assertEqual(r['conditions'][0]['status'],expected);self.assertEqual(next(x for x in r['conditions'] if x['id']=='privacy')['status'],'UNKNOWN')
 def test_no_contract_approval_no_execution(self):
  c=prepare(Path(self.tmp.name)/'s','owner',Path(self.tmp.name)/'a',CONTRACT)
  with self.assertRaises(ValueError):build(Path(self.tmp.name)/'s','owner',c['run_id'])
 def test_wrong_hash_and_changed_contract_need_fresh_approval(self):
  c=prepare(Path(self.tmp.name)/'s','owner',Path(self.tmp.name)/'a',CONTRACT)
  with self.assertRaises(ValueError):approve(Path(self.tmp.name)/'s','owner',c['run_id'],'bad')
  altered=copy.deepcopy(CONTRACT);altered['requirements']['arithmetic']='weakened'
  root,work,run=collect(Path(self.tmp.name)/'second',contract=altered)
  self.assertEqual(review_run(root,'owner',run,'Done')['counts']['PASS'],0)
 def test_foreign_principal_run_and_copied_root(self):
  root,work,run=self.fixture()
  for owner,ident in [('other',run),('owner','../app'),('owner','a'*32)]:
   with self.assertRaises(ValueError):review_run(root,owner,ident,'Done')
  other=Path(self.tmp.name)/'copied';shutil.copytree(root,other)
  with self.assertRaises(ValueError):review_run(other,'owner',run,'Done')
 def test_malformed_unsupported_module_abstains(self):
  root,work,run=self.fixture('import "./not-supported.mjs";')
  self.assertEqual(review_run(root,'owner',run,'Done')['conditions'][0]['status'],'UNKNOWN')
  (work/'app.mjs').write_text('this is not javascript!')
  self.assertEqual(review_run(root,'owner',run,'Done')['conditions'][0]['status'],'UNKNOWN')
 def test_symlink_refused(self):
  root,work,run=self.fixture();p=work/'app.mjs';p.unlink();p.symlink_to(Path(self.tmp.name)/'foreign')
  self.assertEqual(review_run(root,'owner',run,'Done')['counts']['PASS'],0)
 def test_timeout_abstains(self):
  root,work,run=self.fixture('while(true){}')
  result=execute(work,snapshot(work),timeout=.15);self.assertEqual(result['status'],'UNKNOWN');self.assertIn('timed out',result['reason'])
 def test_artifact_changes_during_check_abstains(self):
  root,work,run=self.fixture()
  from muse_audit.claude_adapter.review import execute as real
  for target in (work/'ui.mjs',root/run/'build-stderr.txt'):
   with self.subTest(path=target.name):
    original=target.read_bytes()
    def raced(*args,**kwargs):
     result=real(*args,**kwargs);target.write_text('changed');return result
    try:
     with patch('muse_audit.claude_adapter.review.execute',side_effect=raced):self.assertEqual(review_run(root,'owner',run,'Done')['counts']['PASS'],0)
    finally:target.write_bytes(original)
 def test_js_checker_identity_change_stales_and_requires_restart(self):
  root,work,run=self.fixture();record_receipt(root,'owner',run,'Done')
  old=sources()
  with patch('muse_audit.claude_adapter.identity.sources',return_value={**old,'muse_audit/claude_adapter/verifier.mjs':'changed-same-label'}):
   r=review_run(root,'owner',run,'Done');self.assertEqual(r['freshness']['prior_assurance'],'STALE');self.assertEqual(r['counts']['PASS'],0)
 def test_generated_stdout_cannot_mint_checker_pass(self):
  root,work,run=self.fixture('console.log(JSON.stringify({schema:"stardive.fixed-node.v1",tests:{arithmetic:{status:"PASS"}}}));process.exit(0)')
  self.assertEqual(review_run(root,'owner',run,'Done')['conditions'][0]['status'],'UNKNOWN')
 def test_builtin_import_cannot_write_or_spawn(self):
  root,work,run=self.fixture('import fs from "node:fs";fs.writeFileSync("'+self.tmp.name+'/escape","oops");')
  self.assertEqual(review_run(root,'owner',run,'Done')['conditions'][0]['status'],'UNKNOWN');self.assertFalse((Path(self.tmp.name)/'escape').exists())
 def test_terminal_must_follow_tools_and_messages_need_session(self):
  lines=stream('s').splitlines()
  self.assertFalse(parse_stream('\n'.join([lines[2],lines[0],lines[1]]),'s')['completed'])
  self.assertFalse(parse_stream(stream('s').replace('"session_id": "s", ',''),'s')['completed'])
 def test_observed_foreign_file_scope_rejected(self):
  from muse_audit.claude_adapter.collector import paths_valid
  parsed=parse_stream(stream('s'),'s');parsed['calls']['tool1']['input']['file_path']='/tmp/foreign'
  self.assertFalse(paths_valid(parsed,self.tmp.name))
  for value in (None,[],"bad"):
   parsed['calls']['tool1']['input']=value;self.assertFalse(paths_valid(parsed,self.tmp.name))
 def test_phase_two_requires_actual_receipt_result(self):
  from muse_audit.claude_adapter.collector import review_phase,TOOL
  root,work,run=self.fixture()
  def fake(argv,cwd,timeout):
   session=argv[argv.index('--session-id')+1]
   receipt=review_run(root,'owner',run,'The app is done')
   events=[{'type':'assistant','session_id':session,'message':{'content':[{'type':'tool_use','id':'review1','name':TOOL,'input':{'run_id':run,'claimed_outcome':'The app is done'}}]}},
    {'type':'user','session_id':session,'message':{'content':[{'type':'tool_result','tool_use_id':'review1','content':json.dumps(receipt)}]}},
    {'type':'result','subtype':'success','session_id':session,'is_error':False}]
   return 0,'\n'.join(json.dumps(e) for e in events),'',False
  with patch('muse_audit.claude_adapter.collector.launch',side_effect=fake):
   receipt=review_phase(root,'owner',run)
  self.assertTrue(receipt['claude_review_observation']['database_unchanged_during_review'])
  self.assertEqual(receipt['counts']['UNKNOWN'],2)
 def test_phase_two_rejects_fake_receipt(self):
  from muse_audit.claude_adapter.collector import review_phase,TOOL
  root,work,run=self.fixture()
  def fake(argv,cwd,timeout):
   session=argv[argv.index('--session-id')+1]
   text=stream(session,TOOL).replace('"file_path": "app.mjs", "content": "test-double"','"run_id": "'+run+'", "claimed_outcome": "The app is done"')
   return 0,text,'',False
  with patch('muse_audit.claude_adapter.collector.launch',side_effect=fake):
   with self.assertRaisesRegex(ValueError,'MCP receipt'):review_phase(root,'owner',run)
  self.assertEqual(Store(root).records(run,'owner','receipt'),[])
 def test_explicit_second_review_retains_first_attempt_and_receipt(self):
  from muse_audit.claude_adapter.collector import review_phase,TOOL
  root,work,run=self.fixture()
  def fake(argv,cwd,timeout):
   session=argv[argv.index('--session-id')+1];receipt=review_run(root,'owner',run,'The app is done')
   events=[{'type':'assistant','session_id':session,'message':{'content':[{'type':'tool_use','id':'review1','name':TOOL,'input':{'run_id':run,'claimed_outcome':'The app is done'}}]}},
    {'type':'user','session_id':session,'message':{'content':[{'type':'tool_result','tool_use_id':'review1','content':json.dumps(receipt)}]}},
    {'type':'result','subtype':'success','session_id':session,'is_error':False}]
   return 0,'\n'.join(json.dumps(e) for e in events),'',False
  with patch('muse_audit.claude_adapter.collector.launch',side_effect=fake):
   first=review_phase(root,'owner',run)
   originals={name:(root/run/name).read_bytes() for name in ('review-stream.jsonl','review-stderr.txt','review-mcp.json','completion-receipt.json')}
   second=review_phase(root,'owner',run)
  self.assertNotEqual(first['claude_review_observation']['session_id'],second['claude_review_observation']['session_id'])
  self.assertEqual(second['freshness']['prior_assurance'],'FRESH');self.assertEqual(len(Store(root).records(run,'owner','receipt')),2)
  for name,data in originals.items():self.assertEqual((root/run/name).read_bytes(),data)
  attempt=Path(second['claude_review_observation']['evidence_directory'])
  self.assertEqual(attempt.parent,root/run/'review-attempts');self.assertTrue((attempt/'completion-receipt.json').is_file())
 def test_actual_same_label_js_change_after_restart_stales_prior(self):
  from muse_audit.claude_adapter.identity import ROOT
  checkout=Path(self.tmp.name)/'checkout'
  shutil.copytree(ROOT,checkout,ignore=shutil.ignore_patterns('.git','.venv','.local','__pycache__'))
  env={**os.environ,'PYTHONPATH':str(checkout)+os.pathsep+str(checkout/'tests_adapter')}
  script="from fixture import collect;from muse_audit.claude_adapter.review import record_receipt;import json;root,work,run=collect('state');print(json.dumps({'run':run,'receipt':record_receipt(root,'owner',run,'Done')}))"
  first=json.loads(subprocess.check_output([sys.executable,'-c',script],cwd=checkout,env=env,text=True))
  verifier=checkout/'muse_audit/claude_adapter/verifier.mjs';verifier.write_text(verifier.read_text()+'\n// same-label implementation change\n')
  script="from muse_audit.claude_adapter.review import review_run;import json;print(json.dumps(review_run('state/store','owner','"+first['run']+"','Done')))"
  after=json.loads(subprocess.check_output([sys.executable,'-c',script],cwd=checkout,env=env,text=True))
  self.assertEqual(after['freshness']['prior_assurance'],'STALE');self.assertFalse(after['bindings']['implementation']['restart_required'])
 def test_full_effective_sources_covered(self):
  manifest=sources()
  for path in ['muse_audit/claude_adapter/verifier.mjs','muse_audit/claude_adapter/collector.py','muse_audit/claude_adapter/store.py','muse_audit/claude_adapter/review.py','muse_audit/task_backend/review.py','muse_audit/task_backend/runner.py','.github/workflows/offline-tests.yml']:
   if path.endswith('offline-tests.yml'):self.assertTrue(any(x.startswith('.github/workflows/') for x in manifest))
   else:self.assertIn(path,manifest)
 def test_nested_stream_ids_and_terminal_status(self):
  self.assertTrue(parse_stream(stream('s'),'s')['completed'])
  for text in [stream('other'),stream('s',error=True),stream('s').replace('tool_use_id','wrong'),'{broken',stream('s').splitlines()[0]]:
   self.assertFalse(parse_stream(text,'s')['completed'])
 def test_two_phases_restrict_tools_and_no_stop_hook(self):
  args=command('review','session','config','prompt');self.assertEqual(args[args.index('--tools')+1],'');self.assertIn('--restricted',args);self.assertIn('"disableAllHooks":true',' '.join(args));self.assertNotIn('Bash',args)
 def test_no_original_overwrite_and_sql_immutability(self):
  root,work,run=self.fixture()
  with self.assertRaises(ValueError):build(root,'owner',run)
  with self.assertRaises(Exception):Store(root).db.execute('DELETE FROM records')
if __name__=='__main__':unittest.main()
