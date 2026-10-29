"""Fail-closed backend completion and canonical delivery; not a Muse host veto.

The owner store and process are trusted. Hashes detect changed retained evidence;
they do not claim protection against an operator rewriting the entire trusted store.
All operations run under the same owner lock as uploads and receipt publication.
"""
import tempfile
from pathlib import Path
from ..io import canonical
from ..taskflow.tasks import load_frozen
from ..taskflow.checks import SUPPORTED_KINDS
from .service import Conflict, ID_RE, read_within, strict_json, sha, now
from .quota import enforce


class CompletionBlocked(Conflict):
    pass


def blocked(reason):
    raise CompletionBlocked(reason)


def upload_head(task,allow_legacy=False):
    parent=task/'upload-events'
    if parent.is_symlink():blocked('Upload history is unavailable')
    events=sorted(parent.iterdir()) if parent.exists() else []
    if events:
        head=None
        for number,path in enumerate(events,1):
            if path.name!=f'{number:020}.json':blocked('Upload history is incomplete')
            head=strict_json(read_within(task,'upload-events/'+path.name))
            if head.get('sequence')!=number:blocked('Upload history is invalid')
        version=head.get('version_id')
        if not isinstance(version,str) or not ID_RE.fullmatch(version):blocked('Active version is invalid')
        if sha(read_within(task,f'versions/{version}/version.json'))!=head.get('version_record'):blocked('Latest uploaded version is missing or changed')
        if sha(read_within(task,'frozen.json'))!=head.get('frozen_sha256'):blocked('Original requirements changed')
        return head
    versions=task/'versions'
    if versions.is_symlink():blocked('Version history unavailable')
    prior=list(versions.iterdir()) if versions.exists() else []
    if any(strict_json(read_within(task,f'versions/{v.name}/version.json')).get('server_sequence') for v in prior):blocked('Upload history is missing')
    if allow_legacy:return None
    if len(prior)!=1:blocked('Active version is ambiguous; upload a new immutable version')
    return {'version_id':prior[0].name,'sequence':0,'legacy':True}


def candidate(pilot,principal,task_id,ref):
    if not isinstance(ref,str) or not ref.startswith('receipt-') or not ID_RE.fullmatch(ref):blocked('A valid stored receipt is required')
    task=pilot.task(principal,task_id)
    head=upload_head(task)
    prefix='pilot-receipts/'+ref+'/'
    manifest=strict_json(read_within(task,prefix+'manifest.json'))
    frozen=load_frozen(task);artifact=frozen['artifact']['name']
    if manifest.get('schema')!=1 or manifest.get('receipt_ref')!=ref or set(manifest.get('files',{}))!={'receipt.json','view.txt',artifact}:blocked('Stored receipt has no complete integrity manifest; save a fresh receipt')
    payloads={name:read_within(task,prefix+name) for name in manifest['files']}
    if any(sha(value)!=manifest['files'][name] for name,value in payloads.items()):blocked('Stored receipt or result changed')
    receipt=strict_json(payloads['receipt.json']);binding=receipt.get('pilot_binding',{})
    if binding.get('owner')!=principal or binding.get('task_id')!=task_id or binding.get('version_id')!=head['version_id']:blocked('Receipt does not cover the latest uploaded version of this task')
    current=pilot.recheck(principal,task_id,head['version_id'],receipt)
    if current['status']!='FRESH' or not current['previous_results_verified']:blocked('Verification is stale or invalid; save a fresh receipt')
    fresh=current['fresh'];requirements=frozen['requirements'];checks=fresh.get('checks',[])
    if not requirements or any(r['kind'] not in SUPPORTED_KINDS or r['mode']=='unknown' for r in requirements):blocked('The frozen checklist contains unverified or unsupported requirements')
    if len(checks)!=len(requirements) or {c.get('requirement_id') for c in checks}!={r['id'] for r in requirements}:blocked('Verification evidence is incomplete')
    if fresh.get('decision')!='SELECTED_CHECKS_PASS' or any(c.get('status')!='PASS' for c in checks):blocked('Verification did not pass every frozen requirement')
    if sha(payloads[artifact])!=binding.get('artifact'):blocked('Result does not match verified bytes')
    evidence={'receipt_ref':ref,'receipt_sha256':sha(payloads['receipt.json']),'manifest_sha256':sha(read_within(task,prefix+'manifest.json')),'pilot_binding':binding,'upload_head':head}
    return task,receipt,artifact,payloads[artifact],evidence


