"""Narrow deterministic checks for text, JSON, CSV, XLSX, and DOCX.

No arbitrary shell, URL, web, semantic, privacy, sent, delivered, or
provider-state evaluation is provided here. Anything outside the exact
kinds below is explicitly unsupported, never silently passed.
"""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..io import read_json
from .config_schemas import config_problem

SUPPORTED_KINDS = {
    "text.required_exact",
    "text.forbidden_exact",
    "text.word_limit",
    "markdown.required_exact",
    "markdown.forbidden_exact",
    "markdown.word_limit",
    "json.field_exact",
    "csv.columns",
    "csv.rows_exact",
    "csv.total_cap",
    "xlsx.source_amount",
    "xlsx.sum",
    "xlsx.cap",
    "xlsx.preserve_cell",
    "docx.quote",
    "docx.preserve_paragraph",
}

NATIVE_KINDS = {
    "xlsx.source_amount",
    "xlsx.sum",
    "xlsx.cap",
    "xlsx.preserve_cell",
    "docx.quote",
    "docx.preserve_paragraph",
}

MAX_FILE = 5_000_000
MAX_CSV_ROWS = 10000
MAX_CSV_COLUMNS = 50

_UNSUPPORTED_PREFIXES = (
    "semantic.",
    "web.",
    "privacy.",
    "sent.",
    "delivered.",
    "provider.",
    "provider_state.",
)

_UNSUPPORTED_KINDS = {
    "semantic.claim",
    "web.claim",
    "privacy.claim",
    "sent.message",
    "delivered.message",
    "provider.state",
}


def is_unsupported(kind):
    if not isinstance(kind, str):
        return True
    if kind in _UNSUPPORTED_KINDS:
        return True
    return any(kind.startswith(prefix) for prefix in _UNSUPPORTED_PREFIXES)


def unsupported_reason(kind):
    if kind.startswith("sent.") or kind.startswith("delivered.") or kind in (
        "sent.message",
        "delivered.message",
    ):
        return (
            "A created draft cannot prove a message was sent or delivered. "
            "This claim stays unverified."
        )
    if kind.startswith("privacy.") or kind == "privacy.claim":
        return "Privacy has no supported deterministic checker here. This claim stays unverified."
    if kind.startswith("web.") or kind == "web.claim":
        return "Web content has no supported deterministic checker here. This claim stays unverified."
    if kind.startswith("provider.") or kind.startswith("provider_state."):
        return "Provider state has no supported deterministic checker here. This claim stays unverified."
    return (
        "No supported checker for this kind. A model opinion is not evidence. "
        "This claim stays unverified."
    )


def word_count(text):
    return len(text.split())


