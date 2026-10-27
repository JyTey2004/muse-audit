"""Synthetic, hand-authored study-summary fixture; never a model result."""
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor


def build_fixture(root: Path) -> dict:
    """Create a native DOCX and a plain-text source in a fresh selected job directory."""
    root.mkdir(parents=True, exist_ok=True)
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.left_margin = section.right_margin = Inches(1)
    section.top_margin = section.bottom_margin = Inches(1)
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = "Arial", Pt(11)
    normal.paragraph_format.space_after = Pt(10)
    title = document.styles["Title"]
    title.font.name, title.font.size, title.font.color.rgb = "Arial", Pt(22), RGBColor(0, 0, 0)
    for border in title._element.xpath(".//w:pBdr"):
        border.getparent().remove(border)
    document.add_paragraph("Study Practice Summary", style="Title")
    document.add_paragraph("This practice summary compares a copied observation with the supplied study log. The observation below contains a deliberately planted transcription error for this audit demonstration.")
    document.add_paragraph("Source note: Each practice session lasted 30 minutes.")
    document.add_paragraph("Planned weekly practice remains 3 sessions.")
    document.add_paragraph("This method guarantees better exam results.")
    document.core_properties.title = "Study Practice Summary"
    document.core_properties.author = "Synthetic prototype fixture"
    document.core_properties.subject = "Hand-authored audit test data, not empirical research"
    document.save(root / "study-summary.docx")
    (root / "study-log.txt").write_text(
        "Synthetic practice log for demonstration only.\n"
        "Each practice session lasted 20 minutes.\n"
        "No exam outcomes or causal effects were measured.\n", encoding="utf-8"
    )
    return {
        "schema_version": 1,
        "job_id": "study-summary",
        "title": "Check a study summary against a selected practice log",
        "intent": "Correct the copied observation while retaining the approved title and practice plan; do not certify the causal claim.",
        "contract_version": "contract-1",
        "artifact": {"path": "study-summary.docx", "version": "draft-1", "kind": "docx_report"},
        "sources": [{"id": "study-log", "path": "study-log.txt", "version": "source-1"}],
        "requirements": [
            {"id": "quoted-duration", "kind": "docx.quote", "description": "The copied observation must exactly match the selected source line.", "mode": "must_change", "config": {"paragraph_index": 3, "source_id": "study-log", "source_line": 2, "prefix": "Source note: "}},
            {"id": "preserve-title", "kind": "docx.preserve_paragraph", "description": "Keep the approved report title unchanged.", "mode": "must_preserve", "config": {"paragraph_index": 1, "expected": "Study Practice Summary"}},
            {"id": "preserve-plan", "kind": "docx.preserve_paragraph", "description": "Keep the approved weekly practice plan unchanged.", "mode": "must_preserve", "config": {"paragraph_index": 4, "expected": "Planned weekly practice remains 3 sessions."}},
            {"id": "causal-effect", "kind": "semantic.causal_claim", "description": "Does this method guarantee better exam results?", "mode": "unknown", "config": {"paragraph_index": 5}},
        ],
    }
