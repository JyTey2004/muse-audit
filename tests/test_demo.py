from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from muse_audit.demo import run

ROOT=Path(__file__).resolve().parents[1]


class DemoTests(unittest.TestCase):
    def test_two_jobs_and_source_change(self):
        with TemporaryDirectory() as tmp:
            target=Path(tmp)/'checkpoint'
            result=run(ROOT/'examples',target)
            self.assertEqual(result['source_change']['old_evidence'],'STALE')
            self.assertEqual(result['source_change']['changed_bindings'],['sources'])
            self.assertEqual(result['jobs']['study_summary']['after_repair']['UNKNOWN'],1)
            self.assertEqual(result['jobs']['home_office']['decision_after_repair'],'REVISE')
            self.assertTrue((target/'index.html').is_file())
            self.assertTrue((target/'study_summary-repaired/study-summary.docx').is_file())
            with self.assertRaises(ValueError):
                run(ROOT/'examples',target)
