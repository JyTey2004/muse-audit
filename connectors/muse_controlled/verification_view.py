"""Plain-language snapshot of facts supplied by the guarded controller.

The local disclosure cannot call tools, change a receipt or authorize delivery.
"""
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo
import json
import re


def safe(value):
    return escape(str(value), quote=True)


def value_text(value):
    if value is None:
        return 'Not available'
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def check_title(check):
    title = str(check.get('check') or 'Requested detail')
    # Humanize the checker's exact JSON-field label, without rewriting prose.
    field = re.fullmatch(r'([a-z][a-z0-9_]*) is .+', title)
    if field:
        return field[1].replace('_', ' ').capitalize()
    return title


def render(report, ok, audited):
    checks = report.get('checks') or []
    counts = {key: sum(c.get('status') == key for c in checks)
              for key in ('PASS', 'FAIL', 'UNKNOWN', 'BLOCKED', 'STALE', 'PENDING')}
    headline = 'All set!' if ok else 'Your file needs a fix' if counts['FAIL'] else 'Your file is not ready'
    if not audited:
        headline = 'Your file has not been checked'
    if ok:
        explanation = 'Your file is ready. We checked the details below for you.'
    elif counts['FAIL']:
        explanation = 'Some details do not match your request. We have held back the file.'
    elif counts['STALE']:
        explanation = 'The earlier check is out of date. We have held back the file.'
    elif not audited:
        explanation = 'The check was not completed. We have held back the file.'
    else:
        explanation = 'Some details could not be confirmed. We have held back the file.'
    request = report.get('request')
    request_html = safe(request) if isinstance(request, str) and request else 'The original wording is unavailable in this saved view.'
    stamp = (report.get('mcp_check') or {}).get('checked_at') or report.get('receipt_date')
    try:
        stamp = datetime.fromisoformat(stamp).astimezone(ZoneInfo('Asia/Singapore')).strftime('%d %b · %I:%M %p SGT').replace(' 0', ' ')
    except (ValueError, TypeError):
        stamp = 'Check not completed'
    ref = str(report.get('receipt_ref') or '')
    receipt = 'Receipt ' + ref.removeprefix('receipt-')[:8] if audited else 'No receipt yet'
    check_rows = []
    for check in checks:
        state = check.get('status', 'UNKNOWN')
        label = {'PASS': 'Passed', 'FAIL': 'Needs fixing', 'UNKNOWN': 'Not confirmed',
                 'BLOCKED': 'Not confirmed', 'STALE': 'Needs a new check', 'PENDING': 'Not checked yet'}.get(state, 'Not confirmed')
        check_rows.append('<li class="sv-check"><div class="sv-check-title"><span>' + safe(check_title(check)) +
                          '</span><span class="sv-check-state ' + ('sv-pass' if state == 'PASS' else 'sv-attention') + '">' + label +
                          '</span></div><div class="sv-comparison"><span><small>You asked for</small>' + safe(value_text(check.get('required'))) +
                          '</span><span><small>In your file</small>' + safe(value_text(check.get('observed'))) + '</span></div></li>')
    if not check_rows:
        check_rows.append('<li class="sv-empty">No completed checks yet. The file has been held back.</li>')
    actions = []
    labels = {'request_saved': 'Saved your request', 'file_prepared': 'Created your file',
              'requirements_checked': 'Checked the details', 'result_delivered': 'Delivered your file'}
    for action in report.get('actions') or []:
        key = action.get('id')
        if key not in labels or (key == 'result_delivered' and not ok):
            continue
        status = {'DONE': 'Done', 'PASS': 'Passed'}.get(action.get('status'), 'Needs attention')
        actions.append('<li><span>' + safe(labels[key]) + '</span><span class="sv-action-state">' + status + '</span></li>')
    if not ok:
        actions.append('<li><span>Held back the file</span><span class="sv-action-state">Not delivered</span></li>')
    count_line = str(counts['PASS']) + ' ' + ('check' if counts['PASS'] == 1 else 'checks') + ' passed'
    if not audited:
        count_line = 'Check not completed'
    elif not ok:
        attention = sum(counts[key] for key in ('FAIL', 'UNKNOWN', 'BLOCKED', 'STALE', 'PENDING'))
        if attention:
            count_line += ' · ' + str(attention) + ' ' + ('needs' if attention == 1 else 'need') + ' attention'
    artifact = report.get('artifact_name') or 'Your file'
    footer = 'Audited by Stardive' if audited else 'Not yet audited · Stardive'
    mark = '<path d="m8 12 3 3 5-6"/>' if ok else '<path d="M12 8v5m0 3h.01"/>'
    return '''<style>
.sv-card,.sv-card *{box-sizing:border-box}
.sv-card{--sv-ink:var(--hatch-widget-text,#17223b);--sv-muted:var(--hatch-widget-muted,#5a6680);--sv-surface:var(--hatch-widget-surface,#fff);--sv-line:var(--hatch-widget-border,#dce3f0);--sv-accent:var(--hatch-widget-accent,#3157ce);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--sv-ink);background:var(--sv-surface);max-width:440px;width:100%;height:240px;display:flex;flex-direction:column;border:1px solid var(--sv-line);border-radius:14px;overflow:hidden;overflow-wrap:anywhere}
.sv-top{display:flex;align-items:center;gap:8px;padding:13px 14px 0;flex-shrink:0}.sv-top svg{color:var(--sv-accent);flex-shrink:0}.sv-top h2{font-size:18px;letter-spacing:-.025em;font-weight:600;line-height:1.25;margin:0}
.sv-main{padding:10px 14px;flex:1;min-height:0;overflow:auto}.sv-count{margin:0;font-size:12px;font-weight:500}.sv-explanation{margin:7px 0 0;font-size:13px;color:var(--sv-muted)}.sv-artifact{display:flex;gap:7px;align-items:center;margin:10px 0 0;font-size:11px;color:var(--sv-muted)}.sv-artifact svg{color:var(--sv-accent);flex-shrink:0}.sv-artifact span{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sv-toggle{display:flex;justify-content:space-between;align-items:center;font:500 12px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;width:100%;padding:9px 14px;border:0;border-top:1px solid var(--sv-line);background:transparent;color:var(--sv-ink);text-align:left;cursor:pointer;flex-shrink:0}.sv-toggle:focus-visible{outline:2px solid var(--sv-accent);outline-offset:-3px}.sv-arrow{transition:transform .2s}.sv-toggle[aria-expanded=true] .sv-arrow{transform:rotate(180deg)}
.sv-panel{padding:0 14px 10px;flex:1;min-height:0;overflow:auto}.sv-main[hidden],.sv-panel[hidden]{display:none}.sv-panel h3{font-size:11px;color:var(--sv-muted);font-weight:600;margin:10px 0 5px}.sv-actions ol{list-style:none;margin:0;padding:0;font-size:11px}.sv-actions li{display:flex;justify-content:space-between;gap:10px;padding:3px 0}.sv-action-state{color:var(--sv-muted);white-space:nowrap;font-size:10px}
.sv-checks{list-style:none;padding:0;margin:0}.sv-check{padding:11px 0;border-bottom:1px solid var(--sv-line)}.sv-check-title{display:flex;justify-content:space-between;gap:12px;font-size:13px;font-weight:500}.sv-check-state{font-size:11px;white-space:nowrap}.sv-pass{color:var(--sv-accent)}.sv-attention{font-weight:600}.sv-comparison{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:7px;font-size:12px}.sv-comparison>span{min-width:0}.sv-comparison small{display:block;color:var(--sv-muted);font-size:10px;margin-bottom:2px}.sv-empty{padding:10px 0;font-size:12px}.sv-request p{margin:0;font-size:12px;white-space:pre-wrap}.sv-scope{font-size:11px;color:var(--sv-muted);margin:12px 0 0}
.sv-footer{padding:8px 14px;border-top:1px solid var(--sv-line);display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px 10px;font-size:9px;color:var(--sv-muted);flex-shrink:0}.sv-footer strong{font-size:10px;font-weight:500}.sv-meta{display:flex;flex-wrap:wrap;gap:4px 7px}@media(prefers-reduced-motion:reduce){.sv-arrow{transition:none}}
</style>''' + f'''<section class="sv-card" aria-label="Stardive assurance card">
<div class="sv-top"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m12 3 8 4v5c0 5-8 9-8 9s-8-4-8-9V7z"/>{mark}</svg><h2>{safe(headline)}</h2></div>
<div class="sv-main" id="sv-summary"><p class="sv-count">{safe(count_line)}</p><p class="sv-explanation">{safe(explanation)}</p><div class="sv-artifact"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M14 2H5v20h14V7zM14 2v6h5"/></svg><span title="{safe(artifact)}">{safe(artifact)}</span></div></div>
<button type="button" class="sv-toggle" id="sv-toggle" aria-expanded="false" aria-controls="sv-checks"><span id="sv-hint">See details</span><svg class="sv-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></button>
<div class="sv-panel" id="sv-checks" hidden><section class="sv-actions" aria-label="What Muse did"><h3>What Muse did</h3><ol>{''.join(actions)}</ol></section><h3>What Stardive checked</h3><ul class="sv-checks">{''.join(check_rows)}</ul><section class="sv-request"><h3>Your request</h3><p>{request_html}</p></section><p class="sv-scope">These checks cover only the details shown here, at the time below.</p></div>
<footer class="sv-footer"><strong>{safe(footer)}</strong><span class="sv-meta"><span>{safe(stamp)}</span><span title="{safe(ref)}">{safe(receipt)}</span></span></footer></section>''' + '''
<script>(function(){var bridge=window.hatchWidget;var state=bridge?bridge.getState({open:false}):{open:false};var button=document.getElementById('sv-toggle'),summary=document.getElementById('sv-summary'),panel=document.getElementById('sv-checks'),hint=document.getElementById('sv-hint');function render(){summary.hidden=!!state.open;panel.hidden=!state.open;button.setAttribute('aria-expanded',String(!!state.open));hint.textContent=state.open?'Hide details':'See details';}button.addEventListener('click',function(){state={open:!state.open};if(bridge)bridge.setState(state);render();});window.addEventListener('hatch-widget-state',function(e){if(e&&e.detail&&e.detail.state){state=e.detail.state;render();}});render();})();</script>'''
