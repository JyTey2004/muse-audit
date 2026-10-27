from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from docx import Document
from muse_audit.adapters import docx_report
from muse_audit.fixtures_docx import build_fixture


class DocxReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.job = build_fixture(self.root)

    def results(self):
        return {r["requirement_id"]: r for r in docx_report.evaluate(self.root, self.job)}

    def test_reads_native_docx_and_reports_counterexample(self):
        result = self.results()["quoted-duration"]
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("30 minutes", result["observed"])
        self.assertIn("20 minutes", result["expected"])
        self.assertEqual(result["locations"], ["study-log.txt:line:2", "study-summary.docx:paragraph:3"])
        self.assertEqual(self.results()["preserve-title"]["status"], "PASS")
        self.assertNotIn("causal-effect", self.results())  # Unsupported kinds belong to shared kernel.

    def test_failure_then_guarded_repair_and_preservation(self):
        operations = docx_report.plan(self.root, self.job)
        self.assertEqual(len(operations), 1)
        source, output = self.root / "study-summary.docx", self.root / "fixed.docx"
        original_bytes = source.read_bytes()
        docx_report.apply(source, output, operations)
        self.assertEqual(source.read_bytes(), original_bytes)
        with ZipFile(source) as before, ZipFile(output) as after:
            self.assertEqual(before.namelist(), after.namelist())
            for name in before.namelist():
                if name != "word/document.xml":
                    self.assertEqual(before.read(name), after.read(name), name)
        self.job["artifact"]["path"] = "fixed.docx"
        self.assertTrue(all(r["status"] == "PASS" for r in self.results().values()))
        self.assertEqual(Document(output).paragraphs[0].style.name, "Title")
        self.assertEqual(docx_report.plan(self.root, self.job), [])

    def test_source_change_changes_expected_result_without_version_change(self):
        (self.root / "study-log.txt").write_text("Synthetic\nEach practice session lasted 30 minutes.\n", encoding="utf-8")
        self.assertEqual(self.results()["quoted-duration"]["status"], "PASS")

    def test_protected_content_failure_never_gets_a_repair(self):
        self.job["requirements"][1]["config"]["expected"] = "Different approved title"
        self.assertEqual(self.results()["preserve-title"]["status"], "FAIL")
        self.assertEqual([op["requirement_id"] for op in docx_report.plan(self.root, self.job)], ["quoted-duration"])

    def test_quote_marked_must_preserve_is_not_automatically_changed(self):
        self.job["requirements"][0]["mode"] = "must_preserve"
        self.assertEqual(self.results()["quoted-duration"]["status"], "FAIL")
        self.assertEqual(docx_report.plan(self.root, self.job), [])

    def test_missing_mapped_paragraph_fails(self):
        self.job["requirements"][0]["config"]["paragraph_index"] = 99
        self.assertEqual(self.results()["quoted-duration"]["status"], "FAIL")
        self.assertEqual(docx_report.plan(self.root, self.job), [])

    def test_missing_source_line_is_unknown(self):
        self.job["requirements"][0]["config"]["source_line"] = 99
        self.assertEqual(self.results()["quoted-duration"]["status"], "UNKNOWN")

    def test_invalid_index_and_extra_mapping_never_pass(self):
        self.job["requirements"][0]["config"]["paragraph_index"] = True
        self.assertEqual(self.results()["quoted-duration"]["status"], "UNKNOWN")
        self.job["requirements"][0]["config"]["paragraph_index"] = 3
        self.job["requirements"][0]["config"]["unsupported"] = True
        self.assertEqual(self.results()["quoted-duration"]["status"], "UNKNOWN")

    def test_complex_document_has_explicit_coverage_gap(self):
        path = self.root / "study-summary.docx"
        doc = Document(path)
        doc.add_table(rows=1, cols=1).cell(0, 0).text = "Unmapped table claim"
        doc.save(path)
        self.assertEqual(self.results()["__docx_coverage__"]["status"], "UNKNOWN")

    def test_multiple_runs_are_readable_but_not_auto_repaired(self):
        path = self.root / "study-summary.docx"
        doc = Document(path)
        doc.paragraphs[2].add_run(" Extra formatting.").bold = True
        doc.save(path)
        self.assertEqual(self.results()["quoted-duration"]["status"], "FAIL")
        self.assertEqual(docx_report.plan(self.root, self.job), [])

    def test_stale_patch_before_text_is_rejected(self):
        operations = docx_report.plan(self.root, self.job)
        operations[0]["before"] = "Not the current paragraph"
        with self.assertRaisesRegex(ValueError, "precondition"):
            docx_report.apply(self.root / "study-summary.docx", self.root / "fixed.docx", operations)
        self.assertFalse((self.root / "fixed.docx").exists())

    def test_duplicate_and_overwrite_repairs_are_rejected(self):
        operations = docx_report.plan(self.root, self.job)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            docx_report.apply(self.root / "study-summary.docx", self.root / "fixed.docx", operations * 2)
        with self.assertRaisesRegex(ValueError, "never overwrite"):
            docx_report.apply(self.root / "study-summary.docx", self.root / "study-summary.docx", operations)

    def test_outside_source_mapping_cannot_read(self):
        self.job["sources"][0]["path"] = "../outside.txt"
        self.assertEqual(self.results()["quoted-duration"]["status"], "UNKNOWN")

    def test_corrupt_docx_is_blocked(self):
        (self.root / "study-summary.docx").write_text("Not a DOCX")
        self.assertTrue(all(r["status"] == "BLOCKED" for r in self.results().values()))


if __name__ == "__main__":
    unittest.main()
