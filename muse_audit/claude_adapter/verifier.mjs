// Independent assertions live in this parent, never in generated-code worker.
// Trusted-local generated code only; workers are not a hostile-code security sandbox.
import assert from 'node:assert/strict';
import {Worker} from 'node:worker_threads';
const tests={};let loaded=false;let id=0;
const worker=new Worker(new URL('./target-worker.mjs',import.meta.url),{workerData:process.argv[2]});
const waiting=new Map();let readyResolve,readyReject;
const ready=new Promise((resolve,reject)=>{readyResolve=resolve;readyReject=reject});
worker.on('message',m=>{
 if(Object.hasOwn(m,'ready')){if(m.ready)readyResolve();else readyReject(Error(m.error));return;}
 const entry=waiting.get(m.id);if(!entry)return;waiting.delete(m.id);
 if(m.ok)entry.resolve(m.value);else entry.reject(Error(m.error));
});
const fail=e=>{readyReject(e);for(const entry of waiting.values())entry.reject(e);waiting.clear()};
worker.on('error',fail);worker.on('exit',code=>fail(Error(`Target worker exited (${code})`)));
const call=(method,...args)=>new Promise((resolve,reject)=>{const key=++id;waiting.set(key,{resolve,reject});worker.postMessage({id:key,method,args});});
try {
 await ready;loaded=true;
 const lunch=await call('add','Lunch',1000),travel=await call('add','Travel',500);
 const validID=x=>typeof x==='string'&&x.length>0||Number.isSafeInteger(x);
 assert.ok(validID(lunch)&&validID(travel));assert.notDeepEqual(lunch,travel);
 assert.equal(await call('total'),1500);assert.deepEqual(await call('list'),[{id:lunch,label:'Lunch',cents:1000},{id:travel,label:'Travel',cents:500}]);
 await call('edit',lunch,1500);assert.equal(await call('total'),2000);
 assert.deepEqual(await call('list'),[{id:lunch,label:'Lunch',cents:1500},{id:travel,label:'Travel',cents:500}]);
 await call('remove',travel);assert.equal(await call('total'),1500);assert.deepEqual(await call('list'),[{id:lunch,label:'Lunch',cents:1500}]);
 tests.arithmetic={status:'PASS',detail:'1500 -> 2000 with Travel retained -> 1500; stable Lunch ID/label'};
 const original=await call('snapshot');assert.ok(original.storage.some(([k])=>k==='stardive.expenses.v1'));
 await call('reload');assert.deepEqual(await call('snapshot'),original);
 tests.persistence={status:'PASS',detail:'Fresh store restored exact original items/IDs/labels/total'};
 for(const amount of [-1,.5,NaN,Infinity,-Infinity,'1500',true,false,null,Number.MAX_SAFE_INTEGER+1,undefined]){
  for(const [method,args] of [['add',['Invalid',amount]],['edit',[lunch,amount]]]){
   const before=await call('snapshot');await assert.rejects(call(method,...args));assert.deepEqual(await call('snapshot'),before);
  }
 }
 tests.validation={status:'PASS',detail:'Invalid amounts rejected on add/edit, without items/total/storage mutation'};
}catch(e){
 const next=['arithmetic','persistence','validation'].find(k=>!tests[k]);
 tests[next??'arithmetic']={status:loaded?'FAIL':'UNKNOWN',detail:String(e).slice(0,1500)};
 for(const k of ['arithmetic','persistence','validation'])tests[k]??={status:'UNKNOWN',detail:'Not reached after earlier failure'};
}finally{await worker.terminate();}
console.log(JSON.stringify({schema:'stardive.fixed-node.v1',tests}));
