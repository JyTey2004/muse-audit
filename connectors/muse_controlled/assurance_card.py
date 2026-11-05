"""Snapshot-only Muse widget. Text comes from guarded controller records.

This UI cannot run tools, authorize delivery, update the result or recheck it.
The file attachment stays outside the card. Source/context trust is unchanged.
"""
from datetime import datetime
from html import escape
import re

def text(value,limit=220):
    return escape(str(value)[:limit],quote=True)

def passed(report):
    checks=report.get('checks',[])
    return bool(report.get('state')=='COMPLETED' and report.get('audit_record_matched') is True
        and report.get('result') and checks and all(c.get('status')=='PASS' for c in checks)
        and (report.get('mcp_check') or {}).get('state')=='PASS'
        and any(a.get('id')=='result_delivered' for a in report.get('actions',[])))

def fallback(report):
    if passed(report):return f"Stardive: {len(report['checks'])} {'check' if len(report['checks'])==1 else 'checks'} passed. Tap to see what Muse did."
    return 'Stardive: delivery blocked. Tap to see actions and the verification issue.'

def native_payloads(report):
    """Built-in Muse cards; a tap requests the immutable, task-bound details view."""
    checks=report.get('checks',[]);ok=passed(report)
    records={a.get('id'):a for a in report.get('actions',[]) if isinstance(a,dict)}
    ref=report.get('receipt_ref') or '';tid=report.get('task_id') or ''
    audited=bool(report.get('audit_record_matched') is True and re.fullmatch(r'receipt-[a-f0-9]{32}',ref) and 'receipt_saved' in records)
    artifact=report.get('artifact_name') or 'your file'
    request=f"Show what Muse did for {artifact} (Stardive {tid.removeprefix('task-')})." if re.fullmatch(r'task-[a-f0-9]{16}',tid) else None
    stamp=(report.get('mcp_check') or {}).get('checked_at') or report.get('receipt_date')
    try:when=datetime.fromisoformat(stamp).strftime('%d %b %Y · %H:%M UTC')
    except (TypeError,ValueError):when='No completed audit'
    footer={'title':'Audited by Stardive' if audited else 'Audit not completed · Stardive','subtitle':when+((' · Receipt '+ref.removeprefix('receipt-')[:8]) if audited else ''),'tertiary_title':'Selected requirements only','type':'generic','data':{}}
    title='Task fulfilled · listed requirements' if ok else 'Delivery blocked'
    summary_row={'title':title,'subtitle':f"{len(checks)} checks passed · See what Stardive checked" if ok and request else 'See checks and the verification issue' if request else 'Required task evidence is unavailable','type':'send_message' if request else 'generic','data':{'text':request} if request else {}}
    original=report.get('request')
    request_row={'title':'What you asked for','subtitle':str(original)[:1200] if isinstance(original,str) and original else 'Original wording unavailable in this historical snapshot.','type':'generic','data':{}}
    rows=[]
    for key,label in [('request_saved','Saved your request'),('file_prepared','Prepared '+str(artifact)),('requirements_checked',f"Checked {len(checks)} {'requirement' if len(checks)==1 else 'requirements'}" if checks else 'Ran verification'),('result_delivered','Delivered the verified file')]:
        if key in records:
            row={'title':label,'type':'generic','data':{}}
            if key=='requirements_checked':
                statuses=[c.get('status','UNKNOWN') for c in checks]
                labels={'PASS':'passed','FAIL':'failed','UNKNOWN':'unverified','BLOCKED':'blocked','STALE':'outdated'}
                row['subtitle']=' · '.join(f"{statuses.count(s)} {labels[s]}" for s in labels if s in statuses)
                if 0<len(checks)<=4:row['tertiary_title']=' · '.join(str(c.get('check') or 'Requirement')[:80] for c in checks)
            rows.append(row)
    rows.append(request_row)
    for c in checks:
        shown=lambda value:'Not established' if value is None else str(value).lower() if isinstance(value,bool) else str(value)[:100]
        rows.append({'title':str(c.get('check') or 'Requirement')[:160],'subtitle':f"{c.get('status','UNKNOWN')} · Observed: {shown(c.get('observed'))} · Required: {shown(c.get('required'))}",'type':'generic','data':{}})
    # Muse caps native list cards at20 rows. Every non-PASS remains represented;
    # excessive detail uses an explicit count, rather than silently hiding a failure.
    if len(rows)>18:
        hidden=len(rows)-17;rows=rows[:17]+[{'title':f'{hidden} more recorded checks','subtitle':('Listed checks passed; ' if ok else 'Verification remains blocked; ')+'full checks stay in the audit record.','type':'generic','data':{}}]
    if not ok:rows.append({'title':'Delivery withheld','subtitle':'A required check failed or verification is incomplete. No file was delivered.','type':'generic','data':{}})
    rows.append(footer)
    return {'task_id':tid,'version_id':report.get('version_id'),'receipt_ref':report.get('receipt_ref'),'request_sha256':report.get('request_sha256'),'artifact_sha256':report.get('artifact_sha256'),'actions':report.get('actions',[]),'detail_request':request,
        'summary':{'title':'Stardive verification','items':[summary_row,request_row,footer],'present_now':False},
        'details':{'title':'What Muse did','subtitle':str(artifact),'items':rows,'present_now':False}}

