"""Taskflow tests: fresh tasks, tampering, isolation, MCP, and receipts.

All fixtures are synthetic and local. No network, model, or provider
calls are made. The two main fresh tasks use different types and
different values from each other and from the frozen budget.
"""

import asyncio
import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import Workbook

from muse_audit.taskflow.receipt import render_readable_receipt
from muse_audit.taskflow.tasks import (
    load_frozen,
    prepare_task,
    recheck_task,
    repair_task,
    review_task,
)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _req(req_id, kind, description, config, mode="must_change"):
    return {"id": req_id, "kind": kind, "description": description, "mode": mode, "config": config}


class TaskflowTestCase(unittest.TestCase):
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
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_bytes(data)
        return path

    def _prepare(self, request, requirements, sources, artifact_name, artifact_kind):
        result = prepare_task(
            self.store,
            request,
            requirements,
            [(sid, path, name) for sid, path, name in sources],
            artifact_name,
            artifact_kind,
        )
        return result

    def _artifact_path(self, task_dir, name):
        return Path(task_dir) / "artifacts" / name

    def _status(self, receipt, req_id):
        for check in receipt["checks"]:
            if check["requirement_id"] == req_id:
                return check["status"]
        self.fail(f"Missing check: {req_id}")

    def test_markdown_fresh_task_with_changed_values(self):
        """Fresh task one: a short note, not a budget, with new wording and limits."""
        source = self._source("notes.txt", "Riverbend meeting notes\nSecond line\n")
        reqs = [
            _req("greeting", "markdown.required_exact", "Include the Riverbend greeting", {"text": "Hello Riverbend"}),
            _req("no_urgent", "markdown.forbidden_exact", "Do not mark the note urgent", {"text": "urgent"}),
            _req("short", "markdown.word_limit", "Keep the note short", {"max_words": 40}),
        ]
        result = self._prepare(
            "Draft a short welcome note for Riverbend.",
            reqs,
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        # Freeze happened before generation: no deliverable exists yet.
        self.assertFalse(self._artifact_path(result["task_dir"], "note.md").exists())
        self._artifact_path(result["task_dir"], "note.md").write_text(
            "Hello Riverbend\nWelcome to the meeting.\n", encoding="utf-8"
        )
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(receipt["decision"], "SELECTED_CHECKS_PASS")
        self.assertEqual(self._status(receipt, "greeting"), "PASS")
        self.assertEqual(self._status(receipt, "no_urgent"), "PASS")
        self.assertEqual(self._status(receipt, "short"), "PASS")

    def test_csv_fresh_task_different_type_and_cap(self):
        """Fresh task two: a CSV list with declared columns, source rows, and a new cap."""
        csv_text = "item,amount\napples,400\npears,500\n"
        source = self._source("items.csv", csv_text)
        reqs = [
            _req("columns", "csv.columns", "Use the declared columns", {"columns": ["item", "amount"]}),
            _req("rows", "csv.rows_exact", "Match the selected source rows", {"source_id": "items"}),
            _req("cap", "csv.total_cap", "Keep the total within the new cap", {"column": "amount", "max_value": 1200}),
        ]
        result = self._prepare(
            "Draft a CSV list of items from the selected source.",
            reqs,
            [("items", source, "items.csv")],
            "items.csv",
            "csv",
        )
        self._artifact_path(result["task_dir"], "items.csv").write_text(csv_text, encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(receipt["decision"], "SELECTED_CHECKS_PASS")
        # A changed total over the cap must fail, not inherit an old verdict.
        self._artifact_path(result["task_dir"], "items.csv").write_text(
            "item,amount\napples,900\npears,500\n", encoding="utf-8"
        )
        changed = review_task(self.store, result["task_id"])
        self.assertEqual(self._status(changed, "rows"), "FAIL")
        self.assertEqual(self._status(changed, "cap"), "FAIL")
        self.assertEqual(changed["decision"], "REVISE")

    def test_json_exact_fields_and_fixed_claim_vs_changed_output(self):
        source = self._source("profile.json", json.dumps({"name": "Ada", "city": "Lisbon"}))
        reqs = [
            _req("name", "json.field_exact", "Use the selected name", {"field": "name", "expected": "Ada"}),
            _req("city", "json.field_exact", "Use the selected city", {"field": "city", "expected": "Lisbon"}),
        ]
        result = self._prepare(
            "Draft a JSON profile from the selected source.",
            reqs,
            [("profile", source, "profile.json")],
            "profile.json",
            "json",
        )
        artifact = self._artifact_path(result["task_dir"], "profile.json")
        artifact.write_text(json.dumps({"name": "Ada", "city": "Lisbon"}), encoding="utf-8")
        first = review_task(self.store, result["task_id"], write_outputs=False)
        self.assertEqual(first["decision"], "SELECTED_CHECKS_PASS")
        # Same claim, changed output: the fresh review must not trust the first pass.
        artifact.write_text(json.dumps({"name": "Ada", "city": "Porto"}), encoding="utf-8")
        second = review_task(self.store, result["task_id"], write_outputs=False)
        self.assertEqual(self._status(second, "city"), "FAIL")
        recheck = recheck_task(self.store, result["task_id"], first)
        self.assertEqual(recheck["status"], "STALE")
        self.assertFalse(recheck["previous_results_verified"])

    def test_xlsx_reuse_with_new_values_not_old_budget(self):
        source = self._source(
            "prices.json",
            json.dumps({"currency": "USD", "amounts": {"desk": 10000, "chair": 5000, "delivery": 1000}}),
        )
        reqs = [
            _req("desk", "xlsx.source_amount", "Include required desk cost", {"sheet": "Budget", "cell": "B4", "source_id": "prices", "source_key": "desk", "currency": "USD"}),
            _req("chair", "xlsx.source_amount", "Include required chair cost", {"sheet": "Budget", "cell": "B5", "source_id": "prices", "source_key": "chair", "currency": "USD"}),
            _req("delivery", "xlsx.source_amount", "Include required delivery cost", {"sheet": "Budget", "cell": "B6", "source_id": "prices", "source_key": "delivery", "currency": "USD"}),
            _req("total", "xlsx.sum", "Total includes every approved cost cell", {"sheet": "Budget", "cell": "B8", "required_cells": ["B4", "B5", "B6"]}),
            _req("cap", "xlsx.cap", "Total fits the new cap", {"sheet": "Budget", "cell": "B8", "max_cents": 20000}),
        ]
        result = self._prepare(
            "Draft a small budget with new values.",
            reqs,
            [("prices", source, "prices.json")],
            "budget.xlsx",
            "xlsx",
        )
        book = Workbook()
        sheet = book.active
        sheet.title = "Budget"
        sheet["B4"] = 10000
        sheet["B5"] = 5000
        sheet["B6"] = 1000
        sheet["B8"] = "=SUM(B4:B6)"
        book.save(self._artifact_path(result["task_dir"], "budget.xlsx"))
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(receipt["decision"], "SELECTED_CHECKS_PASS")
        self.assertEqual(self._status(receipt, "cap"), "PASS")

    def test_docx_reuse_quote(self):
        from docx import Document

        source = self._source("quote.txt", "First line\nQuoted line here\n")
        reqs = [
            _req("quote", "docx.quote", "Quote the selected line exactly", {"paragraph_index": 1, "source_id": "quote", "source_line": 2, "prefix": ""}),
        ]
        result = self._prepare(
            "Draft a document quoting the selected line.",
            reqs,
            [("quote", source, "quote.txt")],
            "doc.docx",
            "docx",
        )
        doc = Document()
        doc.add_paragraph("Quoted line here")
        doc.save(self._artifact_path(result["task_dir"], "doc.docx"))
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(self._status(receipt, "quote"), "PASS")

    def test_missing_evidence_blocks_passing(self):
        source = self._source("notes.txt", "Hello Riverbend\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"})],
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        self._artifact_path(result["task_dir"], "note.md").write_text("Hello Riverbend\n", encoding="utf-8")
        # Delete a frozen source after preparation: review must block, not pass.
        (Path(result["task_dir"]) / "sources" / "notes.txt").unlink()
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(receipt["decision"], "BLOCKED")
        self.assertEqual(self._status(receipt, "greeting"), "BLOCKED")

    def test_missing_artifact_blocks_passing(self):
        source = self._source("notes.txt", "Hello Riverbend\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"})],
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(receipt["decision"], "BLOCKED")

    def test_source_tampering_blocks_passing(self):
        source = self._source("notes.txt", "Hello Riverbend\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"})],
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        self._artifact_path(result["task_dir"], "note.md").write_text("Hello Riverbend\n", encoding="utf-8")
        (Path(result["task_dir"]) / "sources" / "notes.txt").write_text("Changed after freezing\n", encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(receipt["decision"], "BLOCKED")
        self.assertEqual(self._status(receipt, "greeting"), "BLOCKED")

    def test_contract_tampering_blocks_passing(self):
        source = self._source("notes.txt", "Hello Riverbend\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"})],
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        self._artifact_path(result["task_dir"], "note.md").write_text("Hello Riverbend\n", encoding="utf-8")
        frozen_path = Path(result["task_dir"]) / "frozen.json"
        data = json.loads(frozen_path.read_text(encoding="utf-8"))
        data["requirements"][0]["config"]["text"] = "Something else"
        frozen_path.write_text(json.dumps(data), encoding="utf-8")
        # frozen.sha256 is deliberately not updated: this is tampering.
        receipt = review_task(self.store, result["task_id"])
        self.assertEqual(receipt["decision"], "BLOCKED")

    def test_unsupported_claims_stay_unknown_and_draft_does_not_prove_sent(self):
        source = self._source("notes.txt", "Hello Riverbend\n")
        reqs = [
            _req("comfort", "semantic.claim", "The chair will be comfortable", {}),
            _req("sent", "sent.message", "The message was sent to Sam", {}),
            _req("web", "web.claim", "The web page says this is true", {}),
            _req("privacy", "privacy.claim", "Only the right people can see this", {}),
            _req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"}),
        ]
        result = self._prepare(
            "Draft a note and make unsupported claims.",
            reqs,
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        self._artifact_path(result["task_dir"], "note.md").write_text("Hello Riverbend\n", encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        for req_id in ("comfort", "sent", "web", "privacy"):
            self.assertEqual(self._status(receipt, req_id), "UNKNOWN")
        self.assertNotEqual(receipt["decision"], "SELECTED_CHECKS_PASS")
        readable = render_readable_receipt(receipt)
        self.assertIn("Remains unverified:", readable)
        self.assertIn("The message was sent to Sam", readable)

    def test_task_isolation_and_traversal_blocked(self):
        source_a = self._source("a.txt", "Hello A\n")
        source_b = self._source("b.txt", "Hello B\n")
        reqs_a = [_req("greeting", "markdown.required_exact", "Include A greeting", {"text": "Hello A"})]
        reqs_b = [_req("greeting", "markdown.required_exact", "Include B greeting", {"text": "Hello B"})]
        task_a = self._prepare("Draft A.", reqs_a, [("a", source_a, "a.txt")], "a.md", "markdown")
        task_b = self._prepare("Draft B.", reqs_b, [("b", source_b, "b.txt")], "b.md", "markdown")
        self._artifact_path(task_a["task_dir"], "a.md").write_text("Hello A\n", encoding="utf-8")
        self._artifact_path(task_b["task_dir"], "b.md").write_text("Hello B\n", encoding="utf-8")
        # Tamper only with B. A must still pass.
        (Path(task_b["task_dir"]) / "sources" / "b.txt").write_text("Tampered B\n", encoding="utf-8")
        self.assertEqual(review_task(self.store, task_a["task_id"])["decision"], "SELECTED_CHECKS_PASS")
        self.assertEqual(review_task(self.store, task_b["task_id"])["decision"], "BLOCKED")
        with self.assertRaises(ValueError):
            review_task(self.store, "../secret")
        with self.assertRaises(ValueError):
            review_task(self.store, "task-does-not-exist")

    def test_repair_creates_new_copy_and_preserves_original(self):
        source = self._source("notes.txt", "Hello Riverbend\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"})],
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        artifact = self._artifact_path(result["task_dir"], "note.md")
        artifact.write_text("Wrong greeting\n", encoding="utf-8")
        before_hash = _sha(artifact)
        first = review_task(self.store, result["task_id"])
        self.assertEqual(self._status(first, "greeting"), "FAIL")
        repaired = repair_task(
            self.store,
            result["task_id"],
            {"reviewed": True, "scope_text": "Fix the greeting only, under the original requirements.", "adopted_source_ids": ["notes"]},
        )
        self.assertNotEqual(repaired["task_id"], result["task_id"])
        self.assertEqual(repaired["frozen"]["requirements"], result["frozen"]["requirements"])
        self.assertEqual(repaired["frozen"]["request"], result["frozen"]["request"])
        self.assertFalse((Path(repaired["task_dir"]) / "artifacts" / "note.md").exists())
        # Original artifact and receipt are untouched.
        self.assertEqual(_sha(artifact), before_hash)
        self.assertTrue((Path(result["task_dir"]) / "outputs").exists())

    def test_checker_change_stales_old_assurance(self):
        source = self._source("notes.txt", "Hello Riverbend\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"})],
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        self._artifact_path(result["task_dir"], "note.md").write_text("Hello Riverbend\n", encoding="utf-8")
        first = review_task(self.store, result["task_id"], write_outputs=False)
        tampered = json.loads(json.dumps(first))
        tampered["binding"]["checker_hash"] = "changed-checker"
        recheck = recheck_task(self.store, result["task_id"], tampered)
        self.assertEqual(recheck["status"], "STALE")
        self.assertFalse(recheck["previous_results_verified"])

    def test_human_receipt_shows_partial_and_failed_checks(self):
        source = self._source("notes.txt", "Hello Riverbend\n")
        reqs = [
            _req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"}),
            _req("missing", "markdown.required_exact", "Include the missing line", {"text": "Missing line here"}),
            _req("comfort", "semantic.claim", "The chair will be comfortable", {}),
        ]
        result = self._prepare(
            "Draft a note with mixed results.",
            reqs,
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        self._artifact_path(result["task_dir"], "note.md").write_text("Hello Riverbend\n", encoding="utf-8")
        receipt = review_task(self.store, result["task_id"])
        readable = render_readable_receipt(receipt)
        self.assertIn("Checked:", readable)
        self.assertIn("Include the greeting", readable)
        self.assertIn("Needs attention:", readable)
        self.assertIn("Include the missing line", readable)
        self.assertIn("Remains unverified:", readable)
        self.assertIn("The chair will be comfortable", readable)
        self.assertIn("Next action:", readable)
        # The readable receipt itself carries no hash strings.
        self.assertNotIn("sha256", readable.lower())

    def test_review_writes_new_output_and_preserves_prior(self):
        source = self._source("notes.txt", "Hello Riverbend\n")
        result = self._prepare(
            "Draft a note.",
            [_req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"})],
            [("notes", source, "notes.txt")],
            "note.md",
            "markdown",
        )
        self._artifact_path(result["task_dir"], "note.md").write_text("Hello Riverbend\n", encoding="utf-8")
        first = review_task(self.store, result["task_id"])
        second = review_task(self.store, result["task_id"])
        outputs = sorted((Path(result["task_dir"]) / "outputs").iterdir())
        self.assertGreaterEqual(len(outputs), 2)
        for output in outputs:
            self.assertTrue((output / "receipt.json").is_file())
            self.assertTrue((output / "receipt.md").is_file())
        self.assertEqual(first["decision"], second["decision"])


class TaskflowMcpTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_tools_are_readonly_and_review_does_not_modify_inputs(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = base / "store"
            store.mkdir()
            inputs = base / "inputs"
            inputs.mkdir()
            source = inputs / "notes.txt"
            source.write_text("Hello Riverbend\n", encoding="utf-8")
            result = prepare_task(
                store,
                "Draft a note.",
                [_req("greeting", "markdown.required_exact", "Include the greeting", {"text": "Hello Riverbend"})],
                [("notes", source, "notes.txt")],
                "note.md",
                "markdown",
            )
            task_dir = Path(result["task_dir"])
            artifact = task_dir / "artifacts" / "note.md"
            artifact.write_text("Hello Riverbend\n", encoding="utf-8")
            before = {
                "artifact": _sha(artifact),
                "source": _sha(task_dir / "sources" / "notes.txt"),
                "frozen": _sha(task_dir / "frozen.json"),
            }
            entry = Path(__file__).resolve().parent.parent / "muse_audit" / "taskflow" / "run_mcp.py"
            params = StdioServerParameters(
                command=sys.executable,
                args=["-B", str(entry), "--workspace", str(store)],
                env={},
                cwd=str(Path(__file__).resolve().parent.parent),
            )
            with open(base / "stderr.txt", "w") as errlog:
                async with stdio_client(params, errlog=errlog) as (read, write):
                    async with ClientSession(read, write) as client:
                        await client.initialize()
                        tools = await client.list_tools()
                        names = sorted(tool.name for tool in tools.tools)
                        self.assertEqual(names, ["taskflow_capabilities", "taskflow_recheck", "taskflow_review"])
                        for tool in tools.tools:
                            self.assertTrue(tool.annotations.readOnlyHint)
                            self.assertFalse(tool.annotations.destructiveHint)
                        def _unpack(response):
                            if response.structuredContent is not None:
                                return response.structuredContent
                            return json.loads(response.content[0].text)

                        caps = _unpack(await client.call_tool("taskflow_capabilities", {}))
                        self.assertTrue(caps["read_only"])
                        review = await client.call_tool("taskflow_review", {"task_id": result["task_id"]})
                        receipt = _unpack(review)
                        self.assertEqual(receipt["decision"], "SELECTED_CHECKS_PASS")
                        recheck = _unpack(
                            await client.call_tool(
                                "taskflow_recheck", {"task_id": result["task_id"], "prior_receipt": receipt}
                            )
                        )
                        self.assertEqual(recheck["status"], "FRESH")
            after = {
                "artifact": _sha(artifact),
                "source": _sha(task_dir / "sources" / "notes.txt"),
                "frozen": _sha(task_dir / "frozen.json"),
            }
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
