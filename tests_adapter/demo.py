"""Offline reproducible adapter mechanics. Host execution is a TEST DOUBLE, not Claude."""
import argparse
import json
from pathlib import Path
from fixture import collect,BAD
from muse_audit.claude_adapter.review import record_receipt,review_run
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
if args.output.exists():raise SystemExit('Use a fresh output directory')
args.output.mkdir(parents=True)
root,work,run=collect(args.output)
first=record_receipt(root,'owner',run,'Done')
(work/'app.mjs').write_text(BAD);second=review_run(root,'owner',run,'Done')
(root/run/'build-stream.jsonl').unlink();missing=review_run(root,'owner',run,'Done')
summary={'disclosure':'OFFLINE host test double; actual fixed Node checker and persisted store; no Claude/model call',
 'run_id':run,'first':first,'changed_app':second,'missing_host_evidence':missing}
(args.output/'offline-demo.json').write_text(json.dumps(summary,indent=2));print(json.dumps({'output':str(args.output),'first':first['counts'],'changed_app':second['counts'],'missing':missing['counts'],'disclosure':summary['disclosure']},indent=2))
