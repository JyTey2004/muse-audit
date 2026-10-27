import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ImplementationTests(unittest.TestCase):
    def copy(self, root):
        shutil.copytree(ROOT/'muse_audit', root/'muse_audit', ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('requirements.txt','constraints-python312.txt','pyproject.toml','run_mcp.py'):
            shutil.copyfile(ROOT/name, root/name)

    def run_copy(self, root, code):
        return subprocess.run([sys.executable, '-c', code], cwd=root, env={**os.environ, 'PYTHONPATH': str(root)}, capture_output=True, text=True, check=True)

    def test_every_effective_source_module_is_in_manifest(self):
        from muse_audit.task_backend.identity import implementation
        r = implementation()
        for name in ('review.py','runner.py','contracts.py','store.py','provider.py','server.py','identity.py','cli.py','demo.py','__init__.py'):
            self.assertIn('muse_audit/task_backend/'+name, r['sources'])
        self.assertIn('muse_audit/io.py', r['sources'])
        self.assertIn('muse_audit/core.py', r['sources'])
        self.assertFalse(r['source_changed_since_process_start'])

    def test_same_label_actual_predicate_change_stales_prior_receipt_after_restart(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d);self.copy(root)
            create = """
import json
from muse_audit.task_backend.runner import Runner
from muse_audit.task_backend.contracts import create_contract,approve_contract,expense_contract
r=Runner('store');c=create_contract(r.store,r.owner,expense_contract());approve_contract(r.store,r.owner,c['contract_id'],c['contract_hash'],reviewed=True);run=r.start(c['contract_id']);p=r.review(run);open('run.txt','w').write(run);open('before.json','w').write(json.dumps(p))
"""
            self.run_copy(root, create)
            file = root/'muse_audit/task_backend/contracts.py'
            file.write_text(file.read_text().replace('len(contract[\'request\']) <= 10000', 'len(contract[\'request\']) <= 9999'))
            r = self.run_copy(root, """
import json
from muse_audit.task_backend.runner import Runner
r=Runner('store');p=r.review(open('run.txt').read());before=json.load(open('before.json'));assert p['implementation']['revision_label']==before['implementation']['revision_label'];assert p['conditions'][0]['status']==before['conditions'][0]['status'];assert p['freshness']['prior_assurance']=='STALE';assert p['bindings']['implementation']!=before['bindings']['implementation'];assert not p['completion_assured'];print('same-label mutation: STALE')
""")
            self.assertIn('STALE', r.stdout)

    def test_loaded_code_disk_edit_fails_closed_and_requires_restart(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d);self.copy(root)
            result = self.run_copy(root, """
from pathlib import Path
from muse_audit.task_backend.runner import Runner
from muse_audit.task_backend.contracts import create_contract,approve_contract,expense_contract
r=Runner('store');c=create_contract(r.store,r.owner,expense_contract());approve_contract(r.store,r.owner,c['contract_id'],c['contract_hash'],reviewed=True);run=r.start(c['contract_id']);r.review(run)
f=Path('muse_audit/task_backend/review.py');f.write_text(f.read_text()+'\\n# actual on-disk implementation mutation\\n');p=r.review(run);assert p['restart_required'];assert p['freshness']['prior_assurance']=='STALE';assert p['counts']=={'UNKNOWN':5};assert not p['completion_assured'];print('restart required; no fresh PASS from changed disk code')
""")
            self.assertIn('restart required', result.stdout)


if __name__ == '__main__':
    unittest.main()
