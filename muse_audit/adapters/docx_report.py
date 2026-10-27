"""Bounded DOCX paragraph checker; no semantic inference or source authentication.

Paragraph and text-source line locators are 1-based. Only top-level body
paragraphs are mapped. A repair edits one plain text run and preserves all
unmodified ZIP member payloads, rather than rewriting the whole document.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import re

from docx import Document
from lxml import etree

VERSION = "docx-report-1.0"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
MAX_BYTES = 5_000_000
MAX_UNPACKED = 20_000_000
MAX_MEMBERS = 1000
SUPPORTED = {"docx.quote", "docx.preserve_paragraph"}


def _path(root: Path, name: str) -> Path:
    root = root.resolve()
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("A selected relative file path is required")
    path = root / name
    if not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise ValueError("Selected path escapes the job root or uses a symlink")
    return path


def _package(path: Path) -> tuple[bytes, dict[str, bytes], list]:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("DOCX exceeds the 5 MB prototype input limit")
    data = path.read_bytes()
    with ZipFile(BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS or len({x.filename for x in infos}) != len(infos):
            raise ValueError("Too many or duplicate DOCX ZIP members")
        if sum(x.file_size for x in infos) > MAX_UNPACKED:
            raise ValueError("DOCX expands beyond the 20 MB prototype limit")
        members = {x.filename: archive.read(x) for x in infos}
    if "word/document.xml" not in members:
        raise ValueError("Missing DOCX document body")
    return data, members, infos


def _xml(blob: bytes):
    return etree.fromstring(blob, parser=etree.XMLParser(resolve_entities=False, no_network=True))


def _coverage(members: dict[str, bytes]) -> list[str]:
    root = _xml(members["word/document.xml"])
    features = []
    tags = {etree.QName(x).localname for x in root.iter() if isinstance(x.tag, str)}
    for tag, label in {
        "tbl": "tables", "hyperlink": "hyperlinks", "fldChar": "fields",
        "instrText": "field instructions", "del": "tracked deletions", "ins": "tracked insertions",
        "sdt": "content controls", "drawing": "drawings", "object": "embedded objects",
        "pict": "pictures or text boxes", "txbxContent": "text boxes", "oMath": "equations",
        "altChunk": "alternate document chunks", "vanish": "hidden text", "webHidden": "hidden text",
    }.items():
        if tag in tags:
            features.append(label)
    for name, blob in members.items():
        if re.fullmatch(r"word/(header\d+|footer\d+|footnotes|endnotes|comments)\.xml", name):
            if _xml(blob).xpath("//*[local-name()='t' and string-length(text()) > 0]"):
                features.append(name)
        if name.endswith("vbaProject.bin"):
            features.append("macros")
    return sorted(set(features))


def _line(root: Path, job: dict, req: dict) -> tuple[str, str]:
    req = req["config"]
    sources = job.get("sources", [])
    if isinstance(sources, dict):
        source = sources.get(req.get("source_id"))
    else:
        matches = [s for s in sources if s.get("id") == req.get("source_id")]
        source = matches[0] if len(matches) == 1 else None
    if not source:
        raise ValueError("Selected source mapping is missing or ambiguous")
    path = _path(root, source["path"])
    if path.suffix.lower() != ".txt":
        raise ValueError("Only selected UTF-8 .txt source lines are supported")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Source exceeds the 5 MB prototype limit")
    lines = path.read_text(encoding="utf-8").splitlines()
    index = req.get("source_line")
    if type(index) is not int or index < 1 or index > len(lines):
        raise ValueError("Selected source line is missing or invalid")
    prefix = req.get("prefix", "")
    if not isinstance(prefix, str):
        raise ValueError("Quote prefix must be text")
    return prefix + lines[index - 1], f"{source['path']}:line:{index}"


def _result(req: dict, status: str, message: str, evidence: list[dict]) -> dict:
    return {"requirement_id": req["id"], "status": status, "reason": message,
            "observed": next((x["text"] for x in evidence if x["role"] == "extracted_candidate"), None),
            "expected": next((x["text"] for x in evidence if x["role"] != "extracted_candidate"), None),
            "locations": [x["location"] for x in evidence]}


def evaluate(root: Path, job: dict) -> list[dict]:
    """Evaluate owned requirements; shared kernel owns unsupported claim statuses."""
    requirements = [r for r in job.get("requirements", []) if r.get("kind") in SUPPORTED]
    try:
        path = _path(root, job["artifact"]["path"])
        data, members, _ = _package(path)
        document = Document(BytesIO(data))
        excluded = _coverage(members)
    except (OSError, KeyError, ValueError, BadZipFile, etree.XMLSyntaxError) as exc:
        return [_result(req, "BLOCKED", f"DOCX extraction could not run: {exc}", []) for req in requirements]
    results = []
    for req in requirements:
        kind = req.get("kind")
        config = req.get("config", {})
        allowed = {"paragraph_index", "source_id", "source_line", "prefix"} if kind == "docx.quote" else {"paragraph_index", "expected"}
        if not isinstance(config, dict) or set(config) - allowed:
            results.append(_result(req, "UNKNOWN", "Unsupported or malformed requirement mapping configuration.", []))
            continue
        index = config.get("paragraph_index")
        if type(index) is not int or index < 1:
            results.append(_result(req, "UNKNOWN", "The confirmed mapping needs a positive 1-based body paragraph index.", []))
            continue
        location = f"{job['artifact']['path']}:paragraph:{index}"
        try:
            if kind == "docx.quote":
                expected, source_location = _line(root, job, req)
                evidence = [{"location": source_location, "text": expected, "role": "supplied_source_not_authenticated"}]
            else:
                expected = req.get("config", {}).get("expected")
                if not isinstance(expected, str):
                    raise ValueError("Protected text must be a string in the approved contract")
                evidence = [{"location": f"contract:requirements:{req['id']}", "text": expected, "role": "approved_preservation_requirement"}]
        except (OSError, UnicodeError, KeyError, ValueError) as exc:
            results.append(_result(req, "UNKNOWN", f"Required source or mapping unavailable: {exc}", []))
            continue
        observed = document.paragraphs[index - 1].text if index <= len(document.paragraphs) else None
        evidence.append({"location": location, "text": observed, "role": "extracted_candidate"})
        equal = observed == expected
        results.append(_result(req, "PASS" if equal else "FAIL", "Exact selected text matches; this does not establish the source is true." if equal else "Selected paragraph is missing or differs from the required exact text.", evidence))
    if excluded:
        results.append({"requirement_id": "__docx_coverage__", "status": "UNKNOWN", "reason": "Outside the paragraph adapter's extraction coverage: " + ", ".join(excluded), "observed": excluded, "expected": "Only mapped top-level plain body paragraphs", "locations": [job["artifact"]["path"]]})
    return results


def _plain_text_node(xml, paragraph: int):
    paragraphs = xml.xpath("./w:body/w:p", namespaces=NS)
    if type(paragraph) is not int or paragraph < 1 or paragraph > len(paragraphs):
        raise ValueError("Repair paragraph is missing or invalid")
    node = paragraphs[paragraph - 1]
    if any(child.tag not in {f"{{{W}}}pPr", f"{{{W}}}r"} for child in node):
        raise ValueError("Repair supports only a plain single-run paragraph")
    runs = node.findall(f"{{{W}}}r")
    if len(runs) != 1 or any(child.tag not in {f"{{{W}}}rPr", f"{{{W}}}t"} for child in runs[0]):
        raise ValueError("Repair supports only a plain single-run paragraph")
    texts = runs[0].findall(f"{{{W}}}t")
    if len(texts) != 1:
        raise ValueError("Repair supports only one plain text node")
    return texts[0]


def plan(root: Path, job: dict) -> list[dict]:
    """Propose exact quote corrections only; never change protected requirements."""
    results = {r["requirement_id"]: r for r in evaluate(root, job)}
    _, members, _ = _package(_path(root, job["artifact"]["path"]))
    xml = _xml(members["word/document.xml"])
    operations = []
    for req in job.get("requirements", []):
        if req.get("kind") != "docx.quote" or req.get("mode") != "must_change" or results[req["id"]]["status"] != "FAIL":
            continue
        try:
            node = _plain_text_node(xml, req["config"]["paragraph_index"])
            after, _ = _line(root, job, req)
            if any(x in after for x in "\n\r\t"):
                continue
        except (KeyError, ValueError, OSError, UnicodeError):
            continue
        operations.append({"kind": "docx.replace_paragraph", "requirement_id": req["id"], "paragraph_index": req["config"]["paragraph_index"], "before": node.text or "", "after": after})
    return operations


def apply(input_path: Path, output_path: Path, operations: list[dict]) -> None:
    """Write a new guarded copy. Caller must approve plan and validate snapshot pins."""
    if input_path.resolve() == output_path.resolve() or output_path.exists():
        raise ValueError("Repair must create a new file and never overwrite a candidate")
    _, members, infos = _package(input_path)
    xml = _xml(members["word/document.xml"])
    seen = set()
    for op in operations:
        if op.get("kind") != "docx.replace_paragraph":
            raise ValueError("Unsupported DOCX repair operation")
        index = op.get("paragraph_index")
        if index in seen:
            raise ValueError("Duplicate paragraph repair")
        seen.add(index)
        node = _plain_text_node(xml, index)
        if not isinstance(op.get("before"), str) or (node.text or "") != op["before"]:
            raise ValueError("Repair precondition failed; candidate text changed")
        after = op.get("after")
        if not isinstance(after, str) or len(after) > 100_000 or any(x in after for x in "\n\r\t"):
            raise ValueError("Repair requires one bounded plain text line")
        node.text = after
        if after != after.strip():
            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    members["word/document.xml"] = etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
    with output_path.open("xb") as handle:
        with ZipFile(handle, "w") as archive:
            for info in infos:
                archive.writestr(info, members[info.filename])
