"""Readable local report; no server or external assets."""
import html
import json


def markdown(receipt):
    lines = [f"# {receipt['title']}", '', f"**{receipt['decision']}** — selected checks only", '', receipt['coverage']['warning'], '',
             f"Declared requirements: {receipt['coverage']['declared_requirements']} · Executed supported checks: {receipt['coverage']['supported_checks_executed']}", '',
             ' | '.join(f'{k}: {v}' for k,v in receipt['counts'].items()), '']
    for check in receipt['checks']:
        lines.extend([f"## {check['status']} · {check['description']}", f"ID: `{check['requirement_id']}` · {check['mode']}", '', check['reason'], '',
                      f"Observed: `{json.dumps(check['observed'], ensure_ascii=False)}`", f"Expected: `{json.dumps(check['expected'], ensure_ascii=False)}`", '',
                      'Locations: '+', '.join(check['locations']), ''])
    lines.extend(['---','No model was called. Supplied source authenticity is not established. Full rechecks include protected commitments.',
                  f"Contract: `{receipt['binding']['contract_sha256']}`", f"Artifact: `{receipt['binding']['artifact']['sha256']}`"])
    return '\n'.join(lines)+'\n'


def html_report(receipt):
    esc = html.escape
    cards = []
    for c in receipt['checks']:
        cards.append(f"<article><h2><span class='{c['status']}'>{c['status']}</span> {esc(c['description'])}</h2><p>{esc(c['reason'])}</p><dl><dt>Observed</dt><dd><code>{esc(json.dumps(c['observed'],ensure_ascii=False))}</code></dd><dt>Expected</dt><dd><code>{esc(json.dumps(c['expected'],ensure_ascii=False))}</code></dd></dl><p class='muted'>{esc(' · '.join(c['locations']))}</p></article>")
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{esc(receipt['title'])}</title><style>body{{font:16px/1.55 system-ui;background:#f4f7f9;color:#173042;max-width:980px;margin:32px auto;padding:0 20px}}h1{{font-size:34px}}h2{{font-size:19px}}article,header{{background:white;padding:22px;border:1px solid #d9e3e9;border-radius:12px;margin:18px 0}}.PASS{{color:#116743}}.FAIL{{color:#a22320}}.UNKNOWN,.BLOCKED,.STALE{{color:#815500}}code{{white-space:pre-wrap;overflow-wrap:anywhere}}.muted,footer{{color:#566a75}}dt{{font-weight:600}}dd{{margin:0 0 10px}}</style><header><p>MUSE AUDIT · OFFLINE PROTOTYPE · SELECTED LOCAL JOB</p><h1>{esc(receipt['title'])}</h1><h2>{receipt['decision'].replace('_',' ')}</h2><p>{esc(receipt['coverage']['warning'])}</p><b>{esc(' · '.join(f'{k}: {v}' for k,v in receipt['counts'].items()))}</b><p>{receipt['coverage']['declared_requirements']} declared requirements; {receipt['coverage']['supported_checks_executed']} supported checks executed.</p></header>{''.join(cards)}<footer>No live Muse/model call. Source truth is assumed, not authenticated. This is not a global ready badge.<br>Artifact SHA-256: <code>{receipt['binding']['artifact']['sha256']}</code></footer></html>"""
