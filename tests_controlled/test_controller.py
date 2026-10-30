"""Controlled delivery acceptance using the actual existing ASGI backend."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests_connector'))
from fixtures import config,TOKEN_A
from muse_audit.native_connector.app import create_app
SPEC=importlib.util.spec_from_file_location('controlled',ROOT/'connectors/muse_controlled/controller.py')
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)

def plan(cap=20):return {'artifact_name':'note.txt','artifact_kind':'text','requirements':[{'id':'words','kind':'text.word_limit','description':'Keep at most '+str(cap)+' words','mode':'must_change','config':{'max_words':cap}}],'sources':[]}

class ControlledTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve()
        self.work=self.base/'private';self.work.mkdir();self.output=self.base/'your_files'
        self.app=create_app(config(self.base/'store',data_policy='selected_task_inputs',requests_per_minute=10000))
        self.client=TestClient(self.app,base_url='http://localhost:8765');self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None);self.calls=[]
        def backend(method,path,value=None,headers=None,raw=False):
            self.calls.append((method,path,value))
            h={'Authorization':'Bearer '+TOKEN_A,**(headers or {})}
            r=self.client.request(method,path,content=value if raw else None,json=None if raw else value,headers={**h,**({'Content-Type':'application/octet-stream'} if raw else {})})
            if r.status_code>=400:raise mod.BackendError(r.status_code,r.json().get('error','refused'))
            return r.content if path.endswith('/result') else r.json()
        def review(tid,vid):
            self.calls.append(('MCP','taskflow_review',{'task_id':tid,'version_id':vid}))
            r=self.client.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'taskflow_review','arguments':{'task_id':tid,'version_id':vid}}},headers={'Authorization':'Bearer '+TOKEN_A,'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2025-11-25'})
            self.assertEqual(r.status_code,200,r.text)
            return mod.McpReview.unpack(r.json()['result'])
        self.review=review;self.backend=backend;self.c=mod.Controller(self.work,backend,self.output,review)
    def prepare(self,p=None):return self.c.prepare('Write a short handover note.',p or plan())
    def upload(self,data=b'Harbor review is ready.'):
        (self.work/'draft.txt').write_bytes(data);return self.c.upload('draft.txt')
    def ready(self,p=None,data=b'Harbor review is ready.'):
        prepared=self.prepare(p);self.upload(data);return prepared
    def delivered_files(self):return list(self.output.rglob('*')) if self.output.exists() else []
    def test_compact_live_schemas_are_read_only(self):
        caps=self.c.capabilities();self.assertIn('text.word_limit',caps['config_schemas']);self.assertEqual(caps['modes'],['must_change','must_preserve','unknown']);self.assertEqual(self.calls,[('GET','/openapi.json',None)]);self.assertFalse(self.c.private.exists())
    def test_freeze_precedes_draft_and_no_output_on_prepare(self):
        state=self.prepare();self.assertEqual(state['state'],'FROZEN');self.assertFalse(self.delivered_files());self.assertFalse((self.work/'draft.txt').exists())
        tid=state['task_id'];frozen=self.app.pilot.describe('owner-a',tid)['frozen'];self.assertEqual(frozen['request'],'Write a short handover note.')
    def test_skipped_verification_blocks_with_real_backend409(self):
        self.ready();result=self.c.deliver();self.assertEqual(result['state'],'BLOCKED');self.assertEqual(result['backend_http'],409);self.assertNotIn('result',result);self.assertFalse(self.delivered_files());self.assertFalse(any('/receipts' in p and m=='POST' for m,p,_ in self.calls))
    def test_failed_verification_blocks_no_publisher(self):
        self.ready(plan(1));result=self.c.verify();self.assertEqual(result['state'],'BLOCKED');self.assertEqual(result['backend_http'],409);self.assertEqual(result['checks'][0]['status'],'FAIL')
        with self.assertRaises(mod.Blocked):self.c.deliver()
        self.assertFalse(self.delivered_files())
    def test_passing_verification_does_not_deliver_until_explicit_stage(self):
        self.ready();result=self.c.verify();self.assertEqual(result['state'],'VERIFIED');self.assertFalse(self.delivered_files());self.assertNotIn('result',result)
    def test_success_exact_gate_bytes_and_idempotent_delivery(self):
        self.ready();self.c.verify();result=self.c.deliver();self.assertEqual(result['state'],'COMPLETED');p=Path(result['result']['path']);self.assertEqual(p.read_bytes(),b'Harbor review is ready.');self.assertEqual(self.c.deliver()['result'],result['result']);self.assertTrue(any(p.endswith('/completion') for _,p,_ in self.calls));self.assertTrue(any(p.endswith('/result') for _,p,_ in self.calls))
    def test_local_draft_mutation_never_substitutes_for_verified_snapshot(self):
        self.ready();self.c.verify();(self.work/'draft.txt').write_bytes(b'Unverified changed draft');result=self.c.deliver();self.assertEqual(Path(result['result']['path']).read_bytes(),b'Harbor review is ready.')
    def test_unknown_requirement_remains_blocked(self):
        p=plan();p['requirements'].append({'id':'meaning','kind':'semantic.claim','description':'Independent semantic truth','mode':'unknown','config':{}});self.ready(p);self.assertEqual(self.c.verify()['state'],'BLOCKED');self.assertFalse(self.delivered_files())
    def test_forged_agent_pass_and_extra_planning_fields_rejected(self):
        for field in ('passed','receipt_ref','completion','request','artifact'):
            p=plan();p[field]=True
            with self.assertRaises(mod.Blocked):self.prepare(p)
        self.assertFalse(self.calls);self.assertFalse(self.delivered_files())
    def test_empty_or_unsupported_plan_blocks_before_any_backend_write(self):
        for p in ({**plan(),'requirements':[]},{**plan(),'artifact_kind':'docx'},{**plan(),'artifact_name':'receipt.json'}):
            with self.assertRaises(mod.Blocked):self.prepare(p)
        self.assertFalse(self.calls)
    def test_duplicate_prepare_preserves_original_contract(self):
        self.prepare();before=(self.c.private/'context.json').read_bytes()
        with self.assertRaises(mod.Blocked):self.c.prepare('Replace the original request',plan())
        self.assertEqual((self.c.private/'context.json').read_bytes(),before);self.assertEqual(len(self.calls),1)
    def test_changed_backend_source_blocks_delivery(self):
        state=self.ready();self.c.verify();task=self.app.pilot.task('owner-a',state['task_id']);(task/'sources/request.txt').write_bytes(b'changed')
        with self.assertRaises(mod.Blocked):self.c.deliver()
        self.assertFalse(self.delivered_files())
    def test_new_backend_version_stales_delivery(self):
        state=self.ready();self.c.verify();ctx=self.c.load();self.app.pilot.upload('owner-a',state['task_id'],b'Other version',ctx['frozen_sha256'],'newer')
        with self.assertRaises(mod.Blocked):self.c.deliver()
        self.assertFalse(self.delivered_files())
    def test_forged_local_completed_state_without_receipt_cannot_publish(self):
        self.ready();ctx=self.c.load();ctx.update(state='VERIFIED',receipt_ref='receipt-'+'a'*32);self.c.save(ctx)
        with self.assertRaises(mod.Blocked):self.c.deliver()
        self.assertFalse(self.delivered_files())
    def test_another_tasks_valid_receipt_cannot_authorize_delivery(self):
        self.ready();self.c.verify();old=self.c.load();other=self.base/'other';other.mkdir();c=mod.Controller(other,self.backend,self.output,self.review);c.prepare('Other task',plan());(other/'d.txt').write_bytes(b'Valid.');c.upload('d.txt');c.verify();ctx=c.load();ctx['receipt_ref']=old['receipt_ref'];c.save(ctx)
        with self.assertRaises(mod.Blocked):c.deliver()
        self.assertFalse(self.delivered_files())
    def test_auth_or_transport_error_never_falls_back_to_draft(self):
        self.ready();self.c.verify();self.c.backend=lambda *a,**kw:(_ for _ in ()).throw(mod.BackendError(401,'Authentication required'))
        with self.assertRaises(mod.Blocked):self.c.deliver()
        self.assertFalse(self.delivered_files())
    def test_missing_private_context_cannot_deliver(self):
        with self.assertRaises(mod.Blocked):self.c.deliver()
        self.assertFalse(self.delivered_files())
    def test_unexpected_result_bytes_refused_before_publication(self):
        self.ready();self.c.verify();actual=self.backend
        self.c.backend=lambda method,path,*a,**kw:b'forged bytes' if path.endswith('/result') else actual(method,path,*a,**kw)
        with self.assertRaises(mod.Blocked):self.c.deliver()
        self.assertFalse(self.delivered_files())
    def test_symlink_output_parent_cannot_redirect_publisher(self):
        self.ready();self.c.verify();elsewhere=self.base/'elsewhere';elsewhere.mkdir();self.output.symlink_to(elsewhere,target_is_directory=True)
        with self.assertRaises(mod.Blocked):self.c.deliver()
        self.assertEqual(list(elsewhere.iterdir()),[])
    def test_existing_changed_published_file_never_overwritten(self):
        self.ready();self.c.verify();r=self.c.deliver();p=Path(r['result']['path']);p.write_bytes(b'keep earlier changed file')
        with self.assertRaises(mod.Blocked):self.c.deliver()
        self.assertEqual(p.read_bytes(),b'keep earlier changed file')
    def test_symlink_or_oversized_draft_refused(self):
        self.prepare();real=self.work/'real.txt';real.write_bytes(b'Hello');(self.work/'draft.txt').symlink_to(real)
        with self.assertRaises(mod.Blocked):self.c.upload('draft.txt')
        with self.assertRaises(mod.Blocked):self.c.upload('../real.txt')
        real.write_bytes(b'x'*1000001)
        with self.assertRaises(mod.Blocked):self.c.upload('real.txt')
        self.assertFalse(self.delivered_files())
    def test_final_check_precedes_receipt_completion_and_release(self):
        self.ready();self.assertFalse(any(m=='MCP' for m,_,_ in self.calls));result=self.c.finalize()
        self.assertEqual(result['state'],'COMPLETED');self.assertEqual(result['mcp_check']['state'],'PASS')
        order=[('MCP' if m=='MCP' else 'receipt' if m=='POST' and p.endswith('/receipts') else 'complete' if p.endswith('/complete') else 'result' if p.endswith('/result') else '') for m,p,_ in self.calls]
        self.assertLess(order.index('MCP'),order.index('receipt'));self.assertLess(order.index('receipt'),order.index('complete'));self.assertLess(order.index('complete'),order.index('result'))
    def test_missing_mcp_blocks_without_receipt_or_output(self):
        self.ready();self.c.mcp_review=lambda *a:(_ for _ in ()).throw(mod.Blocked('MCP unavailable'))
        result=self.c.finalize();self.assertEqual(result['state'],'BLOCKED');self.assertFalse(self.delivered_files());self.assertFalse(any(m=='POST' and p.endswith('/receipts') for m,p,_ in self.calls))
    def test_mcp_from_different_task_blocks_before_persistence(self):
        self.ready()
        def wrong(*args):
            r=self.review(*args);r['pilot_binding']['task_id']='task-'+'f'*16;return r
        self.c.mcp_review=wrong;self.assertEqual(self.c.finalize()['state'],'BLOCKED');self.assertFalse(self.delivered_files());self.assertFalse(any(m=='POST' and p.endswith('/receipts') for m,p,_ in self.calls))
    def test_changed_checks_between_mcp_and_receipt_block_completion(self):
        self.ready()
        def different(*args):
            r=self.review(*args);r['checks'][0]['observed']=0;return r
        self.c.mcp_review=different;result=self.c.finalize();self.assertEqual(result['state'],'BLOCKED');self.assertIn('Evidence changed',result['reason']);self.assertFalse(any(p.endswith('/complete') for _,p,_ in self.calls));self.assertFalse(self.delivered_files())
    def test_receipt_alone_without_mcp_check_cannot_publish(self):
        self.ready();self.c.verify();ctx=self.c.load();del ctx['mcp_check'];self.c.save(ctx)
        with self.assertRaisesRegex(mod.Blocked,'Matching MCP check'):self.c.deliver()
        self.assertFalse(self.delivered_files())
    def test_mcp_error_ambiguous_and_conflicting_evidence_rejected(self):
        for result in ({'isError':True,'content':[{'type':'text','text':'{}'}]}, {'content':[]}, {'content':[{'type':'text','text':'{}'}]*2}, {'content':[{'type':'text','text':'{}'}],'structuredContent':{'different':True}}, {'content':[{'type':'text','text':'{"decision":"PASS","decision":"FAIL"}'}]}):
            with self.assertRaises(mod.Blocked):mod.McpReview.unpack(result)
    def test_action_summary_records_only_completed_controller_steps(self):
        self.prepare();self.assertEqual([a['id'] for a in self.c.load()['actions']],['request_saved'])
        self.upload();self.assertEqual([a['id'] for a in self.c.load()['actions']],['request_saved','file_prepared'])
        self.c.verify();self.assertNotIn('result_delivered',[a['id'] for a in self.c.load()['actions']])
        r=self.c.deliver();self.assertEqual([a['id'] for a in r['actions']],['request_saved','file_prepared','requirements_checked','receipt_saved','delivery_approved','result_delivered'])
        self.c.deliver();self.assertEqual(len(self.c.load()['actions']),6)
    def test_passing_card_is_private_and_uses_matched_audit(self):
        self.ready();report=self.c.finalize();r=self.c.presentation(report);p=Path(r['assurance_card']['path'])
        self.assertEqual(p.parent,self.c.private);self.assertEqual(p.name,'assurance-card.html');html=p.read_text()
        self.assertIn('1 check passed',html);self.assertIn('Audited by Stardive',html);self.assertIn('Delivered the verified file',html);self.assertNotIn('sandbox:',html)
        self.assertEqual(r['receipt_ref'],report['receipt_ref']);self.assertEqual(r['result'],report['result'])
    def test_failed_card_shows_blocked_and_never_claims_delivery(self):
        self.ready(plan(1));report=self.c.finalize();self.assertTrue(report['audit_record_matched']);r=self.c.presentation(report);html=Path(r['assurance_card']['path']).read_text()
        self.assertIn('Delivery blocked',html);self.assertIn('Audited by Stardive',html);self.assertIn('Delivery withheld',html);self.assertNotIn('Delivered the verified file',html);self.assertFalse(self.delivered_files())
    def test_skipped_card_cannot_claim_a_completed_audit(self):
        self.ready();report=self.c.deliver();r=self.c.presentation(report);html=Path(r['assurance_card']['path']).read_text()
        self.assertIn('Audit not completed',html);self.assertNotIn('Audited by Stardive',html);self.assertNotIn('Checked 0 requirements',html);self.assertFalse(self.delivered_files())
    def test_card_escapes_task_text_without_executable_injection(self):
        self.ready();report=self.c.finalize();report['checks'][0]['check']='<script>evil()</script>';report['artifact_name']='"><img src=x onerror=evil()>'
        html=Path(self.c.presentation(report)['assurance_card']['path']).read_text()
        self.assertIn('&lt;script&gt;evil()&lt;/script&gt;',html);self.assertNotIn('<script>evil()',html);self.assertNotIn('<img src=x',html);self.assertEqual(html.count('<script>'),1)
    def test_native_card_binds_the_details_request_to_an_immutable_task_record(self):
        self.ready();report=self.c.finalize();card=self.c.presentation(report)['assurance_card'];p=Path(card['registry_path']);data=json.loads(p.read_text())
        self.assertEqual(data['task_id'],report['task_id']);self.assertEqual(data['receipt_ref'],report['receipt_ref']);self.assertEqual(p.name,report['task_id']+'.json')
        self.assertEqual(data['summary']['items'][0]['data']['text'],data['detail_request']);self.assertIn(report['task_id'][5:],data['detail_request']);self.assertEqual(data['details']['items'][-1]['title'],'Audited by Stardive')
        self.assertEqual([i['title'] for i in data['details']['items'][:4]],['Saved your request','Prepared note.txt','Checked 1 requirement','Delivered the verified file'])
        self.assertFalse(data['summary']['present_now']);self.assertTrue(all(i['type']=='generic' for i in data['details']['items']))
        self.assertEqual(p.stat().st_mode&0o777,0o600);self.assertEqual(p.parent.stat().st_mode&0o777,0o700)
    def test_native_card_snapshot_never_overwrites_an_earlier_record(self):
        self.ready();report=self.c.finalize();card=self.c.presentation(report)['assurance_card'];p=Path(card['registry_path']);before=p.read_bytes()
        changed=copy.deepcopy(report);changed['artifact_name']='another.txt'
        with self.assertRaisesRegex(mod.Blocked,'cannot be overwritten'):self.c.presentation(changed)
        self.assertEqual(p.read_bytes(),before)
    def test_native_skipped_card_records_no_delivery_or_audit_claim(self):
        self.ready();report=self.c.deliver();card=self.c.presentation(report)['assurance_card'];data=json.loads(Path(card['registry_path']).read_text())
        self.assertEqual(data['summary']['items'][0]['title'],'Delivery blocked');self.assertEqual(data['details']['items'][-1]['title'],'Audit not completed · Stardive')
        self.assertNotIn('Delivered the verified file',[i['title'] for i in data['details']['items']]);self.assertIsNone(data['receipt_ref']);self.assertFalse(self.delivered_files())
    def test_card_details_is_read_only_and_never_verifies_or_delivers(self):
        self.ready();report=self.c.finalize();card=self.c.presentation(report)['assurance_card'];calls=list(self.calls);before=Path(card['registry_path']).read_bytes()
        details=self.c.card_details(report['task_id']);self.assertEqual(details['state'],'CARD_DETAILS');self.assertTrue(details['snapshot']);self.assertEqual(details['widget_args']['title'],'What Muse did')
        self.assertEqual(self.calls,calls);self.assertEqual(Path(card['registry_path']).read_bytes(),before)
        for invalid in ('../context','task-'+('f'*16)):
            with self.assertRaises(mod.Blocked):self.c.card_details(invalid)
        self.assertEqual(self.calls,calls)
if __name__=='__main__':unittest.main()
