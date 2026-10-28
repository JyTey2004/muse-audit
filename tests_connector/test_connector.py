import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient
from muse_audit.native_connector.app import create_app
from muse_audit.native_connector.identity import files
from fixtures import config,body,TOKEN_A,TOKEN_B,TOKEN_R

class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.cfg=config(self.temp.name)
        self.app=create_app(self.cfg);self.client=TestClient(self.app,base_url="http://localhost");self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
        self.h={'Authorization':'Bearer '+TOKEN_A}
    def prepare(self,payload=None,key='request1',headers=None):
        return self.client.post('/api/tasks',json=payload or body(),headers={**(headers or self.h),'Idempotency-Key':key})
    def upload(self,task,data=b'item,amount\napples,12\nwater,8\n',version='v1',headers=None):
        return self.client.put('/api/tasks/'+task['task_id']+'/versions/'+version,content=data,headers={**(headers or self.h),'Content-Type':'application/octet-stream','If-Match':task['frozen_sha256']})
    def fixture(self):
        response=self.prepare();self.assertEqual(response.status_code,201,response.text);task=response.json();self.assertEqual(self.upload(task).status_code,201);return task
    def test_authentication_required_and_no_credentials_in_response(self):
        for h in ({},{'Authorization':'Bearer wrong'},{'Authorization':'Basic abc'}):self.assertEqual(self.client.get('/openapi.json',headers=h).status_code,401)
        self.assertNotIn(TOKEN_A,self.client.get('/openapi.json',headers=self.h).text)
    def test_normal_dynamic_request_reuses_taskflow_and_unknown(self):
        task=self.fixture();r=self.app.pilot.review('owner-a',task['task_id'],'v1');self.assertEqual(r['counts']['PASS'],3);self.assertEqual(r['counts']['UNKNOWN'],1);self.assertEqual(r['decision'],'UNRESOLVED')
        frozen=self.app.pilot.describe('owner-a',task['task_id']);self.assertEqual(frozen['frozen']['request'],body()['request'])
    def test_owner_boundary_all_reads_writes(self):
        task=self.fixture();foreign={'Authorization':'Bearer '+TOKEN_B}
        self.assertEqual(self.client.get('/api/tasks/'+task['task_id'],headers=foreign).status_code,400)
        self.assertEqual(self.upload(task,headers=foreign).status_code,400)
        with self.assertRaises(ValueError):self.app.pilot.review('owner-b',task['task_id'],'v1')
    def test_read_scope_refuses_writes(self):
        h={'Authorization':'Bearer '+TOKEN_R};self.assertEqual(self.prepare(headers=h).status_code,403)
        task=self.fixture();self.assertEqual(self.upload(task,version='v2',headers=h).status_code,403)
        self.assertEqual(self.client.post('/api/tasks/'+task['task_id']+'/receipts',json={'version_id':'v1'},headers=h).status_code,403)
    def test_original_frozen_before_artifact_no_intake_artifact_or_arbitrary_path(self):
        task=self.prepare().json();self.assertEqual(task['state'],'FROZEN')
        for field in ('artifact','root','command','url','principal'):
            payload=body();payload[field]='forbidden';self.assertEqual(self.prepare(payload,key=field).status_code,400)
    def test_idempotency_and_changed_request_need_fresh_task(self):
        a=self.prepare().json();self.assertEqual(self.prepare().json()['task_id'],a['task_id'])
        changed=body('Different actual request',30);self.assertEqual(self.prepare(changed).status_code,409)
        b=self.prepare(changed,key='new-request').json();self.assertNotEqual(a['task_id'],b['task_id']);self.assertEqual(self.app.pilot.describe('owner-a',a['task_id'])['frozen']['request'],body()['request'])
    def test_versions_preserve_failed_bytes_and_no_overwrite(self):
        task=self.fixture();changed=b'item,amount\napples,90\nwater,8\n'
        self.assertEqual(self.upload(task,changed).status_code,409);self.assertEqual(self.upload(task).status_code,201)
        self.assertEqual(self.upload(task,changed,'v2').status_code,201)
        old=self.app.pilot.review('owner-a',task['task_id'],'v1');new=self.app.pilot.review('owner-a',task['task_id'],'v2')
        self.assertEqual(old['counts']['FAIL'],0);self.assertEqual(new['counts']['FAIL'],2)
    def test_stale_contract_precondition_refused(self):
        task=self.prepare().json();task['frozen_sha256']='0'*64;self.assertEqual(self.upload(task).status_code,409)
    def test_sources_limits_base64_and_paths(self):
        for name in ('../escape','/absolute','..','x\\y'):
            payload=body();payload['sources'][0]['name']=name;self.assertEqual(self.prepare(payload,key='path'+str(len(name))).status_code,400)
        payload=body();payload['sources'][0]['content_base64']='%%%';self.assertEqual(self.prepare(payload).status_code,400)
        payload=body();payload['sources'][0]['content_base64']=base64.b64encode(b'x'*1000001).decode();self.assertEqual(self.prepare(payload).status_code,400)
        task=self.prepare().json();self.assertEqual(self.upload(task,b'x'*1000001).status_code,400)
    def test_strict_json_and_no_imported_verdict_write(self):
        r=self.client.post('/api/tasks',content='{"request":"a","request":"b"}',headers={**self.h,'Idempotency-Key':'dup','Content-Type':'application/json'});self.assertEqual(r.status_code,400)
        task=self.fixture();r=self.client.post('/api/tasks/'+task['task_id']+'/receipts',json={'version_id':'v1','receipt':{'decision':'SELECTED_CHECKS_PASS'}},headers=self.h);self.assertEqual(r.status_code,400)
    def test_non_synthetic_refused(self):
        payload=body();payload['synthetic']=False;self.assertEqual(self.prepare(payload).status_code,400)
    def test_receipt_persistence_separate_write_and_simple_view(self):
        task=self.fixture();r=self.client.post('/api/tasks/'+task['task_id']+'/receipts',json={'version_id':'v1'},headers=self.h);self.assertEqual(r.status_code,201,r.text);result=r.json()
        self.assertIn('| Check |',result['view']);self.assertIn('20',result['view']);self.assertIn('65',result['view']);self.assertIn('UNKNOWN',result['view']);self.assertNotIn('sha256',result['view'])
        self.assertEqual(self.client.get(result['result_url'],headers=self.h).content,b'item,amount\napples,12\nwater,8\n')
        self.assertEqual(self.client.get(result['details_url'],headers={'Authorization':'Bearer '+TOKEN_B}).status_code,400)
    def test_current_source_change_and_missing_evidence_block(self):
        task=self.fixture();prior=self.app.pilot.review('owner-a',task['task_id'],'v1')
        root=self.app.pilot.task('owner-a',task['task_id']);(root/'sources/items.csv').write_text('changed')
        recheck=self.app.pilot.recheck('owner-a',task['task_id'],'v1',prior);self.assertEqual(recheck['status'],'STALE');self.assertEqual(recheck['fresh']['decision'],'BLOCKED')
        (root/'sources/items.csv').unlink();self.assertEqual(self.app.pilot.review('owner-a',task['task_id'],'v1')['decision'],'BLOCKED')
    def test_artifact_same_label_changed_prior_stale_and_never_saved_pass(self):
        task=self.fixture();prior=self.app.pilot.review('owner-a',task['task_id'],'v1');root=self.app.pilot.task('owner-a',task['task_id'])
        (root/'versions/v1/picnic.csv').write_text('changed');r=self.app.pilot.recheck('owner-a',task['task_id'],'v1',prior);self.assertEqual(r['status'],'STALE');self.assertEqual(r['fresh']['decision'],'BLOCKED')
    def test_implementation_change_same_label_stales_and_blocks(self):
        task=self.fixture();prior=self.app.pilot.review('owner-a',task['task_id'],'v1');old=files()
        with patch('muse_audit.native_connector.identity.files',return_value={**old,'deploy/native-pilot/runtime-policy.json':'changed'}):
            r=self.app.pilot.recheck('owner-a',task['task_id'],'v1',prior);self.assertEqual(r['status'],'STALE');self.assertEqual(r['fresh']['decision'],'BLOCKED')
    def test_forged_prior_results_abstain_not_mint_observation(self):
        task=self.fixture();prior=self.app.pilot.review('owner-a',task['task_id'],'v1');prior['checks'][0]['status']='FAIL'
        self.assertEqual(self.app.pilot.recheck('owner-a',task['task_id'],'v1',prior)['status'],'INVALID_EVIDENCE')
    def test_origin_host_and_rate_limit(self):
        self.assertEqual(self.client.get('/openapi.json',headers={**self.h,'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/openapi.json',headers={**self.h,'Host':'evil.example'}).status_code,400)
    def test_symlink_parent_source_and_version_refused(self):
        task=self.fixture();root=self.app.pilot.task('owner-a',task['task_id']);(root/'sources/items.csv').unlink();(root/'sources').rmdir();(root/'sources').symlink_to(Path(self.temp.name))
        self.assertEqual(self.app.pilot.review('owner-a',task['task_id'],'v1')['decision'],'BLOCKED')
    def test_actual_rate_limit_and_owner_quota(self):
        app=create_app(config(Path(self.temp.name)/'limited',requests_per_minute=1))
        with TestClient(app,base_url='http://localhost') as client:
            self.assertEqual(client.get('/openapi.json',headers=self.h).status_code,200)
            self.assertEqual(client.get('/openapi.json',headers=self.h).status_code,429)
    def test_missing_version_evidence_blocks_and_stales(self):
        task=self.fixture();prior=self.app.pilot.review('owner-a',task['task_id'],'v1');root=self.app.pilot.task('owner-a',task['task_id']);(root/'versions/v1/version.json').unlink()
        result=self.app.pilot.recheck('owner-a',task['task_id'],'v1',prior);self.assertEqual(result['status'],'STALE');self.assertEqual(result['fresh']['decision'],'BLOCKED')
    def test_same_label_both_artifact_copies_changed_metadata_blocks(self):
        task=self.fixture();root=self.app.pilot.task('owner-a',task['task_id']);v=root/'versions/v1';data=b'item,amount\napples,90\nwater,8\n'
        (v/'picnic.csv').write_bytes(data);(v/'evaluation/tasks'/task['task_id']/'artifacts/picnic.csv').write_bytes(data)
        self.assertEqual(self.app.pilot.review('owner-a',task['task_id'],'v1')['decision'],'BLOCKED')
    def test_rewriting_both_frozen_copies_cannot_silently_weaken_original(self):
        import hashlib
        from muse_audit.io import canonical
        task=self.fixture();root=self.app.pilot.task('owner-a',task['task_id']);frozen=copy.deepcopy(task['frozen']);frozen['requirements'][2]['config']['max_value']=10000
        text=canonical(frozen)+'\n'
        for where in (root,root/'versions/v1/evaluation/tasks'/task['task_id']):
            (where/'frozen.json').write_text(text);(where/'frozen.sha256').write_text(hashlib.sha256(text.encode()).hexdigest()+'\n')
        self.assertEqual(self.app.pilot.review('owner-a',task['task_id'],'v1')['decision'],'BLOCKED')
    def test_internal_artifact_names_and_evaluation_symlink_refused(self):
        payload=body();payload['artifact_name']='version.json';self.assertEqual(self.prepare(payload).status_code,400)
        task=self.fixture();root=self.app.pilot.task('owner-a',task['task_id']);evaluation=root/'versions/v1/evaluation'
        evaluation.rename(root/'saved-evaluation');evaluation.symlink_to(root/'saved-evaluation')
        with self.assertRaises(ValueError):self.app.pilot.review('owner-a',task['task_id'],'v1')
    def test_changed_outer_sources_during_check_blocks(self):
        from muse_audit.taskflow.tasks import review_task as actual
        task=self.fixture();root=self.app.pilot.task('owner-a',task['task_id'])
        def raced(*args,**kwargs):
            receipt=actual(*args,**kwargs);(root/'sources/items.csv').write_text('changed during check');return receipt
        with patch('muse_audit.native_connector.service.review_task',side_effect=raced):
            self.assertEqual(self.app.pilot.review('owner-a',task['task_id'],'v1')['decision'],'BLOCKED')
    def test_schema_classifies_every_write_and_no_mutation_mcp(self):
        result=self.client.get('/openapi.json',headers=self.h);self.assertEqual(result.status_code,200)
        for route,methods in result.json()['paths'].items():
            for method,operation in methods.items():self.assertIn('WRITE:' if method in ('post','put') else 'READ:',operation['summary'])
if __name__=='__main__':unittest.main()
