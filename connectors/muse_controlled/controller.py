#!/usr/bin/env python3
"""Guarded publisher for the dedicated Muse workflow, using the existing backend.

Planning and drafts are untrusted. Only the backend can approve completion.
Private workflow files never become final outputs through a fallback copy.
Trust boundary: workflow/helper source and private run state are trusted; this
is not a sandbox against another process that can rewrite that trusted source.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.error
import urllib.request
import uuid

BASE='https://mcp.stardive.xyz'
HOST='mcp.stardive.xyz'
PROVIDER='custom.stardive-task-assurance'
MAX_ARTIFACT=1_000_000
MAX_BODY=4_100_000
ID=re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
NAME=re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}$')
EXT={'text':'.txt','markdown':'.md','json':'.json','csv':'.csv'}
RESERVED={'receipt.json','manifest.json','view.txt','version.json','frozen.json','pilot-intake.json'}
SCOPE='Listed checks only. Checklist completeness, source authenticity, meaning and privacy remain unverified.'

class Blocked(ValueError):pass
class BackendError(Blocked):
    def __init__(self,status,reason):self.status=status;super().__init__(reason)
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def strict(data):
    def pairs(items):
        value={}
        for k,v in items:
            if k in value:raise Blocked('Duplicate JSON fields refused')
            value[k]=v
        return value
    return json.loads(data,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(Blocked('Nonfinite JSON refused')))
def plain(name):
    if not isinstance(name,str) or not NAME.fullmatch(name) or '..' in name:raise Blocked('Plain bounded filename required')
    return name

def review_digest(receipt):
    # Timestamps differ across two real checks; every other returned field must agree.
    return sha(canonical({k:v for k,v in receipt.items() if k!='generated_at'}).encode())

class McpReview:
    """Use the installed, fixed-host, read-only MCP client and its existing broker."""
    @staticmethod
    def unpack(result):
        if not isinstance(result,dict) or result.get('isError'):raise Blocked('MCP review did not return valid check evidence')
        content=result.get('content')
        if not isinstance(content,list) or len(content)!=1 or content[0].get('type')!='text':raise Blocked('MCP review returned no unambiguous check evidence')
        receipt=strict(content[0].get('text'))
        if not isinstance(receipt,dict):raise Blocked('MCP review returned no structured check evidence')
        if 'structuredContent' in result and result['structuredContent']!=receipt:raise Blocked('MCP review evidence disagrees with its displayed result')
        return receipt
    def __call__(self,task_id,version_id):
        try:
            path=safe_components(Path(__file__).parent/'client.py')
            spec=importlib.util.spec_from_file_location('stardive_installed_mcp',path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            client=module.Client();client.initialize()
            result=client.send('tools/call',{'name':'taskflow_review','arguments':{'task_id':task_id,'version_id':version_id}})
            return self.unpack(result)
        except Blocked:raise
        except Exception:
            raise Blocked('MCP check unavailable; delivery remains blocked') from None

def safe_components(path):
    path=Path(path).absolute()
    for p in [path,*path.parents]:
        if p.is_symlink():raise Blocked('Symlink paths refused')
    return path

def read_file(root,name,limit):
    plain(name);path=safe_components(Path(root)/name)
    if not path.is_file() or path.stat().st_size>limit:raise Blocked('Required bounded input unavailable')
    with path.open('rb') as f:data=f.read(limit+1)
    if len(data)>limit:raise Blocked('Input exceeds supported size')
    return data

class Backend:
    """Fixed-origin brokered client. No key in files, args, environment or logs."""
    def __call__(self,method,path,value=None,headers=None,raw=False):
        if not (path in ('/api/tasks','/openapi.json') or re.fullmatch(r'/api/tasks/task-[a-f0-9]{16}(?:/versions/[a-zA-Z0-9_-]{1,64}|/receipts(?:/receipt-[a-f0-9]{32}(?:/result)?)?|/complete|/completion)?',path)):
            raise Blocked('Unreviewed backend path refused')
        data=value if raw else canonical(value).encode() if value is not None else None
        if data is not None and len(data)>MAX_BODY:raise Blocked('Request exceeds supported size')
        request=urllib.request.Request(BASE+path,data=data,method=method,headers=headers or {})
        if data is not None:request.add_header('Content-Type','application/octet-stream' if raw else 'application/json')
        import sys
        sys.path.insert(0,'/opt/muse/skills/custom-connector-setup/bin')
        from dynamic_credentials import add_surrogate_to_request,read_response_body
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*a,**kw):raise Blocked('Authenticated redirect refused')
        try:
            add_surrogate_to_request(request,PROVIDER,allowed_hosts=[HOST])
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=120) as response:
                body=read_response_body(response)
                return body if path.endswith('/result') else strict(body)
        except urllib.error.HTTPError as exc:
            try:reason=strict(exc.read(4096)).get('error','Backend refused this operation')
            except (ValueError,TypeError):reason='Backend refused this operation'
            raise BackendError(exc.code,str(reason)[:400]) from None
        except Blocked:raise
        except Exception:
            # Proxy/credential exceptions can contain sensitive URLs: never echo them.
            raise Blocked('Backend access unavailable; delivery remains blocked') from None

class Controller:
    def __init__(self,workdir,backend,output_root,mcp_review=None):
        self.workdir=safe_components(workdir);self.backend=backend
        self.mcp_review=mcp_review if mcp_review is not None else McpReview()
        self.private=safe_components(self.workdir/'.stardive-controlled')
        self.output_root=safe_components(output_root)
    def load(self):
        value=strict(read_file(self.private,'context.json',MAX_BODY))
        if value.get('schema')!=1:raise Blocked('Private workflow context unavailable')
        return value
    def save(self,value):
        self.private.mkdir(mode=0o700,exist_ok=True)
        safe_components(self.private/'context.json')
        with tempfile.NamedTemporaryFile(mode='w',dir=self.private,delete=False,encoding='utf-8') as f:
            f.write(canonical(value)+'\n');temp=Path(f.name)
        os.replace(temp,self.private/'context.json')
    def describe(self,ctx,state=None,reason=None,receipt=None):
        checks=[]
        if receipt:
            for c in receipt.get('checks',[]):
                checks.append({'check':c.get('description') or c.get('requirement_id'),'observed':c.get('observed'),'required':c.get('expected'),'status':c.get('status'),'reason':c.get('reason')})
        return {'state':state or ctx['state'],'task_id':ctx['task_id'],'version_id':ctx['version_id'],
            'request_sha256':ctx['request_sha256'],'artifact_name':ctx['artifact_name'],'artifact_sha256':ctx.get('artifact_sha256'),
            'receipt_ref':ctx.get('receipt_ref'),'receipt_date':receipt.get('generated_at') if receipt else None,
            'checks':checks,'reason':reason,'mcp_check':ctx.get('mcp_check'),'scope':SCOPE}
    def capabilities(self):
        spec=self.backend('GET','/openapi.json')
        catalog=spec.get('x-checker-config-schemas')
        if not isinstance(catalog,dict):raise Blocked('Live checker schemas unavailable')
        selected={k:v for k,v in catalog.items() if k.startswith(('text.','markdown.','json.','csv.'))}
        if not selected:raise Blocked('Supported checker schemas unavailable')
        return {'formats':list(EXT),'requirement_keys':['id','kind','description','mode','config'],
            'modes':['must_change','must_preserve','unknown'],'config_schemas':selected,
            'plan_keys':['artifact_name','artifact_kind','requirements','sources'],
            'example_requirement':{'id':'word_cap','kind':'text.word_limit','description':'At most45 words','mode':'must_change','config':{'max_words':45}},
            'sources':'Only additional current-task sources; original request/request.txt is added automatically',
            'scope':SCOPE}
    def prepare(self,request,plan):
        if not isinstance(request,str) or not request.strip() or len(request)>10000:raise Blocked('A normal request of at most 10000 characters is required')
        if not isinstance(plan,dict) or set(plan)!={'artifact_name','artifact_kind','requirements','sources'}:raise Blocked('Only an artifact descriptor, checklist and selected extra sources are accepted from planning')
        name=plain(plan['artifact_name']);kind=plan['artifact_kind']
        if kind not in EXT or not name.lower().endswith(EXT[kind]) or name in RESERVED:raise Blocked('This workflow supports text, Markdown, JSON and CSV files')
        if not isinstance(plan['requirements'],list) or not plan['requirements']:raise Blocked('A nonempty frozen checklist is required')
        if not isinstance(plan['sources'],list) or len(plan['sources'])>9:raise Blocked('Bounded task-selected sources required')
        sources=[{'id':'request','name':'request.txt','content_base64':base64.b64encode(request.encode()).decode()}]+plan['sources']
        for source in sources:
            if not isinstance(source,dict) or set(source)!={'id','name','content_base64'}:raise Blocked('Exact source fields required')
            plain(source['name'])
            if not isinstance(source['content_base64'],str) or len(source['content_base64'])>1_333_340:raise Blocked('Source exceeds supported size')
            try:data=base64.b64decode(source['content_base64'],validate=True)
            except ValueError:raise Blocked('Strict source base64 required') from None
            if len(data)>MAX_ARTIFACT:raise Blocked('Source exceeds supported size')
        body={'request':request,'requirements':plan['requirements'],'sources':sources,'artifact_name':name,'artifact_kind':kind,'synthetic':False}
        if (self.private/'context.json').exists():raise Blocked('This private run is already prepared; use a new run, never replace its contract')
        task=self.backend('POST','/api/tasks',body,{'Idempotency-Key':'controlled-'+uuid.uuid4().hex})
        if task.get('frozen',{}).get('request')!=request or not ID.fullmatch(task.get('task_id','')):raise Blocked('Backend did not bind the original request')
        ctx={'schema':1,'state':'FROZEN','task_id':task['task_id'],'frozen_sha256':task['frozen_sha256'],
            'request_sha256':sha(request.encode()),'artifact_name':name,'artifact_kind':kind,'version_id':'v-'+uuid.uuid4().hex,'receipt_ref':None}
        self.save(ctx);return self.describe(ctx)
    def upload(self,draft_name):
        ctx=self.load()
        if ctx['state']!='FROZEN':raise Blocked('Upload requires this run’s frozen contract')
        data=read_file(self.workdir,draft_name,MAX_ARTIFACT)
        response=self.backend('PUT',f"/api/tasks/{ctx['task_id']}/versions/{ctx['version_id']}",data,{'If-Match':ctx['frozen_sha256']},raw=True)
        if response.get('sha256')!=sha(data):raise Blocked('Upload binding did not match draft bytes')
        ctx.update(state='UPLOADED',artifact_sha256=sha(data));self.save(ctx);return self.describe(ctx)
    def require_binding(self,ctx,r):
        if not isinstance(r,dict):raise Blocked('Required structured check evidence is missing')
        binding=r.get('pilot_binding',{})
        if binding.get('task_id')!=ctx['task_id'] or binding.get('version_id')!=ctx['version_id'] or binding.get('artifact')!=ctx.get('artifact_sha256') or sha(r.get('request','').encode())!=ctx['request_sha256']:
            raise Blocked('Receipt does not match this request and draft')
    def receipt(self,ctx):
        ref=ctx.get('receipt_ref')
        if not isinstance(ref,str) or not re.fullmatch(r'receipt-[a-f0-9]{32}',ref):raise Blocked('Verification was skipped: a stored receipt is required')
        r=self.backend('GET',f"/api/tasks/{ctx['task_id']}/receipts/{ref}")
        self.require_binding(ctx,r)
        return r
    @staticmethod
    def require_pass(receipt):
        checks=receipt.get('checks')
        if receipt.get('decision')!='SELECTED_CHECKS_PASS' or not isinstance(checks,list) or not checks or any(c.get('status')!='PASS' for c in checks):
            raise Blocked('Verification did not pass every frozen requirement')
    def verify(self):
        ctx=self.load()
        if ctx['state']!='UPLOADED':raise Blocked('Verification requires an uploaded draft')
        # The late MCP review is mandatory, independently of receipt persistence.
        try:
            review=self.mcp_review(ctx['task_id'],ctx['version_id']);self.require_binding(ctx,review)
        except Blocked as exc:
            ctx['state']='BLOCKED';self.save(ctx)
            return self.describe(ctx,'BLOCKED',str(exc))
        try:self.require_pass(review);status='PASS'
        except Blocked:status='BLOCKED'
        ctx['mcp_check']={'tool':'taskflow_review','state':status,'checked_at':review.get('generated_at'),'digest':review_digest(review)};self.save(ctx)
        response=self.backend('POST',f"/api/tasks/{ctx['task_id']}/receipts",{'version_id':ctx['version_id']})
        ctx['receipt_ref']=response.get('receipt_ref');self.save(ctx)
        receipt=self.receipt(ctx)
        try:
            if review_digest(receipt)!=ctx['mcp_check']['digest']:raise Blocked('Evidence changed between the MCP check and saved receipt')
            complete=self.backend('POST',f"/api/tasks/{ctx['task_id']}/complete",{'receipt_ref':ctx['receipt_ref']})
            self.require_pass(review)
            self.require_pass(receipt)
            if complete.get('state')!='COMPLETED' or complete.get('receipt_ref')!=ctx['receipt_ref']:raise Blocked('Backend did not approve receipt-bound completion')
            ctx['state']='VERIFIED';self.save(ctx);return self.describe(ctx,'VERIFIED',receipt=receipt)
        except Blocked as exc:
            ctx['state']='BLOCKED';self.save(ctx)
            return {**self.describe(ctx,'BLOCKED',str(exc),receipt), 'backend_http':getattr(exc,'status',None)}
    def finalize(self):
        verified=self.verify()
        return self.deliver() if verified['state']=='VERIFIED' else verified
    def deliver(self):
        ctx=self.load()
        if not ctx.get('receipt_ref'):
            # Deliberate skip probes exercise the real backend refusal too. Never
            # create a receipt here: publishing cannot silently repair a skipped check.
            try:self.backend('POST',f"/api/tasks/{ctx['task_id']}/complete",{'receipt_ref':'receipt-missing'})
            except Blocked as exc:return {**self.describe(ctx,'BLOCKED','Verification was skipped: a stored receipt is required'), 'backend_http':getattr(exc,'status',None)}
            raise Blocked('Missing verification; delivery refused')
        receipt=self.receipt(ctx);self.require_pass(receipt)
        mcp=ctx.get('mcp_check',{})
        if mcp.get('tool')!='taskflow_review' or mcp.get('state')!='PASS' or not mcp.get('checked_at') or mcp.get('digest')!=review_digest(receipt):raise Blocked('Matching MCP check is required before delivery')
        if ctx['state'] not in ('VERIFIED','DELIVERED'):raise Blocked('This run has no verified delivery authorization')
        current=self.backend('GET',f"/api/tasks/{ctx['task_id']}/completion")
        if current.get('state')!='COMPLETED' or current.get('receipt_ref')!=ctx['receipt_ref']:raise Blocked('Completion is stale or no longer current')
        data=self.backend('GET',f"/api/tasks/{ctx['task_id']}/receipts/{ctx['receipt_ref']}/result")
        if not isinstance(data,bytes) or len(data)>MAX_ARTIFACT or sha(data)!=ctx.get('artifact_sha256') or sha(data)!=receipt.get('binding',{}).get('artifact',{}).get('sha256'):raise Blocked('Released bytes do not match the verified receipt')
        # Output is constructed by code, never selected by the draft worker.
        folder=safe_components(self.output_root/ctx['task_id']/ctx['receipt_ref']);folder.mkdir(parents=True,exist_ok=True)
        target=safe_components(folder/ctx['artifact_name'])
        if target.exists():
            if read_file(folder,ctx['artifact_name'],MAX_ARTIFACT)!=data:raise Blocked('Existing delivered file changed; refusing overwrite')
        else:
            fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as f:f.write(data)
            if read_file(folder,ctx['artifact_name'],MAX_ARTIFACT)!=data:raise Blocked('Published bytes changed during delivery')
        ctx['state']='DELIVERED';self.save(ctx)
        return {**self.describe(ctx,'COMPLETED',receipt=receipt),'result':{'name':ctx['artifact_name'],'path':str(target),'bytes':len(data),'sha256':sha(data)},'completion_date':current.get('completed_at')}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='operation',required=True)
    p=sub.add_parser('prepare');p.add_argument('--request-file',required=True);p.add_argument('--plan-file',required=True)
    p=sub.add_parser('upload');p.add_argument('--draft-file',required=True)
    sub.add_parser('verify');sub.add_parser('deliver');sub.add_parser('finalize');sub.add_parser('capabilities')
    args=parser.parse_args();controller=Controller(Path.cwd(),Backend(),Path.home()/'workspace/your_files/stardive-controlled')
    try:
        if args.operation=='prepare':result=controller.prepare(read_file(Path.cwd(),args.request_file,40000).decode(),strict(read_file(Path.cwd(),args.plan_file,MAX_BODY)))
        elif args.operation=='capabilities':result=controller.capabilities()
        elif args.operation=='upload':result=controller.upload(args.draft_file)
        elif args.operation=='verify':result=controller.verify()
        elif args.operation=='finalize':result=controller.finalize()
        else:result=controller.deliver()
    except Blocked as exc:
        result={'state':'BLOCKED','reason':str(exc)[:400],'result':None}
    except (OSError,ValueError,KeyError,TypeError,UnicodeError):
        result={'state':'BLOCKED','reason':'Required workflow evidence is missing, invalid or unavailable; no result delivered','result':None}
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result.get('state')!='BLOCKED' else 2
if __name__=='__main__':raise SystemExit(main())
