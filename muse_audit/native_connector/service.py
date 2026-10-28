"""Owner-bound taskflow adapter. Every write is outside MCP; no code/URL execution."""
import base64
import hashlib
import json
import re
import tempfile
import threading
import uuid
from datetime import datetime,timezone
from pathlib import Path
from ..io import canonical,digest,no_duplicates,safe_path
from ..taskflow.tasks import prepare_task,load_frozen,resolve_task,review_task,recheck_task,checker_identity,_validate_requirements
from .view import compact_view
from .identity import identity
from ..taskflow.config_schemas import config_problem

MAX_UPLOAD=1_000_000
MAX_TOTAL=3_000_000
ID_RE=re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
NAME_RE=re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}$')
class Conflict(ValueError):pass

def strict_json(data):
    return json.loads(data,object_pairs_hook=no_duplicates,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def read_within(root,rel):
    return safe_path(root,rel).read_bytes()
def sha(data):return hashlib.sha256(data).hexdigest()
def safe_pin(root,rel):
    try:return sha(read_within(root,rel))
    except (OSError,ValueError):return None
def now():return datetime.now(timezone.utc).isoformat()
def boundary(task,version,frozen,paths):
    return {'original':{rel:safe_pin(task,rel) for rel in paths},'intake':safe_pin(task,'pilot-intake.json'),'version_record':safe_pin(version,'version.json'),'artifact':safe_pin(version,frozen['artifact']['name'])}
def plain_name(name):
    if not isinstance(name,str) or not NAME_RE.fullmatch(name) or '..' in name:raise ValueError('Plain bounded filename required')
    return name

def decode_file(item):
    if not isinstance(item,dict) or set(item)!={'id','name','content_base64'}:raise ValueError('Source needs id, name and content_base64 only')
    if not isinstance(item['id'],str) or not ID_RE.fullmatch(item['id']):raise ValueError('Bounded source ID required')
    plain_name(item['name'])
    if not isinstance(item['content_base64'],str) or len(item['content_base64'])>MAX_UPLOAD*4//3+8:raise ValueError('Source too large')
    try:data=base64.b64decode(item['content_base64'],validate=True)
    except Exception as e:raise ValueError('Strict base64 source required') from e
    if len(data)>MAX_UPLOAD:raise ValueError('Source too large')
    return data

class Pilot:
    def __init__(self,config):
        self.config=config;self.locks={};self.lock_guard=threading.Lock()
        config.store.mkdir(parents=True,exist_ok=True,mode=0o700)
        for principal in {c.principal for c in config.credentials}:
            root=config.owner_root(principal)
            if root.is_symlink():raise ValueError('Symlinked owner store refused')
            root.mkdir(mode=0o700,exist_ok=True)
    def root(self,principal):
        if principal not in {c.principal for c in self.config.credentials}:raise ValueError('Unknown configured principal')
        p=self.config.owner_root(principal)
        if p.is_symlink() or p.resolve()!=p:raise ValueError('Owner root changed')
        return p
    def lock(self,principal):
        with self.lock_guard:return self.locks.setdefault(principal,threading.RLock())
    def task(self,principal,task_id):
        return resolve_task(self.root(principal),task_id)
    def create(self,principal,body,idempotency_key):
        if not isinstance(body,dict) or set(body)!={'request','requirements','sources','artifact_name','artifact_kind','synthetic'}:raise ValueError('Explicit request/checklist/sources/artifact descriptor/synthetic fields required; no artifact or path accepted at intake')
        if identity()['restart_required']:raise Conflict('Restart required after implementation changes')
        if body['synthetic'] is not True:raise ValueError('This private pilot accepts synthetic task data only')
        plain_name(body['artifact_name'])
        if body['artifact_name'] in {'version.json','pilot-intake.json','view.txt','evaluation'}:raise ValueError('Artifact name collides with retained evidence')
        if not isinstance(idempotency_key,str) or not ID_RE.fullmatch(idempotency_key):raise ValueError('Bounded Idempotency-Key required')
        if not isinstance(body['sources'],list) or not 1<=len(body['sources'])<=10:raise ValueError('One through ten selected sources required')
        _validate_requirements(body['requirements'])
        for requirement in body['requirements']:
            problem=config_problem(requirement['kind'],requirement['config'])
            if problem:raise ValueError(problem)
        sources=[(item,decode_file(item)) for item in body['sources']]
        if len({item['id'] for item,_ in sources})!=len(sources) or len({item['name'] for item,_ in sources})!=len(sources):raise ValueError('Source IDs and names must each be distinct')
        if sum(len(d) for _,d in sources)>MAX_TOTAL:raise ValueError('Combined source limit exceeded')
        fingerprint=digest(body)
        with self.lock(principal):
            root=self.root(principal);tasks=root/'tasks';index=root/'intakes'
            if index.is_symlink() or tasks.is_symlink():raise ValueError('Input index/task parent symlink refused')
            key_hash=sha(idempotency_key.encode());key=index/(key_hash+'.json')
            # Retain old d9e0a44 idempotency records; new commits keep the key with the task.
            if key.exists():
                record=strict_json(read_within(root,'intakes/'+key.name))
                if record['input_hash']!=fingerprint:raise Conflict('Idempotency key belongs to different original requirements')
                return self.describe(principal,record['task_id'])
            existing=list(tasks.iterdir()) if tasks.exists() else []
            for prior in existing:
                if prior.is_symlink():raise ValueError('Symlinked task refused')
                metadata=prior/'pilot-intake.json'
                if metadata.is_file():
                    record=strict_json(read_within(prior,'pilot-intake.json'))
                    if record.get('idempotency_key_sha256')==key_hash:
                        if record['input_hash']!=fingerprint:raise Conflict('Idempotency key belongs to different original requirements')
                        return self.describe(principal,prior.name)
            if len(existing)>=self.config.max_tasks_per_owner:raise Conflict('Pilot owner task limit reached')
            # One commit point: the fully frozen task and intake metadata are staged on
            # the same filesystem, then atomically renamed. Cleanup owns only this NEW
            # staging directory; no rejected intake deletes an existing task or evidence.
            with tempfile.TemporaryDirectory(prefix='.intake-staging-',dir=root) as temporary:
                staging=Path(temporary);selection=[]
                for i,(item,data) in enumerate(sources):
                    p=staging/str(i);p.write_bytes(data);selection.append((item['id'],p,item['name']))
                task=prepare_task(staging,body['request'],body['requirements'],selection,body['artifact_name'],body['artifact_kind'])
                staged=Path(task['task_dir'])
                self.write_once(staged/'pilot-intake.json',{'schema':1,'synthetic':True,'origin':'caller-supplied request, interpreted checklist and source bytes; not independent source authenticity','owner':principal,'input_hash':fingerprint,'idempotency_key_sha256':key_hash,'frozen_sha256':sha(read_within(staged,'frozen.json')),'configuration':self.config.binding(),'created_at':now()})
                tasks.mkdir(exist_ok=True)
                target=tasks/task['task_id']
                if target.exists() or target.is_symlink():raise Conflict('Fresh task collision; no overwrite')
                staged.rename(target)
            return self.describe(principal,task['task_id'])
    @staticmethod
    def write_once(path,value):
        with Path(path).open('x',encoding='utf-8') as f:f.write(canonical(value)+'\n')
    def describe(self,principal,task_id):
        task=self.task(principal,task_id);frozen=load_frozen(task)
        return {'task_id':task_id,'frozen':frozen,'frozen_sha256':sha((task/'frozen.json').read_bytes()),'state':'FROZEN' if not (task/'versions').exists() else 'ARTIFACT_VERSIONS_AVAILABLE','synthetic':True,'scope':'Only listed checks; interpreted coverage and source authenticity remain unresolved'}
    def upload(self,principal,task_id,data,expected_frozen,version_id):
        if not isinstance(data,bytes) or len(data)>MAX_UPLOAD:raise ValueError('Bounded raw artifact bytes required')
        if not isinstance(version_id,str) or not ID_RE.fullmatch(version_id):raise ValueError('Bounded artifact version ID required')
        with self.lock(principal):
            task=self.task(principal,task_id)
            if sha(read_within(task,'frozen.json'))!=expected_frozen:raise Conflict('Original contract binding changed; prepare a fresh task')
            frozen=load_frozen(task);versions=task/'versions'
            if versions.is_symlink():raise ValueError('Version parent symlink refused')
            versions.mkdir(exist_ok=True)
            target=versions/version_id
            if target.exists():
                existing=read_within(target,frozen['artifact']['name'])
                if existing!=data:raise Conflict('Version ID cannot overwrite earlier bytes')
                return {'task_id':task_id,'version_id':version_id,'sha256':sha(data),'replayed':True}
            if len(list(versions.iterdir()))>=self.config.max_versions_per_task:raise Conflict('Version limit reached')
            # Stage the complete version before atomic publication; partial uploads never look finalized.
            with tempfile.TemporaryDirectory(prefix='version-staging-',dir=task) as temporary:
                staged=Path(temporary)
                self.write_once(staged/'version.json',{'version_id':version_id,'sha256':sha(data),'bytes':len(data),'observed_at':now(),'origin':'caller-uploaded artifact, not a tool-success assertion'})
                (staged/frozen['artifact']['name']).write_bytes(data)
                inner=staged/'evaluation'/'tasks'/task_id;inner.mkdir(parents=True)
                for name in ('frozen.json','frozen.sha256'):(inner/name).write_bytes(read_within(task,name))
                (inner/'sources').mkdir();(inner/'artifacts').mkdir();(inner/'outputs').mkdir()
                for source in frozen['sources']:
                    selected=read_within(task,'sources/'+source['name'])
                    if len(selected)>MAX_UPLOAD:raise ValueError('Frozen source too large')
                    (inner/'sources'/source['name']).write_bytes(selected)
                (inner/'artifacts'/frozen['artifact']['name']).write_bytes(data)
                staged.rename(target)
            return {'task_id':task_id,'version_id':version_id,'sha256':sha(data),'replayed':False}
    def version(self,principal,task_id,version_id):
        if not isinstance(version_id,str) or not ID_RE.fullmatch(version_id):raise ValueError('Version ID refused')
        task=self.task(principal,task_id);version=task/'versions'/version_id
        if (task/'versions').is_symlink() or version.is_symlink() or not version.is_dir():raise ValueError('Unknown version')
        return task,version
    def review(self,principal,task_id,version_id):
        with self.lock(principal):
            task,version=self.version(principal,task_id,version_id);frozen=load_frozen(task)
            # Compare canonical original inputs with evaluation copy every time, never just the label.
            inner=version/'evaluation'/'tasks'/task_id
            original_paths=['frozen.json','frozen.sha256']+['sources/'+s['name'] for s in frozen['sources']]
            before_boundary=boundary(task,version,frozen,original_paths)
            before_identity=identity()
            problems=['Hosted implementation changed after process load; restart required'] if before_identity['restart_required'] else []
            if not safe_pin(task,'pilot-intake.json') or not safe_pin(version,'version.json'):problems.append('Required intake/version evidence missing')
            try:
                intake=strict_json(read_within(task,'pilot-intake.json'));record=strict_json(read_within(version,'version.json'))
                if intake.get('owner')!=principal or intake.get('frozen_sha256')!=safe_pin(task,'frozen.json'):problems.append('Original intake/request binding changed')
                data=read_within(version,frozen['artifact']['name'])
                if record.get('version_id')!=version_id or record.get('sha256')!=sha(data) or record.get('bytes')!=len(data):problems.append('Version label does not match originally stored bytes')
            except (ValueError,OSError,TypeError,AttributeError):problems.append('Intake/version binding unavailable')
            for rel in original_paths:
                try:
                    if read_within(task,rel)!=read_within(inner,rel):problems.append(rel)
                except (ValueError,OSError):problems.append(rel)
            artifact=version/frozen['artifact']['name'];evaluated=inner/'artifacts'/frozen['artifact']['name']
            try:
                if read_within(version,frozen['artifact']['name'])!=read_within(inner,'artifacts/'+frozen['artifact']['name']):problems.append('artifact version bytes')
            except (ValueError,OSError):problems.append('artifact version bytes')
            safe_path(version,'evaluation/tasks/'+task_id+'/frozen.json')
            receipt=review_task(version/'evaluation',task_id,write_outputs=False)
            after_boundary=boundary(task,version,frozen,original_paths)
            after_identity=identity()
            if before_boundary!=after_boundary:problems.append('Original/version bytes changed during verification')
            if before_identity!=after_identity:problems.append('Hosted implementation changed during verification')
            if problems:
                for check in receipt['checks']:check.update(status='BLOCKED',reason='Original/version evidence missing or changed: '+', '.join(problems),observed=None)
                receipt['counts']={'BLOCKED':max(1,len(receipt['checks']))};receipt['decision']='BLOCKED';receipt['block_reason']='Original/version bindings differ'
            receipt['pilot_binding']={'owner':principal,'task_id':task_id,'version_id':version_id,'configuration':self.config.binding(),
                'intake':after_boundary['intake'],'version_record':after_boundary['version_record'],
                'original_files':after_boundary['original'],'implementation':after_identity,
                'artifact':after_boundary['artifact']}
            receipt['synthetic']=True
            return receipt
    def recheck(self,principal,task_id,version_id,prior):
        fresh=self.review(principal,task_id,version_id)
        if not isinstance(prior,dict):return {'status':'INVALID_EVIDENCE','fresh':fresh,'previous_results_verified':False}
        changed=prior.get('binding')!=fresh.get('binding') or prior.get('pilot_binding')!=fresh.get('pilot_binding')
        semantic=('receipt_schema','task_id','title','request','coverage','checks','counts','decision','synthetic')
        equal=all(canonical(prior.get(k))==canonical(fresh.get(k)) for k in semantic)
        return {'status':'STALE' if changed else 'FRESH' if equal else 'INVALID_EVIDENCE','fresh':fresh,'previous_results_verified':not changed and equal,
            'origin':'Prior JSON assertions are untrusted; all checks recomputed'}
    def persist(self,principal,task_id,version_id):
        with self.lock(principal):
            task,version=self.version(principal,task_id,version_id);receipt=self.review(principal,task_id,version_id)
            outputs=task/'pilot-receipts'
            if outputs.is_symlink():raise ValueError('Receipt parent symlink refused')
            outputs.mkdir(exist_ok=True)
            if len(list(outputs.iterdir()))>=self.config.max_receipts_per_task:raise Conflict('Receipt limit reached')
            ref='receipt-'+uuid.uuid4().hex;folder=outputs/ref;folder.mkdir()
            frozen=load_frozen(task);artifact=version/frozen['artifact']['name']
            if receipt['decision']!='BLOCKED':
                data=read_within(version,frozen['artifact']['name'])
                current=self.review(principal,task_id,version_id)
                keys=('binding','pilot_binding','checks','counts','decision','request','coverage')
                if any(canonical(receipt.get(k))!=canonical(current.get(k)) for k in keys):raise Conflict('Evidence changed after review; no completion receipt saved')
                if sha(data)!=receipt['pilot_binding']['artifact']:raise Conflict('Artifact changed during receipt persistence')
                (folder/frozen['artifact']['name']).write_bytes(data)
            self.write_once(folder/'receipt.json',receipt)
            view=compact_view(receipt,ref,frozen['artifact']['name'],frozen['requirements'])
            (folder/'view.txt').write_text(view)
            return {'receipt_ref':ref,'view':view,'receipt':receipt,'result_url':f'/api/tasks/{task_id}/receipts/{ref}/result','details_url':f'/api/tasks/{task_id}/receipts/{ref}'}