def typed_equal(left, right):
    """Recursive typed equality: bool is not int, and nested values must match in type and value."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        if set(left) != set(right):
            return False
        return all(typed_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        if len(left) != len(right):
            return False
        return all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def get_json_field(data, field):
    current = data
    for part in field.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(f"Field is missing: {field}")
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                raise KeyError(f"Field is missing: {field}") from exc
        else:
            raise KeyError(f"Field is missing: {field}")
    return current


def _result(req, status, reason, observed=None, expected=None):
    return {
        "requirement_id": req["id"],
        "status": status,
        "reason": reason,
        "observed": observed,
        "expected": expected,
        "description": req.get("description", ""),
        "mode": req.get("mode", "must_change"),
        "locations": [],
    }


def _check_readable(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Symlinked input is refused.")
    if not path.is_file():
        raise ValueError("Input file is missing.")
    if path.stat().st_size > MAX_FILE:
        raise ValueError("Input exceeds the 5 MB limit.")


def check_text(req, artifact_text):
    problem = config_problem(req.get("kind"), req.get("config"))
    if problem:
        return _result(req, "UNKNOWN", problem)
    kind = req["kind"]
    if kind not in (
        "text.required_exact",
        "text.forbidden_exact",
        "text.word_limit",
        "markdown.required_exact",
        "markdown.forbidden_exact",
        "markdown.word_limit",
    ):
        return _result(req, "UNKNOWN", f"No supported checker for {kind!r}.")
    config = req.get("config", {})
    suffix = kind.split(".", 1)[1]
    if suffix == "required_exact":
        text = config.get("text")
        if not isinstance(text, str) or not text:
            return _result(req, "UNKNOWN", "Required exact text is missing or is not text.")
        present = text in artifact_text
        return _result(
            req,
            "PASS" if present else "FAIL",
            "Required exact text is present." if present else "Required exact text is missing.",
            present,
            True,
        )
    if suffix == "forbidden_exact":
        text = config.get("text")
        if not isinstance(text, str) or not text:
            return _result(req, "UNKNOWN", "Forbidden exact text is missing or is not text.")
        present = text in artifact_text
        return _result(
            req,
            "PASS" if not present else "FAIL",
            "Forbidden exact text is absent." if not present else "Forbidden exact text is present.",
            present,
            False,
        )
    if suffix == "word_limit":
        limit = config.get("max_words")
        if type(limit) is not int or limit < 0:
            return _result(req, "UNKNOWN", "Word limit is missing or is not a non-negative integer.")
        count = word_count(artifact_text)
        return _result(
            req,
            "PASS" if count <= limit else "FAIL",
            "Word count is within the limit." if count <= limit else "Word count exceeds the limit.",
            count,
            limit,
        )
    return _result(req, "UNKNOWN", f"No supported checker for {kind!r}.")


def check_json(req, artifact_path):
    problem = config_problem(req.get("kind"), req.get("config"))
    if problem:
        return _result(req, "UNKNOWN", problem)
    if req["kind"] != "json.field_exact":
        return _result(req, "UNKNOWN", f"No supported checker for {req['kind']!r}.")
    config = req.get("config", {})
    field = config.get("field")
    if not isinstance(field, str) or not field or "expected" not in config:
        return _result(req, "UNKNOWN", "JSON field check needs a field and an expected value.")
    try:
        _check_readable(artifact_path)
        data = read_json(Path(artifact_path))
    except (OSError, UnicodeError, ValueError) as exc:
        return _result(req, "FAIL", f"Artifact is not valid strict JSON: {exc}")
    try:
        observed = get_json_field(data, field)
    except KeyError:
        return _result(req, "FAIL", "Required JSON field is missing.", None, config["expected"])
    expected = config["expected"]
    passed = typed_equal(observed, expected)
    return _result(
        req,
        "PASS" if passed else "FAIL",
        "JSON field matches exactly, with types." if passed else "JSON field differs from the expected value, including type.",
        observed,
        expected,
    )


def _read_csv_rows(path):
    _check_readable(path)
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        if columns is None:
            raise ValueError("CSV header is missing.")
        if len(columns) > MAX_CSV_COLUMNS:
            raise ValueError("CSV exceeds the column limit.")
        if any(not isinstance(name, str) or not name.strip() for name in columns):
            raise ValueError("CSV header contains an empty column name.")
        if len(set(columns)) != len(columns):
            raise ValueError("CSV header contains a duplicate column name.")
        rows = []
        for row in reader:
            if None in row:
                raise ValueError("CSV row has extra fields.")
            if any(value is None for value in row.values()):
                raise ValueError("CSV row is missing a field.")
            rows.append(row)
        if len(rows) > MAX_CSV_ROWS:
            raise ValueError("CSV exceeds the row limit.")
    return columns, rows


def check_csv(req, artifact_path, task_dir, frozen):
    problem = config_problem(req.get("kind"), req.get("config"))
    if problem:
        return _result(req, "UNKNOWN", problem)
    if req["kind"] not in ("csv.columns", "csv.rows_exact", "csv.total_cap"):
        return _result(req, "UNKNOWN", f"No supported checker for {req['kind']!r}.")
    config = req.get("config", {})
    kind = req["kind"]
    try:
        columns, rows = _read_csv_rows(artifact_path)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        return _result(req, "FAIL", f"Artifact is not valid CSV: {exc}")
    if kind == "csv.columns":
        expected = config.get("columns")
        if not isinstance(expected, list) or not expected:
            return _result(req, "UNKNOWN", "CSV column check needs a declared column list.")
        return _result(
            req,
            "PASS" if columns == expected else "FAIL",
            "CSV columns match the declared columns." if columns == expected else "CSV columns differ from the declared columns.",
            columns,
            expected,
        )
    if kind == "csv.rows_exact":
        source_id = config.get("source_id")
        source = next((s for s in frozen.get("sources", []) if s["id"] == source_id), None)
        if source is None:
            return _result(req, "BLOCKED", "Required CSV source is missing from the frozen task.")
        source_path = Path(task_dir) / "sources" / source["name"]
        if source_path.is_symlink() or not source_path.is_file():
            return _result(req, "BLOCKED", "Required CSV source file is missing or is a symlink.")
        try:
            _source_columns, source_rows = _read_csv_rows(source_path)
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            return _result(req, "BLOCKED", f"Required CSV source cannot be read: {exc}")
        return _result(
            req,
            "PASS" if rows == source_rows else "FAIL",
            "CSV rows match the selected source rows exactly." if rows == source_rows else "CSV rows differ from the selected source rows.",
            rows,
            source_rows,
        )
    if kind == "csv.total_cap":
        column = config.get("column")
        cap = config.get("max_value")
        if not isinstance(column, str) or not column:
            return _result(req, "UNKNOWN", "CSV total check needs a column name.")
        if type(cap) not in (int, float) or isinstance(cap, bool):
            return _result(req, "UNKNOWN", "CSV total check needs a numeric cap.")
        if columns is None or column not in columns:
            return _result(req, "FAIL", "CSV total column is missing.", None, cap)
        try:
            cap_decimal = Decimal(str(cap))
            if not cap_decimal.is_finite():
                raise InvalidOperation("Cap is not finite.")
            values = []
            for row in rows:
                value = Decimal(row[column].strip())
                if not value.is_finite():
                    raise InvalidOperation("CSV value is not finite.")
                values.append(value)
            total = sum(values, Decimal("0"))
        except (InvalidOperation, ValueError, AttributeError) as exc:
            return _result(req, "FAIL", f"CSV total column contains a non-finite or non-numeric value: {exc}", None, cap)
        passed = total <= cap_decimal
        observed = int(total) if total == total.to_integral_value() else float(total)
        return _result(
            req,
            "PASS" if passed else "FAIL",
            "CSV total is within the cap." if passed else "CSV total exceeds the cap.",
            observed,
            cap,
        )
    return _result(req, "UNKNOWN", f"No supported checker for {kind!r}.")
