"""Regression tests for the independent review defects in taskflow v2.

Each test reproduces a reported false pass or missing guard, then
asserts the corrected behaviour. All fixtures are synthetic and local.
"""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docx import Document

from muse_audit.taskflow.client import mcp_review
from muse_audit.taskflow.receipt import render_readable_receipt
from muse_audit.taskflow.tasks import (
    TaskBlocked,
    prepare_task,
    recheck_task,
    repair_task,
    review_task,
)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _req(req_id, kind, description, config, mode="must_change"):
    return {"id": req_id, "kind": kind, "description": description, "mode": mode, "config": config}


class V2TestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.store = self.base / "store"
        self.store.mkdir()
        self.inputs = self.base / "inputs"
        self.inputs.mkdir()

    def _source(self, name, data):
        path = self.inputs / name
        path.write_text(data, encoding="utf-8") if isinstance(data, str) else path.write_bytes(data)
        return path

    def _prepare(self, request, requirements, sources, artifact_name, artifact_kind):
        return prepare_task(
            self.store, request, requirements,
            [(sid, path, name) for sid, path, name in sources],
            artifact_name, artifact_kind,
        )

    def _status(self, receipt, req_id):
        for check in receipt["checks"]:
            if check["requirement_id"] == req_id:
                return check["status"]
        self.fail(f"Missing check: {req_id}")

    def test_unknown_json_kind_stays_unknown_not_pass(self):
        source = self._source("s.txt", "x\n")
        result = self._prepare(
            "Draft JSON.",
            [_req("truth", "json.unsupported_truth", "Claim truth", {"field": "x", "expected": True})],
            [("s", source, "s.txt")],
            "a.json",
            "json",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "a.json"
        artifact.write_text(json.dumps({"x": True}), encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(self._status(receipt, "truth"), "UNKNOWN")
        self.assertNotEqual(receipt["decision"], "SELECTED_CHECKS_PASS")

    def test_unknown_text_and_csv_kinds_stay_unknown(self):
        source = self._source("s.txt", "x\n")
        result = self._prepare(
            "Draft text.",
            [_req("weird", "text.unsupported_thing", "Weird claim", {"text": "x"})],
            [("s", source, "s.txt")],
            "a.md",
            "markdown",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "a.md"
        artifact.write_text("x\n", encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(self._status(receipt, "weird"), "UNKNOWN")

    def test_json_typed_equality_bool_is_not_int(self):
        source = self._source("s.txt", "x\n")
        result = self._prepare(
            "Draft JSON.",
            [_req("count", "json.field_exact", "Use the exact count object", {"field": "x", "expected": {"count": 0}})],
            [("s", source, "s.txt")],
            "a.json",
            "json",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "a.json"
        artifact.write_text(json.dumps({"x": {"count": False}}), encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(self._status(receipt, "count"), "FAIL")
        # And the true typed match still passes.
        artifact.write_text(json.dumps({"x": {"count": 0}}), encoding="utf-8")
        receipt2 = review_task(self.store, result["task_id"], write_outputs=False)
        self.assertEqual(self._status(receipt2, "count"), "PASS")

    def test_duplicate_key_json_does_not_pass(self):
        source = self._source("s.txt", "x\n")
        result = self._prepare(
            "Draft JSON.",
            [_req("x", "json.field_exact", "Use the exact value", {"field": "x", "expected": 7})],
            [("s", source, "s.txt")],
            "a.json",
            "json",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "a.json"
        artifact.write_text('{"x": 6, "x": 7}', encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        self.assertNotEqual(self._status(receipt, "x"), "PASS")

    def test_csv_decimal_cap_point_one_plus_point_two(self):
        source = self._source("items.csv", "item,amount\napples,0.1\npears,0.2\n")
        result = self._prepare(
            "Draft CSV.",
            [
                _req("columns", "csv.columns", "Use declared columns", {"columns": ["item", "amount"]}),
                _req("cap", "csv.total_cap", "Keep total within cap", {"column": "amount", "max_value": 0.3}),
            ],
            [("items", source, "items.csv")],
            "items.csv",
            "csv",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "items.csv"
        artifact.write_text("item,amount\napples,0.1\npears,0.2\n", encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(self._status(receipt, "cap"), "PASS")

    def test_csv_rejects_duplicate_empty_headers_malformed_and_nonfinite(self):
        source = self._source("s.txt", "x\n")
        cases = [
            ("item,item\n1,2\n", "duplicate header"),
            ("item,\n1,2\n", "empty header"),
            ("item,amount\n1\n", "malformed row"),
            ("item,amount\n1,NaN\n", "nonfinite"),
            ("item,amount\n1,Infinity\n", "nonfinite"),
        ]
        for csv_text, _label in cases:
            result = self._prepare(
                "Draft CSV.",
                [_req("cap", "csv.total_cap", "Keep total within cap", {"column": "amount", "max_value": 100})],
                [("s", source, "s.txt")],
                "items.csv",
                "csv",
            )
            artifact = Path(result["task_dir"]) / "artifacts" / "items.csv"
            artifact.write_text(csv_text, encoding="utf-8")
            receipt = review_task(self.store, result["task_id"], write_outputs=False)
            self.assertNotEqual(self._status(receipt, "cap"), "PASS", csv_text)

    def test_docx_preserve_paragraph_kind_is_supported(self):
        source = self._source("s.txt", "x\n")
        result = self._prepare(
            "Draft a document.",
            [_req("keep", "docx.preserve_paragraph", "Keep the paragraph", {"paragraph_index": 1, "expected": "Keep this"})],
            [("s", source, "s.txt")],
            "doc.docx",
            "docx",
        )
        doc = Document()
        doc.add_paragraph("Keep this")
        doc.save(Path(result["task_dir"]) / "artifacts" / "doc.docx")
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(self._status(receipt, "keep"), "PASS")

    def test_docx_wrong_kind_stays_unknown(self):
        source = self._source("s.txt", "x\n")
        result = self._prepare(
            "Draft a document.",
            [_req("keep", "docx.preserve_text", "Keep the paragraph", {"paragraph_index": 1, "expected": "Keep this"})],
            [("s", source, "s.txt")],
            "doc.docx",
            "docx",
        )
        doc = Document()
        doc.add_paragraph("Keep this")
        doc.save(Path(result["task_dir"]) / "artifacts" / "doc.docx")
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(self._status(receipt, "keep"), "UNKNOWN")

    def test_symlink_artifact_is_refused(self):
        source = self._source("s.txt", "Hello\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include greeting", {"text": "Hello"})],
            [("s", source, "s.txt")],
            "note.md",
            "markdown",
        )
        task_dir = Path(result["task_dir"])
        target = self.base / "real.md"
        target.write_text("Hello\n", encoding="utf-8")
        artifact = task_dir / "artifacts" / "note.md"
        artifact.symlink_to(target)
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(receipt["decision"], "BLOCKED")
        self.assertEqual(self._status(receipt, "greeting"), "BLOCKED")

    def test_symlink_source_is_refused(self):
        source = self._source("s.txt", "Hello\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include greeting", {"text": "Hello"})],
            [("s", source, "s.txt")],
            "note.md",
            "markdown",
        )
        task_dir = Path(result["task_dir"])
        artifact = task_dir / "artifacts" / "note.md"
        artifact.write_text("Hello\n", encoding="utf-8")
        real = self.base / "real-source.txt"
        real.write_text("Hello\n", encoding="utf-8")
        (task_dir / "sources" / "s.txt").unlink()
        (task_dir / "sources" / "s.txt").symlink_to(real)
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(receipt["decision"], "BLOCKED")

    def test_withholding_frozen_hash_file_stales_recheck(self):
        source = self._source("s.txt", "Hello\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include greeting", {"text": "Hello"})],
            [("s", source, "s.txt")],
            "note.md",
            "markdown",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "note.md"
        artifact.write_text("Hello\n", encoding="utf-8")
        first = review_task(self.store, result["task_id"], write_outputs=False)
        self.assertEqual(first["decision"], "SELECTED_CHECKS_PASS")
        self.assertTrue(first["binding"]["frozen_hash_file"]["available"])
        # Withhold the frozen hash record: the next review is blocked, and
        # recheck must not report the old evidence as fresh.
        (Path(result["task_dir"]) / "frozen.sha256").unlink()
        recheck = recheck_task(self.store, result["task_id"], first)
        self.assertEqual(recheck["status"], "STALE")
        self.assertFalse(recheck["previous_results_verified"])
        self.assertIn("frozen_hash_file", recheck["changed_bindings"])

    def test_artifact_snapshot_is_preserved_after_later_edit(self):
        source = self._source("s.txt", "Hello\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include greeting", {"text": "Hello"})],
            [("s", source, "s.txt")],
            "note.md",
            "markdown",
        )
        task_dir = Path(result["task_dir"])
        artifact = task_dir / "artifacts" / "note.md"
        artifact.write_text("Hello\n", encoding="utf-8")
        review_task(self.store, result["task_id"])
        outputs = sorted((task_dir / "outputs").iterdir())
        snapshot = next((p for p in outputs[0].iterdir() if p.name.startswith("artifact-snapshot")), None)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.read_text(encoding="utf-8"), "Hello\n")
        # Later edit cannot erase the older output.
        artifact.write_text("Changed later\n", encoding="utf-8")
        self.assertEqual(snapshot.read_text(encoding="utf-8"), "Hello\n")

    def test_recheck_compares_identity_title_request_coverage_and_decision(self):
        source = self._source("s.txt", "Hello\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include greeting", {"text": "Hello"})],
            [("s", source, "s.txt")],
            "note.md",
            "markdown",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "note.md"
        artifact.write_text("Hello\n", encoding="utf-8")
        first = review_task(self.store, result["task_id"], write_outputs=False)
        tampered = json.loads(json.dumps(first))
        tampered["title"] = "Different title"
        recheck = recheck_task(self.store, result["task_id"], tampered)
        self.assertEqual(recheck["status"], "INVALID_EVIDENCE")
        self.assertFalse(recheck["previous_results_verified"])

    def test_repair_requires_reviewed_scope_and_does_not_silently_adopt(self):
        source = self._source("s.txt", "Hello\n")
        other = self._source("other.txt", "Other\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include greeting", {"text": "Hello"})],
            [("s", source, "s.txt"), ("o", other, "other.txt")],
            "note.md",
            "markdown",
        )
        with self.assertRaises(TaskBlocked):
            repair_task(self.store, result["task_id"])
        with self.assertRaises(TaskBlocked):
            repair_task(self.store, result["task_id"], {"reviewed": False, "scope_text": "x", "adopted_source_ids": ["s"]})
        repaired = repair_task(
            self.store,
            result["task_id"],
            {"reviewed": True, "scope_text": "Fix greeting only.", "adopted_source_ids": ["s"]},
        )
        adopted = {s["id"] for s in repaired["frozen"]["sources"]}
        self.assertEqual(adopted, {"s"})
        self.assertFalse((Path(repaired["task_dir"]) / "sources" / "other.txt").exists())
        self.assertEqual(repaired["frozen"]["requirements"], result["frozen"]["requirements"])
        # Originals are untouched.
        self.assertTrue((Path(result["task_dir"]) / "sources" / "other.txt").exists())

    def test_receipt_block_next_action_and_coverage_disclosure(self):
        source = self._source("s.txt", "Hello\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include greeting", {"text": "Hello"})],
            [("s", source, "s.txt")],
            "note.md",
            "markdown",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "note.md"
        artifact.write_text("Hello\n", encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        readable = render_readable_receipt(receipt)
        self.assertIn("Checklist coverage itself", readable)
        self.assertNotIn("Remains unverified:\n- None", readable)
        # Blocked receipt must not encourage weakening the contract.
        (Path(result["task_dir"]) / "frozen.json").write_text('{"tampered": true}', encoding="utf-8")
        blocked = review_task(self.store, result["task_id"], write_outputs=False)
        readable_blocked = render_readable_receipt(blocked)
        self.assertIn("Restore the original input, or start a newly confirmed task.", readable_blocked)
        self.assertNotIn("Fix the frozen task record", readable_blocked)

    def test_receipt_uses_title_and_short_values_not_full_request_or_huge_arrays(self):
        source = self._source("s.txt", "Hello\n")
        result = self._prepare(
            "Draft a note.\nWith a long request body that should not be repeated in full.",
            [_req("count", "json.field_exact", "Use exact count", {"field": "count", "expected": 3})],
            [("s", source, "s.txt")],
            "a.json",
            "json",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "a.json"
        artifact.write_text(json.dumps({"count": 3, "big": list(range(500))}), encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        readable = render_readable_receipt(receipt)
        self.assertTrue(readable.startswith("Task: Draft a note."))
        self.assertNotIn("long request body that should not be repeated", readable)
        self.assertNotIn(str(list(range(500))), readable)
        self.assertIn("observed 3", readable)

    def test_mcp_client_writes_readable_receipt_and_snapshot_outside_server(self):
        source = self._source("s.txt", "Hello\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include greeting", {"text": "Hello"})],
            [("s", source, "s.txt")],
            "note.md",
            "markdown",
        )
        artifact = Path(result["task_dir"]) / "artifacts" / "note.md"
        artifact.write_text("Hello\n", encoding="utf-8")
        output = self.base / "client-output"
        client_result = mcp_review(self.store, result["task_id"], output)
        self.assertEqual(client_result["receipt"]["decision"], "SELECTED_CHECKS_PASS")
        self.assertTrue((output / "receipt.md").is_file())
        self.assertTrue((output / "receipt.json").is_file())
        self.assertTrue((output / "observations.json").is_file())
        snapshot = next(p for p in output.iterdir() if p.name.startswith("artifact-snapshot"))
        self.assertEqual(snapshot.read_text(encoding="utf-8"), "Hello\n")
        observations = json.loads((output / "observations.json").read_text(encoding="utf-8"))["observations"]
        methods = [obs["method"] for obs in observations]
        self.assertIn("initialize", methods)
        self.assertIn("tools/list", methods)
        self.assertTrue(any(obs.get("params", {}).get("name") == "taskflow_review" for obs in observations if obs["method"] == "tools/call"))
        # Files are immutable in the usual sense: read-only mode.
        for name in ("receipt.md", "receipt.json", "observations.json"):
            self.assertEqual(oct((output / name).stat().st_mode & 0o777), "0o444")
        with self.assertRaises(ValueError):
            mcp_review(self.store, result["task_id"], output)

    def test_checker_identity_covers_project_and_versions(self):
        from muse_audit.taskflow.tasks import checker_identity

        identity = checker_identity()
        self.assertIn("sources", identity)
        self.assertTrue(any("taskflow/tasks.py" in key for key in identity["sources"]))
        self.assertTrue(any("requirements.txt" in key for key in identity["sources"]))
        self.assertIn("packages", identity["runtime"])
        self.assertEqual(identity["runtime"]["packages"]["mcp"], "1.29.0")
        self.assertFalse(identity["source_changed_since_process_start"])


if __name__ == "__main__":
    unittest.main()
