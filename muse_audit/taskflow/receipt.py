"""Human-readable completion receipt.

This readable receipt is the main deliverable. It contains no hashes,
file paths, tool names, protocol names, counts, or huge values. Raw
execution data stays in the machine receipt, which is retained behind
an optional details view.
"""

import json


def _result_sentence(receipt):
    decision = receipt.get("decision", "")
    if decision == "SELECTED_CHECKS_PASS":
        return "Ready for the listed requirements."
    if decision == "REVISE":
        return "Needs fixes before the listed requirements pass."
    if decision == "BLOCKED":
        return "Blocked: a required input is missing or changed."
    return "Not fully verified: some items remain unverified."


def _next_action(receipt):
    statuses = [check["status"] for check in receipt.get("checks", [])]
    if receipt.get("block_reason"):
        return "Restore the original input, or start a newly confirmed task."
    if "BLOCKED" in statuses:
        return "Provide the missing or unchanged input, then ask for a fresh review."
    if "FAIL" in statuses:
        return "Fix the items under Needs attention, then ask for a fresh review."
    if "UNKNOWN" in statuses or "STALE" in statuses:
        return "Treat unverified items as not proven. Do not rely on them as established."
    return "Review the result. The listed checks are current; checklist interpretation still needs your judgment."


def _short_value(value):
    """Render a short observed or expected value, or None when it is not useful in prose."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, str)):
        text = str(value)
        return text if len(text) <= 200 else None
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return None
    if len(text) > 200:
        return None
    return text


def _line(check):
    observed = _short_value(check.get("observed"))
    expected = _short_value(check.get("expected"))
    parts = [check["description"]]
    if observed is not None and expected is not None and observed != expected:
        parts.append(f"observed {observed}, expected {expected}")
    elif observed is not None and check["status"] in ("PASS", "FAIL"):
        parts.append(f"observed {observed}")
    if check["status"] in ("FAIL", "BLOCKED", "STALE", "UNKNOWN") and check.get("reason"):
        parts.append(check["reason"])
    return " — ".join(parts)


def render_readable_receipt(receipt):
    checks = receipt.get("checks", [])
    checked = [check for check in checks if check["status"] == "PASS"]
    attention = [check for check in checks if check["status"] in ("FAIL", "BLOCKED", "STALE")]
    unverified = [check for check in checks if check["status"] == "UNKNOWN"]
    title = receipt.get("title") or ""
    if not title and receipt.get("request"):
        title = receipt["request"].strip().splitlines()[0][:200]
    lines = []
    lines.append(f"Task: {title}")
    lines.append("")
    lines.append(f"Result: {_result_sentence(receipt)}")
    lines.append("")
    lines.append("Checked:")
    if checked:
        for check in checked:
            lines.append(f"- {_line(check)}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("Needs attention:")
    if attention:
        for check in attention:
            lines.append(f"- {_line(check)}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("Remains unverified:")
    if unverified:
        for check in unverified:
            lines.append(f"- {_line(check)}")
    # Checklist coverage itself is never fully verified, even when every
    # listed check passes. Never present this section as empty.
    lines.append("- Checklist coverage itself: the interpreted checklist is not independently verified as complete.")
    lines.append("")
    lines.append(f"Next action: {_next_action(receipt)}")
    lines.append("")
    lines.append("Receipt reference:")
    lines.append(f"- Task: {receipt.get('task_id', '')}")
    lines.append(f"- Receipt date: {receipt.get('generated_at', '')}")
    lines.append("- Raw execution details are kept with the machine receipt, not in this readable receipt.")
    if receipt.get("block_reason"):
        lines.append(f"- Block reason: {receipt['block_reason']}")
    return "\n".join(lines) + "\n"
