"""Reproducible offline checkpoint in a NEW output directory; no live model."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from . import core
from .io import read_json
from .report import html_report, markdown


def save(path, value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def run(examples, output):
    examples, output = Path(examples).resolve(), Path(output)
    if output.exists():
        raise ValueError('Choose a NEW demo output directory; existing results are never overwritten')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.muse-demo-',dir=output.parent) as temporary:
        root=Path(temporary)/'result'; root.mkdir()
        shutil.copytree(examples,root/'inputs')
        summary={'synthetic':True,'model_calls':0,'muse_integration':'NOT_TESTED','jobs':{}}
        for slug in ('home_office','study_summary'):
            job=f'{slug}/job.json'
            initial=core.audit_job(root/'inputs',job)
            plan=core.prepare_repair(root/'inputs',job)
            # Demo fixture operations are declared, deterministic and synthetic.
            repaired=core.apply_repair(root/'inputs',job,plan,root/f'{slug}-repaired')
            for name,receipt in (('initial',initial),('repaired',repaired)):
                prefix=root/f'{slug}-{name}'
                save(prefix.with_suffix('.json'),receipt)
                prefix.with_suffix('.html').write_text(html_report(receipt),encoding='utf-8')
                prefix.with_suffix('.md').write_text(markdown(receipt),encoding='utf-8')
            save(root/f'{slug}-plan.json',plan)
            save(root/f'{slug}-old-receipt-recheck.json',core.recheck(root/f'{slug}-repaired','job.json',initial))
            summary['jobs'][slug]={'initial':initial['counts'],'after_repair':repaired['counts'],'decision_after_repair':repaired['decision']}
        changed=root/'home-office-source-changed'
        shutil.copytree(root/'home_office-repaired',changed)
        source=read_json(changed/'prices.json'); source['amounts']['delivery']+=1000
        save(changed/'prices.json',source)  # Deliberately leave source version label unchanged.
        prior=read_json(root/'home_office-repaired.json')
        rechecked=core.recheck(changed,'job.json',prior)
        save(root/'source-change-recheck.json',rechecked)
        (root/'source-change.html').write_text(html_report(rechecked['fresh']),encoding='utf-8')
        summary['source_change']={'old_evidence':rechecked['status'],'changed_bindings':rechecked['changed_bindings'],'fresh_counts':rechecked['fresh']['counts']}
        save(root/'summary.json',summary)
        (root/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Muse audit: offline checkpoint</title><style>body{font:18px/1.6 system-ui;max-width:850px;margin:50px auto;padding:24px;color:#173042}li{margin:12px 0}</style><h1>Check, review, repair, recheck</h1><p>Two hand-authored synthetic jobs. Real native files and deterministic checks. No Muse/model call. Open any report below.</p><h2>1. Home-office budget</h2><ul><li><a href="home_office-initial.html">Initial: missing required delivery fee</a></li><li><a href="home_office-plan.json">Review the exact fee patch</a></li><li><a href="home_office-repaired.html">After repair: honest cap failure remains</a></li><li><a href="source-change-recheck.json">Source-change evidence: old receipt becomes STALE</a> · <a href="source-change.html">fresh checks</a></li></ul><h2>2. Study summary</h2><ul><li><a href="study_summary-initial.html">Initial: copied quote differs from source</a></li><li><a href="study_summary-plan.json">Review the exact paragraph patch</a></li><li><a href="study_summary-repaired.html">After repair: exact quote fixed; causal claim still UNKNOWN</a></li></ul><h2>What to test</h2><p>Can you locate the evidence, understand the preserved commitments, distinguish a repaired supported check from an unverified claim, and identify which decision still needs you?</p><p>Sources are assumed, not authenticated. These results are not global artifact approval or measured user-study outcomes.</p></html>''',encoding='utf-8')
        root.rename(output)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--examples',type=Path,default=Path(__file__).resolve().parents[1]/'examples')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(run(args.examples,args.output),indent=2))


if __name__=='__main__':
    main()