def render_card(report):
    from pathlib import Path
    import importlib.util
    spec=importlib.util.spec_from_file_location('stardive_verification_view',Path(__file__).with_name('verification_view.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    records={a.get('id'):a for a in report.get('actions',[]) if isinstance(a,dict)}
    audited=bool(report.get('audit_record_matched') is True and re.fullmatch(r'receipt-[a-f0-9]{32}',report.get('receipt_ref') or '') and 'receipt_saved' in records)
    return module.render(report,passed(report),audited)

def legacy_render_card(report):
    ok=passed(report);checks=report.get('checks',[])
    records={a.get('id'):a for a in report.get('actions',[]) if isinstance(a,dict)}
    ref=report.get('receipt_ref') or ''
    audited=bool(report.get('audit_record_matched') is True and re.fullmatch(r'receipt-[a-f0-9]{32}',ref) and 'receipt_saved' in records)
    title=f"{len(checks)} {'check' if len(checks)==1 else 'checks'} passed" if ok else 'Delivery blocked'
    rows=[]
    for key,label in [('request_saved','Saved your request'),('file_prepared','Prepared '+str(report.get('artifact_name') or 'your file')),('requirements_checked',f"Checked {len(checks)} {'requirement' if len(checks)==1 else 'requirements'}" if checks else 'Ran verification'),('result_delivered','Delivered the verified file')]:
        if key in records:
            status='done' if records[key].get('status') in ('DONE','PASS') else 'blocked'
            rows.append(f'<li class="sd-step {status}"><span class="sd-mark" aria-hidden="true"></span><span>{text(label)}</span></li>')
    if not ok:
        rows.append('<li class="sd-step blocked"><span class="sd-mark" aria-hidden="true"></span><span>Delivery withheld</span></li>')
    if not rows:rows.append('<li>No recorded actions are available.</li>')
    details=[]
    for c in checks:
        state=c.get('status','UNKNOWN')
        observed=c.get('observed');required=c.get('required')
        def value(v):return 'Not established' if v is None else str(v).lower() if isinstance(v,bool) else str(v)
        note='' if state=='PASS' else f'<span class="sd-values">Observed: {text(value(observed))} · Required: {text(value(required))}</span>'
        details.append(f'<li><span>{text(c.get("check") or "Requirement")}{note}</span><span class="sd-status">{text(state)}</span></li>')
    statuses={c.get('status') for c in checks}
    issue='A required check failed.' if 'FAIL' in statuses else 'A requirement could not be verified.' if 'UNKNOWN' in statuses else 'Verification was not completed.' if 'requirements_checked' not in records else 'The result could not be released safely.'
    reason='' if ok else '<p class="sd-reason">'+issue+' No file was delivered.</p>'
    checked=report.get('mcp_check') or {}
    stamp=checked.get('checked_at') or report.get('receipt_date')
    try:when=datetime.fromisoformat(stamp).strftime('%d %b %Y · %H:%M UTC')
    except (TypeError,ValueError):when='No completed audit'
    footer='Audited by Stardive' if audited else 'Audit not completed · Stardive'
    short_ref=ref.removeprefix('receipt-')[:8] if audited else ''
    receipt_line=f'<span title="{text(ref)}">Receipt {text(short_ref)}</span>' if short_ref else ''
    mark='<path d="m8 12 3 3 5-6"/>' if ok else '<path d="M12 8v5m0 3h.01"/>'
    # All variable values are escaped HTML text/attributes, never executable code.
    return '''<style>
.sd-card,.sd-card *{box-sizing:border-box}.sd-card{font:14px/1.45 system-ui,sans-serif;max-width:520px;width:100%;color:var(--hatch-widget-text);background:var(--hatch-widget-surface);border:1px solid var(--hatch-widget-border);border-radius:16px;overflow:hidden;overflow-wrap:anywhere}.sd-toggle{font:inherit;display:flex;align-items:center;gap:12px;width:100%;padding:17px 18px;border:0;cursor:pointer;background:transparent;color:inherit;text-align:left}.sd-toggle:focus-visible{outline:2px solid var(--hatch-widget-focus,var(--hatch-widget-accent));outline-offset:-4px;border-radius:12px}.sd-icon{display:grid;place-items:center;width:32px;height:32px;flex:none;border:1px solid var(--hatch-widget-border);border-radius:50%;color:var(--hatch-widget-accent)}.sd-toggle strong{font-size:15px;font-weight:600}.sd-sub{display:block;font-size:12px;color:var(--hatch-widget-muted);margin-top:2px}.sd-chevron{margin-left:auto;width:8px;height:8px;flex:none;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(45deg)}[aria-expanded=true] .sd-chevron{transform:rotate(225deg)}.sd-panel{padding:0 18px 16px}.sd-panel[hidden]{display:none}.sd-panel h3{margin:4px 0 12px;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--hatch-widget-muted);font-weight:500}.sd-steps{list-style:none;margin:0;padding:0;display:grid;gap:13px}.sd-step{display:flex;gap:10px;align-items:start}.sd-mark{position:relative;display:inline-block;flex:none;width:16px;height:16px;margin-top:2px;border:1px solid var(--hatch-widget-border);border-radius:50%;color:var(--hatch-widget-accent)}.done .sd-mark:after{content:"";position:absolute;width:6px;height:3px;border-left:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(-45deg);left:4px;top:4px}.blocked .sd-mark:after{content:"!";position:absolute;inset:0;text-align:center;font:600 11px/14px system-ui}.sd-reason{font-size:13px;padding:10px 0 0;margin:6px 0 0}.sd-checks{list-style:none;margin:16px 0 0;padding:12px 0 0;border-top:1px solid var(--hatch-widget-border);display:grid;gap:8px;font-size:12px}.sd-checks li{display:flex;gap:12px;justify-content:space-between}.sd-checks li>span:first-child{min-width:0}.sd-status{flex:none;font-size:11px;color:var(--hatch-widget-muted)}.sd-values{display:block;color:var(--hatch-widget-muted);margin-top:3px}.sd-scope{font-size:11px;line-height:1.5;color:var(--hatch-widget-muted);margin:14px 0 0}.sd-footer{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px 12px;padding:11px 18px;border-top:1px solid var(--hatch-widget-border);font-size:11px;color:var(--hatch-widget-muted)}.sd-brand{font-weight:600}.sd-meta{display:flex;flex-wrap:wrap;gap:4px 10px;font-size:10px}
</style>'''+f'''<section class="sd-card" aria-label="Stardive assurance">
<button type="button" class="sd-toggle" id="sd-toggle" aria-expanded="false" aria-controls="sd-actions"><span class="sd-icon" aria-hidden="true"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z"/>{mark}</svg></span><span><strong>{text(title)}</strong><span class="sd-sub" id="sd-hint">See what Muse did</span></span><span class="sd-chevron" aria-hidden="true"></span></button>
<div class="sd-panel" id="sd-actions" hidden><h3>What Muse did</h3><ol class="sd-steps">{''.join(rows)}</ol>{reason}<ul class="sd-checks" aria-label="Requirement checks">{''.join(details)}</ul><p class="sd-scope">{text(report.get('scope') or 'Only the listed requirements were checked.')}</p></div>
<footer class="sd-footer"><span class="sd-brand">{text(footer)}</span><span class="sd-meta"><span>{text(when)}</span>{receipt_line}</span></footer></section>'''+'''
<script>(function(){
var bridge=window.hatchWidget;
var state=bridge?bridge.getState({open:false}):{open:false};
var button=document.getElementById('sd-toggle'),panel=document.getElementById('sd-actions'),hint=document.getElementById('sd-hint');
function render(){panel.hidden=!state.open;button.setAttribute('aria-expanded',String(!!state.open));hint.textContent=state.open?'Hide actions':'See what Muse did';}
button.addEventListener('click',function(){state={open:!state.open};if(bridge)bridge.setState(state);render();});
window.addEventListener('hatch-widget-state',function(e){if(e&&e.detail&&e.detail.state){state=e.detail.state;render();}});
render();
})();</script>'''
