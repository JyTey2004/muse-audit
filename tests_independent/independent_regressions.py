"""Adversarial acceptance checks authored outside the implementation package."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
sys.path.insert(0, str(args.source.resolve()))
from muse_audit.taskflow.tasks import prepare_task, review_task, recheck_task
from muse_audit.taskflow.receipt import render_readable_receipt

results = []


def run_case(name, function):
    try:
        detail = function()
        results.append({'case': name, 'passed': True, 'detail': detail})
    except Exception as exc:
        results.append({'case': name, 'passed': False,
                        'error': type(exc).__name__ + ': ' + str(exc)})


with tempfile.TemporaryDirectory() as temp:
    base = Path(temp).resolve()
    store = base / 'store'
    source = base / 'facts.txt'
    source.write_text('Supplied synthetic task facts.\n')

    def prepared(kind, config, content, artifact_kind='json'):
        name = {'json': 'result.json', 'csv': 'result.csv',
                'markdown': 'result.md', 'xlsx': 'result.xlsx'}[artifact_kind]
        task = prepare_task(store, 'Create a fresh task result from supplied facts.',
            [{'id': 'condition', 'kind': kind, 'description': 'Requested check',
              'mode': 'must_change', 'config': config}],
            [('facts', source, 'facts.txt')], name, artifact_kind)
        root = Path(task['task_dir'])
        artifact = root / 'artifacts' / name
        if content is not None:
            artifact.write_text(content, encoding='utf-8')
        return task, root, artifact

    def must_not_pass(kind, config, content, artifact_kind='json'):
        try:
            task, root, artifact = prepared(kind, config, content, artifact_kind)
            receipt = review_task(store, task['task_id'], write_outputs=False)
        except ValueError as exc:
            return {'validation_refused': str(exc)}
        assert receipt['counts'].get('PASS', 0) == 0, receipt['checks']
        assert receipt['decision'] != 'SELECTED_CHECKS_PASS', receipt
        return {'decision': receipt['decision'], 'checks': receipt['checks']}

    run_case('unknown_json_predicate_cannot_pass', lambda: must_not_pass(
        'json.unsupported_truth', {'field': 'x', 'expected': True}, '{"x":true}'))
    run_case('nested_json_booleans_are_not_numbers', lambda: must_not_pass(
        'json.field_exact', {'field': 'x', 'expected': {'count': 0}},
        '{"x":{"count":false}}'))
    run_case('duplicate_json_keys_are_ambiguous', lambda: must_not_pass(
        'json.field_exact', {'field': 'x', 'expected': 7}, '{"x":6,"x":7}'))
    run_case('nonfinite_json_is_invalid', lambda: must_not_pass(
        'json.field_exact', {'field': 'x', 'expected': 7}, '{"x":7,"unused":NaN}'))
    run_case('nonfinite_csv_cannot_be_under_budget', lambda: must_not_pass(
        'csv.total_cap', {'column': 'amount', 'max_value': 65},
        'amount\n-Infinity\n', 'csv'))
    run_case('duplicate_csv_headers_cannot_pass', lambda: must_not_pass(
        'csv.columns', {'columns': ['amount', 'amount']}, 'amount,amount\n3,4\n', 'csv'))

    def decimal_case():
        task, _, _ = prepared('csv.total_cap', {'column': 'amount', 'max_value': 0.3},
                              'amount\n0.1\n0.2\n', 'csv')
        receipt = review_task(store, task['task_id'], write_outputs=False)
        assert receipt['counts']['PASS'] == 1, receipt['checks']
        return receipt['checks']
    run_case('exact_decimal_sum_at_cap', decimal_case)

    def symlink_case(target_kind):
        task, root, artifact = prepared('json.field_exact', {'field': 'x', 'expected': 7}, '{"x":7}')
        target = artifact if target_kind == 'artifact' else root / 'sources/facts.txt'
        outside = base / ('outside-' + task['task_id'])
        outside.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(outside)
        try:
            receipt = review_task(store, task['task_id'], write_outputs=False)
        except ValueError as exc:
            return {'refused': str(exc)}
        assert receipt['counts'].get('PASS', 0) == 0, receipt['checks']
        return receipt['decision']
    run_case('artifact_symlink_is_refused', lambda: symlink_case('artifact'))
    run_case('source_symlink_with_identical_bytes_is_refused', lambda: symlink_case('source'))

    def forged_identity():
        task, _, _ = prepared('json.field_exact', {'field': 'x', 'expected': 7}, '{"x":7}')
        receipt = review_task(store, task['task_id'], write_outputs=False)
        receipt['task_id'] = 'task-forged-identity'
        receipt['title'] = 'A different user-facing task'
        receipt['request'] = 'A different original request'
        checked = recheck_task(store, task['task_id'], receipt)
        assert not checked['previous_results_verified'], checked
        assert checked['status'] != 'FRESH', checked
        return checked['status']
    run_case('forged_task_identity_is_not_fresh', forged_identity)

    def native_guard():
        task, root, artifact = prepared('xlsx.preserve_cell',
            {'sheet': 'Budget', 'cell': 'B12', 'expected': 'Keep existing monitor'},
            None, 'xlsx')
        original = args.source / 'examples/home_office/budget.xlsx'
        with zipfile.ZipFile(original) as src, zipfile.ZipFile(artifact, 'w') as dst:
            for item in src.infolist():
                data = src.read(item.filename)
                if item.filename == 'xl/workbook.xml':
                    data = b'<!DOCTYPE workbook>\n' + data
                dst.writestr(item, data)
        try:
            receipt = review_task(store, task['task_id'], write_outputs=False)
        except ValueError as exc:
            return {'refused': str(exc)}
        assert receipt['counts'].get('PASS', 0) == 0, receipt['checks']
        return receipt['decision']
    run_case('native_archive_guard_survives_wrapper', native_guard)

    def immutable_output():
        task, root, artifact = prepared('json.field_exact', {'field': 'x', 'expected': 7}, '{"x":7}')
        original = artifact.read_bytes()
        review_task(store, task['task_id'], write_outputs=True)
        artifact.write_text('{"x":9}')
        candidates = [f for f in (root / 'outputs').rglob('*') if f.is_file()]
        assert any(f.read_bytes() == original for f in candidates), 'No original deliverable snapshot retained'
        return {'original_artifact_retained': True}
    run_case('prior_receipt_retains_delivered_bytes', immutable_output)

    def readable_scope():
        task, _, _ = prepared('json.field_exact', {'field': 'x', 'expected': 7}, '{"x":7}')
        receipt = review_task(store, task['task_id'], write_outputs=False)
        text = render_readable_receipt(receipt)
        assert any(word in text.lower() for word in ['interpreted', 'checklist', 'scope']), text
        assert 'No further check is needed' not in text, text
        return {'interpreted_scope_visible': True}
    run_case('human_receipt_discloses_scope', readable_scope)

    def loaded_identity():
        copied = base / 'copied-source'
        shutil.copytree(args.source / 'muse_audit', copied / 'muse_audit',
                        ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('requirements.txt', 'constraints-python312.txt', 'pyproject.toml', 'run_mcp.py'):
            shutil.copyfile(args.source / name, copied / name)
        code = '''from pathlib import Path
from muse_audit.taskflow.tasks import prepare_task,review_task,recheck_task
b=Path('case');b.mkdir();s=b/'facts.txt';s.write_text('supplied')
t=prepare_task(b/'store','Create a note',[{'id':'a','kind':'markdown.required_exact','description':'Include Hello','mode':'must_change','config':{'text':'Hello'}}],[('facts',s,'facts.txt')],'note.md','markdown')
(Path(t['task_dir'])/'artifacts/note.md').write_text('Hello')
first=review_task(b/'store',t['task_id'],write_outputs=False)
p=Path('muse_audit/io.py');p.write_text(p.read_text()+'\\n# bytes changed after process load\\n')
fresh=review_task(b/'store',t['task_id'],write_outputs=False)
assert fresh['counts'].get('PASS',0)==0, fresh
checked=recheck_task(b/'store',t['task_id'],first)
assert not checked['previous_results_verified'], checked
print('loaded code changes refused')
'''
        completed = subprocess.run([sys.executable, '-c', code], cwd=copied,
                                   text=True, capture_output=True)
        assert completed.returncode == 0, completed.stderr[-2400:]
        return completed.stdout.strip()
    run_case('all_effective_code_and_loaded_state_are_bound', loaded_identity)

def serializable(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {'invalid_json_number': repr(value)}
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serializable(v) for v in value]
    return value


args.output.write_text(json.dumps({'source': str(args.source), 'results': serializable(results),
    'passed': sum(r['passed'] for r in results), 'total': len(results)}, indent=2,
    allow_nan=False) + '\n')
print(json.dumps({'passed': sum(r['passed'] for r in results), 'total': len(results),
                  'failures': [r['case'] for r in results if not r['passed']]}))
sys.exit(0 if all(r['passed'] for r in results) else 1)
