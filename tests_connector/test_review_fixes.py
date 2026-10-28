"""Regression repros for the three independent d9e0a44 observations."""
import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient
from fixtures import config,body,TOKEN_A
from muse_audit.native_connector.app import create_app,schema
from muse_audit.taskflow.config_schemas import schemas

def paths(root):return sorted(str(p.relative_to(root)) for p in Path(root).rglob('*'))
class IndependentFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.cfg=config(self.tmp.name);self.app=create_app(self.cfg);self.client=TestClient(self.app,base_url='http://localhost');self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
        self.headers={'Authorization':'Bearer '+TOKEN_A,'Idempotency-Key':'fresh'}
    def test_duplicate_ids_names_and_invalid_requirements_leave_no_partial_intake(self):
        root=Path(self.tmp.name)
        variants=[]
        for field in ('id','name','both'):
            b=body();other=copy.deepcopy(b['sources'][0])
            if field=='id':other['name']='different.csv'
            if field=='name':other['id']='different'
            b['sources'].append(other);variants.append(b)
        b=body();b['requirements'][0]['mode']='invalid';variants.append(b)
        for b in variants:
            before=paths(root);r=self.client.post('/api/tasks',json=b,headers=self.headers)
            self.assertEqual(r.status_code,400);self.assertEqual(paths(root),before)
    def test_aborted_staging_does_not_publish_or_consume_task_quota(self):
        from muse_audit.native_connector.service import Pilot
        before=paths(Path(self.tmp.name))
        with patch.object(Pilot,'write_once',side_effect=ValueError('injected intake metadata failure')):
            self.assertEqual(self.client.post('/api/tasks',json=body(),headers=self.headers).status_code,400)
        self.assertEqual(paths(Path(self.tmp.name)),before)
        good=self.client.post('/api/tasks',json=body(),headers=self.headers);self.assertEqual(good.status_code,201)
    def test_rejected_new_intake_preserves_existing_files_byte_for_byte(self):
        self.assertEqual(self.client.post('/api/tasks',json=body(),headers=self.headers).status_code,201)
        root=Path(self.tmp.name);before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        bad=body();bad['sources']*=2
        self.assertEqual(self.client.post('/api/tasks',json=bad,headers={**self.headers,'Idempotency-Key':'bad'}).status_code,400)
        after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()};self.assertEqual(before,after)
    def test_native_intake_rejects_extra_config_for_each_new_family(self):
        cases=[('markdown.word_limit',{'max_words':100,'min_words':50}),('text.required_exact',{'text':'Hi','ignore_case':True}),('json.field_exact',{'field':'x','expected':7,'tolerance':1}),('csv.total_cap',{'column':'amount','max_value':65,'min_value':50})]
        for kind,cfg in cases:
            b=body();b['requirements'][0].update(kind=kind,config=cfg)
            before=paths(Path(self.tmp.name));r=self.client.post('/api/tasks',json=b,headers=self.headers)
            self.assertEqual(r.status_code,400);self.assertEqual(paths(Path(self.tmp.name)),before)
    def test_schema_exposes_exact_config_catalog(self):
        s=self.client.get('/openapi.json',headers=self.headers).json();self.assertEqual(s['x-checker-config-schemas'],schemas())
        self.assertIn('oneOf',s['components']['schemas']['TaskflowRequirement'])
    def test_word_cap_id_is_word_count_not_budget_and_failure_reason_is_present(self):
        b=body();b.update(artifact_name='note.md',artifact_kind='markdown')
        b['requirements']=[{'id':'word_cap','kind':'markdown.word_limit','description':'Maximum 100 words','mode':'must_change','config':{'max_words':100}}]
        t=self.client.post('/api/tasks',json=b,headers=self.headers).json()
        self.app.pilot.upload('owner-a',t['task_id'],b'Hi there.',t['frozen_sha256'],'v1')
        result=self.app.pilot.persist('owner-a',t['task_id'],'v1');view=result['view']
        self.assertIn('Word count 2; maximum 100',view);self.assertNotIn('Total 2',view)
        self.assertIn('Reason',view);self.assertIn('Meaning and real-world accuracy',view)
        self.assertNotIn('sha256',view)
        b['requirements'][0]['config']={'max_words':1}
        t=self.client.post('/api/tasks',json=b,headers={**self.headers,'Idempotency-Key':'failed-word-task'}).json()
        self.app.pilot.upload('owner-a',t['task_id'],b'Hi there.',t['frozen_sha256'],'v1')
        failed=self.app.pilot.persist('owner-a',t['task_id'],'v1')['view'];self.assertIn('FAIL',failed);self.assertIn('Word count exceeds',failed)
if __name__=='__main__':unittest.main()
