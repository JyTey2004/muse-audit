"""One compact result/table/inline receipt. Summaries use actual frozen checker kinds."""
import json
import re

def cell(value):
    if value is None:return 'Not established'
    if isinstance(value,bool):return 'Yes' if value else 'No'
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
    return text.replace('|','/').replace('\n',' ')[:140]

def short_reason(check):
    if check.get('status')=='PASS':return 'Matched the listed check'
    text=str(check.get('reason') or 'Not independently established')
    # User-facing diagnostics must not expose filesystem, hash or protocol details.
    text=re.sub(r'(?<!\w)(?:[A-Za-z]:\\|/)[^\s,;]+','[input]',text)
    text=re.sub(r'\b[a-fA-F0-9]{40,}\b','[binding]',text)
    if any(word in text.lower() for word in ('traceback','json-rpc','stdio','streamable','mcp')):
        text='Verification could not establish this item; see optional details'
    return cell(text)

def compact_view(receipt,reference,artifact_name,requirements=()):
    decision=receipt.get('decision')
    status={'SELECTED_CHECKS_PASS':'Selected checks passed','REVISE':'Needs a correction','BLOCKED':'Verification blocked'}.get(decision,'Some items remain unverified')
    kinds={req['id']:req['kind'] for req in requirements}
    useful=''
    for check in receipt.get('checks',[]):
        if check.get('status') not in ('PASS','FAIL') or type(check.get('observed')) not in (int,float):continue
        kind=kinds.get(check.get('requirement_id'))
        if kind=='csv.total_cap':useful=f"Total {cell(check['observed'])}; limit {cell(check['expected'])}. ";break
        if kind in ('text.word_limit','markdown.word_limit'):useful=f"Word count {cell(check['observed'])}; maximum {cell(check['expected'])}. ";break
    lines=[f'{useful}{status}. Result: {artifact_name}.','', '| Check | Observed | Required | Result | Reason |','|---|---|---|---|---|']
    for check in receipt.get('checks',[]):
        lines.append(f"| {cell(check.get('description') or check.get('requirement_id'))} | {cell(check.get('observed'))} | {cell(check.get('expected'))} | {check['status']} | {short_reason(check)} |")
    lines.append('| Checklist completeness and source authenticity | Not independently established | Human review | UNKNOWN | Meaning and real-world accuracy may need user review |')
    classification='Declared synthetic data' if receipt.get('synthetic') is True else 'Selected current-task inputs' if receipt.get('synthetic') is False else 'Input classification unverified'
    lines.extend(['',f"Verification receipt (completion pending): {reference} · {receipt.get('generated_at','')} · {classification}; caller-declared, not detected. Interpreted checklist only; source authenticity, semantics and privacy unverified."])
    return '\n'.join(lines)
