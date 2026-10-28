"""Receipt export must not turn a historical service PASS into a current claim."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from muse_audit.taskflow.client import mcp_review
from muse_audit.taskflow.tasks import prepare_task, review_task


class ExportGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        source = self.base / 'notes.txt'
        source.write_text('Hello')
        self.store = self.base / 'store'
        self.task = prepare_task(self.store, 'Create a greeting note.',
            [{'id': 'greeting', 'kind': 'markdown.required_exact',
              'description': 'Include the supplied greeting', 'mode': 'must_change',
              'config': {'text': 'Hello'}}], [('notes', source, 'notes.txt')],
            'note.md', 'markdown', title='Greeting note')
        self.root = Path(self.task['task_dir'])

    def test_source_changes_after_service_response_block_exported_acceptance(self):
        (self.root / 'artifacts/note.md').write_text('Hello')
        async def observed_then_changed(*_):
            receipt = review_task(self.store, self.task['task_id'], write_outputs=False)
            (self.root / 'sources/notes.txt').write_text('Different source')
            return receipt, [{'method': 'tools/call', 'params': {'name': 'taskflow_review'},
                              'result': receipt, 'test_double': True}]
        output = self.base / 'race-output'
        with patch('muse_audit.taskflow.client._run_review', side_effect=observed_then_changed):
            result = mcp_review(self.store, self.task['task_id'], output)
        self.assertEqual(result['receipt']['decision'], 'BLOCKED')
        self.assertEqual(result['receipt']['counts']['PASS'], 0)
        raw = json.loads((output / 'observations.json').read_text())
        self.assertEqual(raw['observations'][0]['result']['counts']['PASS'], 1)
        self.assertFalse(list(output.glob('artifact-snapshot*')))

    def test_missing_deliverable_still_has_a_readable_receipt_from_real_mcp(self):
        output = self.base / 'missing-output'
        result = mcp_review(self.store, self.task['task_id'], output)
        self.assertEqual(result['receipt']['decision'], 'BLOCKED')
        self.assertEqual(result['receipt']['counts']['PASS'], 0)
        self.assertIn('missing', (output / 'receipt.md').read_text().lower())
        self.assertTrue((output / 'server-stderr.txt').is_file())
        self.assertFalse(list(output.glob('artifact-snapshot*')))

    def test_all_pass_receipt_keeps_scope_and_human_review_visible(self):
        from muse_audit.taskflow.receipt import render_readable_receipt
        (self.root / 'artifacts/note.md').write_text('Hello')
        text = render_readable_receipt(review_task(self.store, self.task['task_id'], False))
        self.assertIn('interpreted checklist', text)
        self.assertNotIn('No further check is needed', text)


if __name__ == '__main__':
    unittest.main()
