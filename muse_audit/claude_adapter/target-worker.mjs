// No generated-code imports, Node globals, host callbacks or eval are exposed.
// Node vm is NOT a security sandbox; this is for trusted local generated code only.
import {parentPort,workerData} from 'node:worker_threads';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
let store,create,storage,snapshot;
try {
 const context=vm.createContext(Object.create(null),{codeGeneration:{strings:false,wasm:false}});
 const module=new vm.SourceTextModule(readFileSync(workerData,'utf8'),{context,
  importModuleDynamically:()=>{throw Error('Unsupported dynamic import')}});
 await module.link(()=>{throw Error('Unsupported import: app.mjs must be a self-contained pure JS module')});
 await module.evaluate({timeout:1000});create=module.namespace.createExpenseStore;
 if(typeof create!=='function')throw Error('Missing createExpenseStore export');
 const helpers=vm.runInContext(`(()=>{const data=new Map();return {storage:{getItem:k=>data.get(k)??null,setItem:(k,v)=>{if(k!=='stardive.expenses.v1'||typeof v!=='string')throw Error('Invalid persistence write');data.set(k,v)}},snapshot:()=>[...data]}})()`,context);
 storage=helpers.storage;snapshot=helpers.snapshot;store=create(storage);parentPort.postMessage({ready:true});
}catch(e){parentPort.postMessage({ready:false,error:String(e)});}
parentPort.on('message',({id,method,args})=>{
 try {
  let value;
  if(method==='reload'){store=create(storage);value=true;}
  else if(method==='snapshot'){value={items:store.list(),total:store.total(),storage:snapshot()};}
  else if(['add','edit','remove','list','total'].includes(method)){value=store[method](...args);}
  else throw Error('Unsupported fixed-check operation');
  parentPort.postMessage({id,ok:true,value});
 }catch(e){parentPort.postMessage({id,ok:false,error:String(e)});}
});
