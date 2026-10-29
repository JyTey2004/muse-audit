"""Real loopback TCP HTTP + official SDK MCP. Synthetic auth and data; NOT Muse acceptance."""
import asyncio
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
import httpx
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from muse_audit.native_connector.app import create_app
from fixtures import config,body,TOKEN_A,TOKEN_B,TOKEN_R

def pins(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*') if p.is_file()}
def unpack(response):
    if response.isError:raise AssertionError(str(response.content))
    return response.structuredContent or json.loads(response.content[0].text)

async def exercise(base,cfg):
    headers={'Authorization':'Bearer '+TOKEN_A};observations=[]
    async with httpx.AsyncClient(base_url=base,headers=headers,timeout=20,trust_env=False) as http:
        assert (await http.get('/openapi.json',headers={'Authorization':'Bearer wrong'})).status_code==401
        payload=body();payload['synthetic']=cfg.data_policy!='selected_task_inputs'
        task_response=await http.post('/api/tasks',json=payload,headers={'Idempotency-Key':'normal-picnic-1'});assert task_response.status_code==201,task_response.text
        task=task_response.json();assert task['state']=='FROZEN';tid=task['task_id']
        upload=await http.put(f'/api/tasks/{tid}/versions/v1',content=b'item,amount\napples,12\nwater,8\n',headers={'Content-Type':'application/octet-stream','If-Match':task['frozen_sha256']});assert upload.status_code==201,upload.text
        before=pins(cfg.store)
        async with streamable_http_client(base+'/mcp',http_client=http) as (read,write,_):
            async with ClientSession(read,write) as client:
                init=await client.initialize();observations.append({'method':'initialize','result':init.model_dump(mode='json')})
                listed=await client.list_tools();observations.append({'method':'tools/list','result':listed.model_dump(mode='json')})
                assert sorted(t.name for t in listed.tools)==['taskflow_capabilities','taskflow_recheck','taskflow_review']
                assert all(t.annotations.readOnlyHint for t in listed.tools)
                caps_response=await client.call_tool('taskflow_capabilities',{});caps=unpack(caps_response)
                openapi=(await http.get('/openapi.json')).json()
                assert caps['config_schemas']==openapi['x-checker-config-schemas']
                assert caps['data_policy']==cfg.data_policy
                assert caps['limits']['max_stored_bytes_per_owner']==cfg.max_stored_bytes_per_owner
                assert openapi['x-pilot-limits']['data_policy']==cfg.data_policy
                assert caps['config_schemas']['markdown.word_limit']['additionalProperties'] is False
                observations.append({'method':'tools/call','params':{'name':'taskflow_capabilities','arguments':{}},'raw_result':caps_response.model_dump(mode='json')})
                assert all('root' not in t.inputSchema.get('properties',{}) and 'principal' not in t.inputSchema.get('properties',{}) and 'command' not in t.inputSchema.get('properties',{}) for t in listed.tools)
                response=await client.call_tool('taskflow_review',{'task_id':tid,'version_id':'v1'});first=unpack(response);observations.append({'method':'tools/call','params':{'name':'taskflow_review','arguments':{'task_id':tid,'version_id':'v1'}},'raw_result':response.model_dump(mode='json')})
                assert first['synthetic'] is payload['synthetic'];assert first['active_data_policy']==cfg.data_policy
                assert first['counts']['PASS']==3 and first['counts']['UNKNOWN']==1,first
                recheck=unpack(await client.call_tool('taskflow_recheck',{'task_id':tid,'version_id':'v1','prior_receipt':first}));assert recheck['status']=='FRESH'
                assert pins(cfg.store)==before,'Read-only MCP changed persistent bytes'
                assert (await client.call_tool('taskflow_review',{'task_id':'../other','version_id':'v1'})).isError
                # Valid separate upload creates different bytes in another immutable version.
                changed=await http.put(f'/api/tasks/{tid}/versions/v2',content=b'item,amount\napples,90\nwater,8\n',headers={'Content-Type':'application/octet-stream','If-Match':task['frozen_sha256']});assert changed.status_code==201
                before_changed=pins(cfg.store)
                result=unpack(await client.call_tool('taskflow_recheck',{'task_id':tid,'version_id':'v2','prior_receipt':first}));assert result['status']=='STALE' and result['fresh']['counts']['FAIL']==2,result
                assert pins(cfg.store)==before_changed
                observations.append({'method':'tools/call','params':{'name':'taskflow_recheck','version_id':'v2'},'result':result})
        async with httpx.AsyncClient(base_url=base,headers={'Authorization':'Bearer '+TOKEN_B},timeout=20,trust_env=False) as foreign:
            async with streamable_http_client(base+'/mcp',http_client=foreign) as (r,w,_):
                async with ClientSession(r,w) as client:
                    await client.initialize();assert (await client.call_tool('taskflow_review',{'task_id':tid,'version_id':'v1'})).isError
        saved_response=await http.post(f'/api/tasks/{tid}/receipts',json={'version_id':'v1'});assert saved_response.status_code==201,saved_response.text;saved=saved_response.json()
        result=await http.get(saved['result_url']);assert result.status_code==409 # UNKNOWN and superseded version cannot release
        assert 'receipt' not in saved
        details=(await http.get(saved['details_url'])).json();assert details['counts']['UNKNOWN']==1
        assert details['synthetic'] is payload['synthetic']
        if not payload['synthetic']:assert 'Selected current-task inputs' in saved['view'] and 'synthetic' not in saved['view'].lower()
        # Reproduce the reported intake failure through actual HTTP, not only the service API.
        before_rejected=pins(cfg.store);duplicate=payload.copy();duplicate['sources']=payload['sources']*2
        rejected=await http.post('/api/tasks',json=duplicate,headers={'Idempotency-Key':'duplicate-sources'})
        assert rejected.status_code==400 and pins(cfg.store)==before_rejected
        bad_word=body();bad_word.update(artifact_name='note.md',artifact_kind='markdown')
        bad_word['requirements']=[{'id':'word_cap','kind':'markdown.word_limit','description':'Between 50 and 100 words','mode':'must_change','config':{'max_words':100,'min_words':50}}]
        before_rejected=pins(cfg.store);rejected=await http.post('/api/tasks',json=bad_word,headers={'Idempotency-Key':'unsupported-minimum'})
        assert rejected.status_code==400 and pins(cfg.store)==before_rejected
        word=body();word.update(artifact_name='note.md',artifact_kind='markdown')
        word['requirements']=[{'id':'word_cap','kind':'markdown.word_limit','description':'Maximum 100 words','mode':'must_change','config':{'max_words':100}}]
        word_response=await http.post('/api/tasks',json=word,headers={'Idempotency-Key':'word-count-request'});assert word_response.status_code==201;word_task=word_response.json()
        word_upload=await http.put(f"/api/tasks/{word_task['task_id']}/versions/v1",content=b'Hi there.',headers={'Content-Type':'application/octet-stream','If-Match':word_task['frozen_sha256']});assert word_upload.status_code==201
        async with streamable_http_client(base+'/mcp',http_client=http) as (r,w,_):
            async with ClientSession(r,w) as client:
                await client.initialize();before_word=pins(cfg.store)
                response=await client.call_tool('taskflow_review',{'task_id':word_task['task_id'],'version_id':'v1'});word_receipt=unpack(response)
                assert word_receipt['checks'][0]['observed']==2 and word_receipt['checks'][0]['status']=='PASS'
                assert pins(cfg.store)==before_word
                observations.append({'method':'tools/call','params':{'name':'taskflow_review','arguments':{'task_id':word_task['task_id'],'version_id':'v1'}},'raw_result':response.model_dump(mode='json')})
        word_save=await http.post(f"/api/tasks/{word_task['task_id']}/receipts",json={'version_id':'v1'});assert word_save.status_code==201
        word_saved=word_save.json();assert 'Word count 2; maximum 100' in word_saved['view'] and 'Total 2' not in word_saved['view']
        assert (await http.get(word_saved['result_url'])).status_code==409
        completed=await http.post(f"/api/tasks/{word_task['task_id']}/complete",json={'receipt_ref':word_saved['receipt_ref']});assert completed.status_code==200,completed.text
        assert (await http.get(word_saved['result_url'])).content==b'Hi there.'
        return {'disclosure':'Real loopback HTTP/SDK MCP, synthetic credentials and data; no Muse/model/HTTPS ingress tested','protocol':init.protocolVersion,'read_only_store_bytes':'UNCHANGED','scoped_auth':'401 invalid token; cross-owner MCP refused','data_policy':cfg.data_policy,'synthetic_declaration':payload['synthetic'],'first':first['counts'],'changed_version':{'status':'STALE','FAIL':2},'saved':saved,'word_saved':word_saved,'review_fixes':{'duplicate_intake':'400; no persistent changes','unsupported_minimum':'400; no persistent changes','word_cap_summary':'Word count, not budget','capability_schemas':'Exact live/OpenAPI match'},'observations':observations}

class HTTPProtocolTests(unittest.TestCase):
    def test_actual_tcp_http_initialize_list_review_recheck_and_receipt(self):
        result=run_protocol();self.assertEqual(result['protocol'],'2025-11-25')
    def test_selected_input_mode_actual_http_mcp_classification_and_readonly(self):
        result=run_protocol(selected_task_inputs=True);self.assertFalse(result['synthetic_declaration']);self.assertEqual(result['data_policy'],'selected_task_inputs')

def run_protocol(output=None,selected_task_inputs=False):
    with tempfile.TemporaryDirectory() as temp:
        cfg=config(Path(temp)/'store',data_policy='selected_task_inputs' if selected_task_inputs else 'synthetic_only');app=create_app(cfg)
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error',access_log=False))
        thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
        try:
            deadline=time.monotonic()+10
            while not server.started and time.monotonic()<deadline:time.sleep(.02)
            if not server.started:raise AssertionError('Loopback service failed startup')
            result=asyncio.run(asyncio.wait_for(exercise(f'http://127.0.0.1:{port}',cfg),60))
            if output:
                import shutil
                output=Path(output);output.mkdir(parents=True,exist_ok=False);shutil.copytree(cfg.store,output/'synthetic-store');(output/'protocol.json').write_text(json.dumps(result,indent=2));(output/'compact-view.txt').write_text(result['saved']['view']);(output/'word-view.txt').write_text(result['word_saved']['view'])
            return result
        finally:server.should_exit=True;thread.join(timeout=10);sock.close()
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output');p.add_argument('--selected-task-inputs',action='store_true');a=p.parse_args();r=run_protocol(a.output,a.selected_task_inputs);print(json.dumps({k:v for k,v in r.items() if k not in ('observations','saved')},indent=2));print(r['saved']['view'])
