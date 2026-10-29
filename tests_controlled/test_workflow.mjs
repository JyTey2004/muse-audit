import fs from 'node:fs';
import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('../connectors/muse_controlled/workflow.js',import.meta.url),'utf8');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
const compile=s=>new AsyncFunction('args','phase','agent','parallel','pipeline','log',s.replace('export const meta','const meta'));
const tid='task-'+'a'.repeat(16),vid='v-'+'b'.repeat(32),ref='receipt-'+'c'.repeat(32),hash='d'.repeat(64),req='e'.repeat(64);
const base={task_id:tid,version_id:vid,request_sha256:req,artifact_name:'note.txt',artifact_sha256:hash,receipt_ref:null,receipt_date:null,checks:[],reason:null};
const frozen={...base,state:'FROZEN',artifact_sha256:null};
const uploaded={...base,state:'UPLOADED'};
const verified={...base,state:'VERIFIED',receipt_ref:ref,receipt_date:'2026-10-29T08:00:00+00:00',checks:[{check:'words',observed:5,required:20,status:'PASS'}]};
const delivered={...verified,state:'COMPLETED',result:{name:'note.txt',path:`/home/hatch/workspace/your_files/stardive-controlled/${tid}/${ref}/note.txt`,bytes:25,sha256:hash}};
const phases=[];const cases=[];
async function run(name,changes={},inputs={request:'Create a short note.'},text=source){
 const calls=[];const returns={freeze:frozen,'draft-upload':uploaded,verify:verified,deliver:delivered,...changes};
 const result=await compile(text)(inputs,n=>phases.push(n),async (prompt,options)=>{calls.push(options.key);await Promise.resolve();const value=returns[options.key];if(value instanceof Error){value.calls=[...calls];throw value;}return structuredClone(value);},null,null,()=>{});
 return {name,result,calls};
}
async function blocked(name,changes={},options={}){
 const r=await run(name,changes,options.inputs,options.source);assert.equal(r.result.__hatchWorkflowControl,'blocked',name);assert.equal(r.result.result.state,'BLOCKED');assert.equal(r.result.result.result,undefined);assert.equal(r.result.result.result_path,undefined);
 if(options.noDelivery!==false)assert.ok(!r.calls.includes('deliver'),name+' invoked publisher');cases.push({case:name,state:'BLOCKED',calls:r.calls});
}
const success=await run('valid result');assert.equal(success.result.state,'COMPLETED');assert.equal(success.result.result.path,delivered.result.path);assert.equal(success.result.receipt.reference,ref);assert.ok(success.result.message.includes(ref));assert.ok(success.result.message.includes('| Check |'));cases.push({case:'valid result',state:'COMPLETED',calls:success.calls});
await blocked('no request',{}, {inputs:{}});
await blocked('caller bypass flag',{}, {inputs:{request:'Create a note',skip_verification:true}});
await blocked('freeze missing',{freeze:null});
await blocked('freeze blocked',{freeze:{state:'BLOCKED',reason:'Unsupported requirement'}});
await blocked('upload task mismatch',{'draft-upload':{...uploaded,task_id:'task-'+'f'.repeat(16)}});
await blocked('upload request binding mismatch',{'draft-upload':{...uploaded,request_sha256:'f'.repeat(64)}});
await blocked('verification skipped',{verify:null});
await blocked('verification failure',{verify:{...verified,state:'BLOCKED',checks:[{status:'FAIL'}]}});
await blocked('forged completed state instead of verification',{verify:{...verified,state:'COMPLETED',passed:true}});
await blocked('empty check evidence',{verify:{...verified,checks:[]}});
await blocked('unknown check',{verify:{...verified,checks:[{status:'UNKNOWN'}]}});
await blocked('missing receipt',{verify:{...verified,receipt_ref:null}});
await blocked('missing receipt date',{verify:{...verified,receipt_date:null}});
await blocked('verification artifact mismatch',{verify:{...verified,artifact_sha256:'f'.repeat(64)}});
await assert.rejects(run('verification stage error',{verify:new Error('provider error')}),error=>{assert.ok(!error.calls.includes('deliver'));return /provider error/.test(error.message);});cases.push({case:'provider error propagates without publisher',state:'FAILED_NO_DELIVERY'});
await assert.rejects(run('durable runtime suspension',{freeze:new Error('runtime suspension')}),/runtime suspension/);cases.push({case:'runtime suspension is never swallowed by a catch',state:'PROPAGATED'});
await blocked('publisher refusal',{deliver:{state:'BLOCKED',reason:'stale'}},{noDelivery:false});
await blocked('publisher wrong receipt',{deliver:{...delivered,receipt_ref:'receipt-'+'f'.repeat(32)}},{noDelivery:false});
await blocked('publisher changed bytes hash',{deliver:{...delivered,result:{...delivered.result,sha256:'f'.repeat(64)}}},{noDelivery:false});
await blocked('publisher draft path',{deliver:{...delivered,result:{...delivered.result,path:'/home/hatch/workspace/private/draft.data'}}},{noDelivery:false});
await blocked('publisher traversal',{deliver:{...delivered,result:{...delivered.result,path:'/tmp/../home/hatch'+delivered.result.path.slice('/home/hatch'.length)}}},{noDelivery:false});
await blocked('deliberate omission test snapshot',{'skip-probe':{state:'BLOCKED',reason:'Verification skipped',backend_http:409}},{source:source.replace('const SKIP_VERIFICATION_TEST = false','const SKIP_VERIFICATION_TEST = true')});
console.log(JSON.stringify({mode:'Asynchronous workflow JavaScript harness with Promise-returning stages; separate actual Muse runs required',passed:cases.length,cases},null,2));
