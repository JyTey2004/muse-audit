"""Backend acceptance: HTTP status, bytes and retained state, not model assertions."""
import copy
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from starlette.testclient import TestClient
from muse_audit.native_connector.app import create_app
from muse_audit.native_connector.quota import stored_bytes
from muse_audit.native_connector.identity import files
from fixtures import config,body,TOKEN_A,TOKEN_B,TOKEN_R

DATA=b'item,amount\napples,12\nwater,8\n'

class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.cfg=config(self.temp.name,requests_per_minute=10000);self.app=create_app(self.cfg)
        self.c=TestClient(self.app,base_url='http://localhost');self.c.__enter__();self.addCleanup(self.c.__exit__,None,None,None)
        self.h={'Authorization':'Bearer '+TOKEN_A};self.counter=0
    def task(self,payload=None):
        self.counter+=1;p=payload or body();p=copy.deepcopy(p)
        if payload is None:p['requirements']=p['requirements'][:3]
        r=self.c.post('/api/tasks',json=p,headers={**self.h,'Idempotency-Key':'gate-'+str(self.counter)});self.assertEqual(r.status_code,201,r.text)
        t=r.json();self.upload(t);return t
    def upload(self,t,version='v1',data=DATA):
        r=self.c.put(f"/api/tasks/{t['task_id']}/versions/{version}",content=data,headers={**self.h,'If-Match':t['frozen_sha256'],'Content-Type':'application/octet-stream'});self.assertEqual(r.status_code,201,r.text)
    def save(self,t,version='v1'):
        r=self.c.post(f"/api/tasks/{t['task_id']}/receipts",json={'version_id':version},headers=self.h);self.assertEqual(r.status_code,201,r.text);return r.json()
    def complete(self,t,s,headers=None,extra=None):
        return self.c.post(f"/api/tasks/{t['task_id']}/complete",json={'receipt_ref':s['receipt_ref'],**(extra or {})},headers=headers or self.h)
    def status(self,t):return self.c.get(f"/api/tasks/{t['task_id']}/completion",headers=self.h).json()['state']
    def root(self,t):return self.app.pilot.task('owner-a',t['task_id'])
    def pins(self):return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.cfg.store.rglob('*') if p.is_file()}
    def denied(self,t,s):
        r=self.complete(t,s);self.assertEqual(r.status_code,409,r.text);self.assertEqual(r.json()['state'],'BLOCKED')
        self.assertEqual(self.status(t),'BLOCKED');self.assertEqual(self.c.get(s['result_url'],headers=self.h).status_code,409)
    def test_skipped_receipt_blocks_without_mutation(self):
        t=self.task();before=self.pins();self.denied(t,{'receipt_ref':'receipt-missing','result_url':f"/api/tasks/{t['task_id']}/receipts/receipt-missing/result"});self.assertEqual(before,self.pins())
    def test_receipt_save_alone_never_completes_or_releases(self):
        t=self.task();s=self.save(t);self.assertEqual(s['state'],'AUDIT_SAVED');self.assertEqual(self.status(t),'BLOCKED');self.assertEqual(self.c.get(s['result_url'],headers=self.h).status_code,409)
    def test_valid_completion_idempotent_exact_bytes_and_restart(self):
        t=self.task();s=self.save(t);r=self.complete(t,s);self.assertEqual(r.status_code,200,r.text);self.assertFalse(r.json()['replayed']);before=self.pins()
        self.assertTrue(self.complete(t,s).json()['replayed']);self.assertEqual(before,self.pins());self.assertEqual(self.status(t),'COMPLETED');self.assertEqual(self.c.get(s['result_url'],headers=self.h).content,DATA)
        with TestClient(create_app(self.cfg),base_url='http://localhost') as c:self.assertEqual(c.get(s['result_url'],headers=self.h).content,DATA)
    def test_failed_verification_blocks(self):
        p=body(total=10);p['requirements']=p['requirements'][:3];t=self.task(p);self.denied(t,self.save(t))
    def test_unknown_requirement_blocks(self):
        t=self.task(body());self.denied(t,self.save(t))
    def test_unknown_mode_blocks_even_supported_kind(self):
        p=body();p['requirements']=p['requirements'][:3];p['requirements'][0]['mode']='unknown';t=self.task(p);self.denied(t,self.save(t))
    def test_forged_verdict_json_and_missing_body_rejected(self):
        t=self.task();s=self.save(t);before=self.pins()
        for extra in ({'decision':'SELECTED_CHECKS_PASS'},{'receipt':{}},{'version_id':'v1'}):self.assertEqual(self.complete(t,s,extra=extra).status_code,400)
        self.assertEqual(self.c.post(f"/api/tasks/{t['task_id']}/complete",json={},headers=self.h).status_code,400);self.assertEqual(before,self.pins())
    def test_cross_owner_task_and_readonly_scope(self):
        t=self.task();s=self.save(t);other=self.task()
        self.assertNotEqual(self.complete(t,s,headers={'Authorization':'Bearer '+TOKEN_B}).status_code,200)
        self.assertEqual(self.complete(t,s,headers={'Authorization':'Bearer '+TOKEN_R}).status_code,403)
        self.denied(other,s)
    def test_new_upload_invalidates_old_completion_nonlexical_order(self):
        t=self.task();self.upload(t,'v9');s=self.save(t,'v9');self.assertEqual(self.complete(t,s).status_code,200)
        self.upload(t,'v2');self.denied(t,s);self.assertTrue((self.root(t)/'completions'/(s['receipt_ref']+'.json')).exists())
        new=self.save(t,'v2');self.assertEqual(self.complete(t,new).status_code,200);self.assertEqual(self.c.get(new['result_url'],headers=self.h).content,DATA)
    def test_deleted_latest_version_cannot_reactivate_old_completion(self):
        import shutil
        t=self.task();s=self.save(t);self.complete(t,s);self.upload(t,'new');shutil.rmtree(self.root(t)/'versions/new');self.denied(t,s)
    def test_replayed_old_upload_does_not_change_active_version(self):
        t=self.task();s=self.save(t);self.upload(t,'v2');self.upload(t,'v1');self.denied(t,s)
    def test_changed_receipt_timestamp_blocks_before_completion(self):
        t=self.task();s=self.save(t);p=self.root(t)/'pilot-receipts'/s['receipt_ref']/'receipt.json';r=json.loads(p.read_text());r['generated_at']='forged';p.write_text(json.dumps(r));self.denied(t,s)
    def test_snapshot_tamper_blocks_completed_delivery(self):
        t=self.task();s=self.save(t);self.complete(t,s);(self.root(t)/'pilot-receipts'/s['receipt_ref']/'picnic.csv').write_bytes(b'forged result');self.denied(t,s)
    def test_missing_snapshot_blocks(self):
        t=self.task();s=self.save(t);(self.root(t)/'pilot-receipts'/s['receipt_ref']/'picnic.csv').unlink();self.denied(t,s)
    def test_changed_source_and_artifact_block(self):
        for rel in ('sources/items.csv','versions/v1/picnic.csv'):
            t=self.task();s=self.save(t);self.complete(t,s);(self.root(t)/rel).write_bytes(b'changed');self.denied(t,s)
    def test_changed_implementation_blocks(self):
        t=self.task();s=self.save(t);old=files()
        with patch('muse_audit.native_connector.identity.files',return_value={**old,'completion-policy':'changed'}):self.denied(t,s)
    def test_changed_config_blocks(self):
        t=self.task();s=self.save(t);self.app.pilot.config=replace(self.cfg,max_tasks_per_owner=101);self.denied(t,s)
    def test_legacy_receipt_without_manifest_not_promoted(self):
        t=self.task();s=self.save(t);(self.root(t)/'pilot-receipts'/s['receipt_ref']/'manifest.json').unlink();self.denied(t,s)
    def test_empty_or_incomplete_recomputed_checks_never_complete(self):
        t=self.task();s=self.save(t);original=self.app.pilot.recheck
        for checks in ([],[{'requirement_id':'columns','status':'PASS'}]):
            def incomplete(*args,**kwargs):
                value=original(*args,**kwargs);value['fresh']['checks']=checks;return value
            with patch.object(self.app.pilot,'recheck',side_effect=incomplete):self.denied(t,s)
    def test_completion_quota_rejection_preserves_all_evidence(self):
        t=self.task();s=self.save(t);before=self.pins()
        with patch('muse_audit.native_connector.completion.enforce',side_effect=__import__('muse_audit.native_connector.quota',fromlist=['QuotaExceeded']).QuotaExceeded('quota')):self.denied(t,s)
        self.assertEqual(before,self.pins())
    def test_race_evidence_changed_before_publication_blocks(self):
        import muse_audit.native_connector.completion as gate
        t=self.task();s=self.save(t);original=gate.candidate;calls=[]
        def race(*args):
            calls.append(1)
            if len(calls)==2:(self.root(t)/'sources/items.csv').write_bytes(b'changed')
            return original(*args)
        with patch.object(gate,'candidate',side_effect=race):self.assertEqual(self.complete(t,s).status_code,409)
        self.assertFalse((self.root(t)/'completions').exists())
    def test_concurrent_completion_single_immutable_record(self):
        t=self.task();s=self.save(t)
        with ThreadPoolExecutor(2) as pool:values=list(pool.map(lambda _:self.app.pilot.complete('owner-a',t['task_id'],s['receipt_ref']),range(2)))
        self.assertEqual(sorted(v['replayed'] for v in values),[False,True]);self.assertEqual(len(list((self.root(t)/'completions').iterdir())),1)
    def test_schema_declares_required_backend_gate(self):
        spec=self.c.get('/openapi.json',headers=self.h).json();self.assertTrue(spec['x-completion-policy']['required']);self.assertIn('/api/tasks/{task_id}/complete',spec['paths'])