def record_path(task,ref):
    parent=task/'completions'
    if parent.is_symlink():blocked('Completion history unavailable')
    return parent/(ref+'.json')


def record_valid(task,ref,evidence):
    path=record_path(task,ref)
    value=strict_json(read_within(task,'completions/'+path.name))
    if value.get('state')!='COMPLETED' or value.get('evidence')!=evidence:blocked('Completion record is missing or no longer current')
    return value


def completed_view(receipt,ref,artifact):
    return {'state':'COMPLETED','receipt_ref':ref,'verified_checks':len(receipt['checks']),'result_url':f"/api/tasks/{receipt['task_id']}/receipts/{ref}/result",'details_url':f"/api/tasks/{receipt['task_id']}/receipts/{ref}",'scope':'All frozen deterministic checks passed. Checklist completeness, source authenticity, semantics and privacy remain unverified.'}


def complete(pilot,principal,task_id,ref):
    with pilot.lock(principal):
        try:
            task,receipt,artifact,data,evidence=candidate(pilot,principal,task_id,ref)
            target=record_path(task,ref)
            if target.exists():
                record_valid(task,ref,evidence)
                return {**completed_view(receipt,ref,artifact),'replayed':True}
            record={'schema':1,'state':'COMPLETED','completed_at':now(),'evidence':evidence}
            encoded=(canonical(record)+'\n').encode()
            enforce(pilot.root(principal),pilot.config.max_stored_bytes_per_owner,len(encoded),'completion')
            with tempfile.TemporaryDirectory(prefix='.completion-staging-',dir=task) as temporary:
                staged=Path(temporary)/'record.json';staged.write_bytes(encoded)
                # Recompute immediately before the single publication point.
                if candidate(pilot,principal,task_id,ref)[4]!=evidence:blocked('Evidence changed during completion')
                enforce(pilot.root(principal),pilot.config.max_stored_bytes_per_owner,0,'completion-staged')
                target.parent.mkdir(exist_ok=True);staged.rename(target)
            return {**completed_view(receipt,ref,artifact),'replayed':False}
        except (OSError,ValueError,KeyError,TypeError) as exc:
            if isinstance(exc,Conflict):raise
            blocked('A current, intact passing receipt and result are required')


def release(pilot,principal,task_id,ref):
    with pilot.lock(principal):
        try:
            task,receipt,artifact,data,evidence=candidate(pilot,principal,task_id,ref)
            record_valid(task,ref,evidence)
            # Return already-read, hash-bound bytes; never reopen after unlocking.
            return artifact,data
        except (OSError,ValueError,KeyError,TypeError) as exc:
            if isinstance(exc,Conflict):raise
            blocked('Result release requires current verified completion')


def status(pilot,principal,task_id):
    with pilot.lock(principal):
        task=pilot.task(principal,task_id)
        try:
            head=upload_head(task)
            parent=task/'completions'
            if parent.is_symlink():blocked('Completion history unavailable')
            for path in sorted(parent.iterdir()) if parent.exists() else []:
                ref=path.stem
                try:
                    _,receipt,artifact,_,evidence=candidate(pilot,principal,task_id,ref)
                    record=record_valid(task,ref,evidence)
                    return {**completed_view(receipt,ref,artifact),'completed_at':record['completed_at']}
                except (OSError,ValueError,KeyError,TypeError):continue
            return {'state':'BLOCKED','reason':'No current valid completion receipt','active_version':head['version_id']}
        except (OSError,ValueError,KeyError,TypeError):
            return {'state':'BLOCKED','reason':'Current upload or completion evidence is missing, ambiguous or changed'}
