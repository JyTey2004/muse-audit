"""Selected-input policy and quotas use manufactured fixtures, never actual user data."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient
from fixtures import config,body,TOKEN_A,TOKEN_B
from muse_audit.native_connector.app import create_app
from muse_audit.native_connector.service import Pilot
from muse_audit.native_connector.quota import stored_bytes,QuotaExceeded
from muse_audit.native_connector.config import load_config

class PolicyQuotaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.cfg=config(self.temp.name);self.h={'Authorization':'Bearer '+TOKEN_A}
    def client(self,cfg=None):
        app=create_app(cfg or self.cfg);client=TestClient(app,base_url='http://localhost');client.__enter__();self.addCleanup(client.__exit__,None,None,None);return app,client
    def create(self,app,real=False,key='one'):
        b=body();b['synthetic']=not real;return app.pilot.create('owner-a',b,key)
    def fill(self,app,real=False):
        task=self.create(app,real);app.pilot.upload('owner-a',task['task_id'],b'item,amount\napples,12\nwater,8\n',task['frozen_sha256'],'v1');return task
    def pin(self):return {str(p.relative_to(self.cfg.store)):p.read_bytes() for p in self.cfg.store.rglob('*') if p.is_file()}
    def test_default_refuses_selected_inputs_and_nonboolean_classification(self):
        app,c=self.client();b=body();b['synthetic']=False
        r=c.post('/api/tasks',json=b,headers={**self.h,'Idempotency-Key':'selected'});self.assertEqual(r.status_code,400);self.assertEqual(self.pin(),{})
        for value in (0,1,'false',None):
            b['synthetic']=value;self.assertEqual(c.post('/api/tasks',json=b,headers={**self.h,'Idempotency-Key':'bad'}).status_code,400)
    def test_selected_mode_truthful_intake_receipt_recheck_and_view(self):
        app,c=self.client(replace(self.cfg,data_policy='selected_task_inputs'));task=self.fill(app,True)
        self.assertFalse(task['synthetic']);self.assertEqual(task['data_classification'],'selected_task_inputs')
        r=app.pilot.review('owner-a',task['task_id'],'v1');self.assertFalse(r['synthetic']);self.assertEqual(r['data_classification'],'selected_task_inputs')
        self.assertEqual(app.pilot.recheck('owner-a',task['task_id'],'v1',r)['status'],'FRESH')
        saved=app.pilot.persist('owner-a',task['task_id'],'v1');self.assertIn('Selected current-task inputs',saved['view']);self.assertNotIn('synthetic',saved['view'].lower());self.assertIn('privacy unverified',saved['view'])
        self.assertEqual(r['counts']['UNKNOWN'],1)
        spec=c.get('/openapi.json',headers=self.h).json();self.assertEqual(spec['x-pilot-limits']['data_policy'],'selected_task_inputs');self.assertFalse(spec['x-pilot-limits']['synthetic_only'])
        prop=spec['paths']['/api/tasks']['post']['requestBody']['content']['application/json']['schema']['properties']['synthetic'];self.assertNotIn('const',prop)
    def test_synthetic_fixture_stays_synthetic_in_selected_mode(self):
        app,c=self.client(replace(self.cfg,data_policy='selected_task_inputs'));task=self.fill(app)
        saved=app.pilot.persist('owner-a',task['task_id'],'v1');self.assertTrue(saved['receipt']['synthetic']);self.assertIn('Declared synthetic data',saved['view'])
    def test_legacy_synthetic_metadata_is_not_reclassified(self):
        app,c=self.client();task=self.fill(app);root=app.pilot.task('owner-a',task['task_id'])
        p=root/'pilot-intake.json';record=json.loads(p.read_text());record.pop('data_policy',None);p.write_text(json.dumps(record))
        selected=Pilot(replace(self.cfg,data_policy='selected_task_inputs'));self.assertTrue(selected.describe('owner-a',task['task_id'])['synthetic'])
    def test_policy_and_quota_are_config_bound_and_loadable(self):
        self.assertEqual(self.cfg.max_stored_bytes_per_owner,256*1024*1024)
        self.assertNotEqual(self.cfg.binding(),replace(self.cfg,data_policy='selected_task_inputs').binding())
        self.assertNotEqual(self.cfg.binding(),replace(self.cfg,max_stored_bytes_per_owner=10000).binding())
        path=Path(self.temp.name)/'operator.json';path.write_text(json.dumps({'credentials':[{'principal':x.principal,'token_sha256':x.token_sha256,'scopes':list(x.scopes)} for x in self.cfg.credentials],'data_policy':'selected_task_inputs','max_stored_bytes_per_owner':123456}));path.chmod(0o600)
        loaded=load_config(path,self.cfg.store);self.assertEqual(loaded.data_policy,'selected_task_inputs');self.assertEqual(loaded.max_stored_bytes_per_owner,123456)
        path.unlink()
        for kwargs in ({'data_policy':'public'},{'max_stored_bytes_per_owner':False},{'max_stored_bytes_per_owner':0}):
            with self.assertRaises(ValueError):replace(self.cfg,**kwargs)
    def test_intake_quota_conflict_no_committed_task_and_no_prior_deletion(self):
        app,c=self.client();task=self.fill(app);before=self.pin();used=stored_bytes(self.cfg.owner_root('owner-a'))
        limited,c2=self.client(replace(self.cfg,max_stored_bytes_per_owner=used+1))
        with self.assertLogs('stardive.write_attempts',level='WARNING') as logs:
            r=c2.post('/api/tasks',json=body(),headers={**self.h,'Idempotency-Key':'new'})
        self.assertEqual(r.status_code,409);self.assertIn('Stored-byte quota exceeded',r.text);self.assertEqual(before,self.pin());self.assertIn('operation=intake',' '.join(logs.output))
    def test_upload_quota_counts_all_copies_and_metadata_without_partial_version(self):
        app,c=self.client();task=self.create(app);before=self.pin();used=stored_bytes(self.cfg.owner_root('owner-a'))
        limited,c2=self.client(replace(self.cfg,max_stored_bytes_per_owner=used+30))
        r=c2.put('/api/tasks/'+task['task_id']+'/versions/v1',content=b'item,amount\napples,12\nwater,8\n',headers={**self.h,'Content-Type':'application/octet-stream','If-Match':task['frozen_sha256']})
        self.assertEqual(r.status_code,409);self.assertEqual(before,self.pin());self.assertFalse((app.pilot.task('owner-a',task['task_id'])/'versions').exists())
    def test_receipt_quota_counts_snapshot_machine_record_and_view(self):
        app,c=self.client();task=self.fill(app);saved=app.pilot.persist('owner-a',task['task_id'],'v1');before=self.pin();used=stored_bytes(self.cfg.owner_root('owner-a'))
        limited,c2=self.client(replace(self.cfg,max_stored_bytes_per_owner=used+1))
        r=c2.post('/api/tasks/'+task['task_id']+'/receipts',json={'version_id':'v1'},headers=self.h)
        self.assertEqual(r.status_code,409);self.assertEqual(before,self.pin());self.assertEqual(c.get(saved['result_url'],headers=self.h).status_code,200)
    def test_actual_usage_includes_retained_extra_file_not_just_known_versions(self):
        app,c=self.client();root=self.cfg.owner_root('owner-a');p=root/'retained-old-evidence.bin';p.write_bytes(b'x'*10000)
        self.assertEqual(stored_bytes(root),10000);limited=Pilot(replace(self.cfg,max_stored_bytes_per_owner=10001))
        with self.assertRaises(QuotaExceeded):limited.create('owner-a',body(),'new')
        self.assertEqual(p.read_bytes(),b'x'*10000)
    def test_other_owner_quota_independent_and_scope_unchanged(self):
        app,c=self.client();root=self.cfg.owner_root('owner-a');(root/'history.bin').write_bytes(b'x'*100000)
        limited=Pilot(replace(self.cfg,max_stored_bytes_per_owner=50000));limited.create('owner-b',body(),'other-owner')
        with self.assertRaises(QuotaExceeded):limited.create('owner-a',body(),'owner-a')
    def test_current_policy_revert_blocks_new_selected_upload_without_relabeling(self):
        selected,c=self.client(replace(self.cfg,data_policy='selected_task_inputs'));task=self.create(selected,True)
        default=Pilot(self.cfg);self.assertFalse(default.describe('owner-a',task['task_id'])['synthetic'])
        with self.assertRaises(ValueError):default.upload('owner-a',task['task_id'],b'new',task['frozen_sha256'],'v1')
if __name__=='__main__':unittest.main()
