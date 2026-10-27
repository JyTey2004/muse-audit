"""Shared requirements -> version-bound evidence -> reviewed repair -> full recheck."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import shutil
import sys
import zipfile
from openpyxl.utils.exceptions import InvalidFileException
from lxml.etree import XMLSyntaxError
from xml.etree.ElementTree import ParseError
from . import __version__
from .io import canonical, digest, read_json, safe_path, file_pin, guard_archive
from .adapters import xlsx_budget

STATES = ('PASS', 'FAIL', 'UNKNOWN', 'STALE', 'BLOCKED')


def adapters():
    from .adapters import docx_report
    return {'xlsx_budget': xlsx_budget, 'docx_report': docx_report}


def capabilities():
    return {
        'version': __version__, 'transport': 'MCP stdio via official Python SDK 1.29.0',
        'adapters': {
            'xlsx_budget': ['integer-cent source mapping', 'exact single-column SUM evaluation', 'required-cell inclusion', 'budget cap', 'protected cell'],
            'docx_report': ['exact paragraph/source quotation mapping', 'protected paragraph', 'narrow single-run repair'],
        },
        'not_supported': ['arbitrary natural-language truth', 'semantic or causal validity', 'app/browser behavior', 'PDF', 'macros', 'arbitrary spreadsheet formulas', 'authenticity of supplied sources'],
        'model_adapter': {'status':'UNCONFIGURED', 'calls_made':0, 'note':'No Meta/Muse SDK or live model invocation. Hand-authored fixture requirements and deterministic patches.'},
        'repair_policy': 'MCP is read-only. prepare_repair returns a reviewable patch; explicit local CLI command writes a NEW bundle and fully rechecks.',
        'trust_boundary': 'Caller supplies and retains approved requirements/sources. Hashes are content bindings, not signatures. Locally trusted workspace, not a hostile-file sandbox.',
    }


def load_job(workspace, relative):
    path = safe_path(workspace, relative)
    job = read_json(path)
    required = {'schema_version','job_id','title','intent','contract_version','artifact','sources','requirements'}
    if not isinstance(job, dict) or set(job) != required or type(job['schema_version']) is not int or job['schema_version'] != 1:
        raise ValueError('Job must match schema version 1 with exactly the documented fields')
    for key in ('job_id','title','intent','contract_version'):
        if not isinstance(job[key], str) or not job[key].strip() or len(job[key]) > 2000:
            raise ValueError(f'Invalid job field: {key}')
    artifact = job['artifact']
    if not isinstance(artifact, dict) or set(artifact) != {'path','version','kind'}:
        raise ValueError('Artifact requires path, version and kind')
    if not isinstance(job['sources'], list) or not 1 <= len(job['sources']) <= 20:
        raise ValueError('Provide 1 through 20 selected sources')
    ids = set()
    paths = {path.name.casefold(), 'job.json', 'receipt.json', 'repair-plan.json'}
    for item in [artifact] + job['sources']:
        if not isinstance(item, dict) or set(item) != ({'path','version','kind'} if item is artifact else {'path','version','id'}):
            raise ValueError('Invalid artifact/source fields')
        if any(not isinstance(value, str) or not value or len(value)>200 for value in item.values()):
            raise ValueError('Artifact/source descriptors must be nonempty strings')
        safe_path(path.parent, item['path'], must_exist=False)
        if item['path'].casefold() in paths:
            raise ValueError('Artifact/source paths must be distinct and cannot use reserved output metadata names (job.json, receipt.json, repair-plan.json)')
        paths.add(item['path'].casefold())
        if item is not artifact:
            if item['id'] in ids:
                raise ValueError('Duplicate source ID')
            ids.add(item['id'])
    reqs = job['requirements']
    if not isinstance(reqs, list) or not 1 <= len(reqs) <= 100:
        raise ValueError('Provide 1 through 100 explicit approved requirements')
    ids = set()
    for req in reqs:
        if not isinstance(req, dict) or set(req) != {'id','kind','description','mode','config'}:
            raise ValueError('Each requirement needs id, kind, description, mode and config')
        if any(not isinstance(req[k], str) or not req[k] or len(req[k])>2000 for k in ('id','kind','description')):
            raise ValueError('Invalid requirement text')
        if req['id'].startswith('__') or req['id'] in ids:
            raise ValueError('Requirement IDs must be distinct; __ prefix is reserved')
        ids.add(req['id'])
        if req['mode'] not in ('must_change','must_preserve','unknown') or not isinstance(req['config'], dict):
            raise ValueError('Invalid requirement mode or configuration')
    return path.parent, job


def implementation():
    root = Path(__file__).parent
    code = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*.py'))}
    return {'kernel':__version__, 'code_sha256':digest(code), 'python':sys.version.split()[0],
            'packages':{name:version(name) for name in ('mcp','openpyxl','python-docx','pydantic','lxml')}}


def binding(root, job):
    artifact = job['artifact']
    return {
        'contract_sha256':digest(job), 'contract_version':job['contract_version'],
        'artifact':{**artifact, **file_pin(safe_path(root, artifact['path'], must_exist=False))},
        'sources':{s['id']:{**s, **file_pin(safe_path(root,s['path'],must_exist=False))} for s in job['sources']},
        'implementation':implementation(),
    }


def _result(req, status, reason):
    return dict(requirement_id=req['id'],status=status,reason=reason,observed=None,expected=None,locations=[])


def audit(root, job):
    root = Path(root)
    before = binding(root, job)
    registry = adapters()
    adapter = registry.get(job['artifact']['kind'])
    checks = []
    input_error = None
    try:
        for descriptor in [job['artifact']] + job['sources']:
            path = safe_path(root, descriptor['path'])
            if path.suffix.lower() in ('.xlsx', '.docx'):
                guard_archive(path)
            elif path.suffix.lower() == '.json':
                read_json(path)
        if adapter:
            checks = adapter.evaluate(root, job)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, EOFError, InvalidFileException, XMLSyntaxError, ParseError) as exc:
        input_error = f'Input/parser unavailable or unsupported: {exc}'
    indexed = {r['requirement_id']:r for r in checks}
    ordered = []
    for req in job['requirements']:
        result = indexed.get(req['id'])
        if input_error:
            result = _result(req,'BLOCKED',input_error)
        elif result is None:
            result = _result(req,'UNKNOWN',f"No supported checker for {req['kind']!r} in artifact adapter {job['artifact']['kind']!r}. A model opinion is not evidence.")
        ordered.append({**result, 'description':req['description'], 'mode':req['mode']})
    ordered.extend({**r,'description':'Native-format coverage boundary','mode':'unknown'} for r in checks if r['requirement_id'].startswith('__'))
    after = binding(root, job)
    if canonical(before) != canonical(after):
        ordered = [{**r,'status':'STALE','reason':'Inputs changed during the audit; no current evidence was established.'} for r in ordered]
    counts = {state:0 for state in STATES}
    counts.update(Counter(c['status'] for c in ordered))
    decision = 'REVISE' if counts['FAIL'] else 'UNRESOLVED' if any(counts[s] for s in ('UNKNOWN','STALE','BLOCKED')) else 'SELECTED_CHECKS_PASS'
    return {
        'receipt_schema':1, 'job_id':job['job_id'],'title':job['title'],'intent':job['intent'],
        'generated_at':datetime.now(timezone.utc).isoformat(), 'binding':before,
        'checks':ordered, 'counts':counts, 'decision':decision,
        'coverage':{'declared_requirements':len(job['requirements']), 'extra_coverage_gates':len(ordered)-len(job['requirements']),
                    'supported_checks_executed':sum(c['status'] in ('PASS','FAIL') for c in ordered),
                    'warning':'Only the declared mappings/requirements were checked. No global artifact readiness or completeness certification.'},
        'execution':{'strategy':'full_recheck','model_calls':0,'source_authentication':False},
    }


def audit_job(workspace, relative):
    root, job = load_job(workspace, relative)
    return audit(root, job)


def semantic_receipt(receipt):
    return {key:receipt.get(key) for key in ('receipt_schema','job_id','title','intent','binding','checks','counts','decision','coverage','execution')}


def recheck(workspace, relative, prior):
    fresh = audit_job(workspace, relative)
    if not isinstance(prior, dict) or prior.get('receipt_schema') != 1 or not isinstance(prior.get('binding'), dict):
        return {'status':'INVALID_EVIDENCE','changed_bindings':[],'previous_results_verified':False,'fresh':fresh}
    changed = [key for key in fresh['binding'] if canonical(prior['binding'].get(key)) != canonical(fresh['binding'][key])]
    matches = canonical(semantic_receipt(prior)) == canonical(semantic_receipt(fresh))
    return {'status':'STALE' if changed else 'FRESH' if matches else 'INVALID_EVIDENCE',
            'changed_bindings':changed,'previous_results_verified':not changed and matches,'fresh':fresh}


def prepare_repair(workspace, relative):
    root, job = load_job(workspace, relative)
    receipt = audit(root, job)
    adapter = adapters().get(job['artifact']['kind'])
    operations = []
    if adapter and not receipt['counts']['BLOCKED'] and not receipt['counts']['STALE']:
        operations = adapter.plan(root, job)
    return {'plan_schema':1,'job_id':job['job_id'],'binding':receipt['binding'],'operations':operations,
            'policy':'Review exact before/after values. Applies only to a new output bundle; preserves contract/sources and fully rechecks all requirements.',
            'remaining_unknowns':[r['requirement_id'] for r in receipt['checks'] if r['status'] in ('UNKNOWN','BLOCKED')],
            'model_generated':False}


def apply_repair(workspace, relative, plan, output):
    """Explicit CLI-only repair. Reject stale/modified plans, never overwrite input."""
    root, job = load_job(workspace, relative)
    expected = prepare_repair(workspace, relative)
    if canonical(plan) != canonical(expected):
        raise ValueError('Repair plan is stale or modified; prepare and review a new plan')
    if not plan['operations']:
        raise ValueError('No supported automatic repair is proposed')
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be a NEW directory; no overwrite is permitted')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Build complete new bundle, recheck, then rename. Never mutate the selected bundle.
    with TemporaryDirectory(prefix='.muse-repair-', dir=output.parent) as tmp:
        target = Path(tmp) / 'bundle'
        target.mkdir()
        for source in job['sources']:
            destination = target / source['path']
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(safe_path(root,source['path']), destination)
        artifact = job['artifact']
        destination = target / artifact['path']
        destination.parent.mkdir(parents=True,exist_ok=True)
        adapters()[artifact['kind']].apply(safe_path(root,artifact['path']),destination,plan['operations'])
        repaired = deepcopy(job)
        repaired['artifact']['version'] += '+reviewed-repair'
        (target/'job.json').write_text(canonical(repaired)+'\n', encoding='utf-8')
        current_root, current_job = load_job(workspace, relative)
        if canonical(binding(current_root,current_job)) != canonical(plan['binding']):
            raise ValueError('Selected inputs changed during repair; output discarded')
        receipt = audit(target,repaired)
        (target/'receipt.json').write_text(canonical(receipt)+'\n', encoding='utf-8')
        (target/'repair-plan.json').write_text(canonical(plan)+'\n', encoding='utf-8')
        target.rename(output)
    return receipt
