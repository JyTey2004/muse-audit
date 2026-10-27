"""Offline CLI: audit, review patch, explicitly write a new repaired copy, recheck."""
import argparse
import json
from pathlib import Path
import sys
from . import core
from .io import read_json
from .report import markdown, html_report


def emit(result, destination):
    text = json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    if destination:
        Path(destination).write_text(text,encoding='utf-8')
    else:
        print(text,end='')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=Path('.'))
    sub = p.add_subparsers(dest='command',required=True)
    sub.add_parser('capabilities')
    for command in ('audit','plan','recheck','apply'):
        item = sub.add_parser(command)
        item.add_argument('job',help='Relative job.json path inside --workspace')
        item.add_argument('--json-out')
        if command == 'audit':
            item.add_argument('--report',help='Write readable HTML (.html) or Markdown report')
        if command == 'recheck':
            item.add_argument('--receipt',required=True)
        if command == 'apply':
            item.add_argument('--plan',required=True)
            item.add_argument('--output',required=True,type=Path,help='New directory only; never overwrites')
            item.add_argument('--approve-reviewed-plan',action='store_true',help='Explicit local confirmation; inspect plan before use')
    args = p.parse_args()
    try:
        if args.command == 'capabilities':
            emit(core.capabilities(),None)
            return 0
        if args.command == 'audit':
            result = core.audit_job(args.workspace,args.job)
            if args.report:
                target = Path(args.report)
                target.write_text(html_report(result) if target.suffix == '.html' else markdown(result),encoding='utf-8')
        elif args.command == 'plan':
            result = core.prepare_repair(args.workspace,args.job)
        elif args.command == 'recheck':
            result = core.recheck(args.workspace,args.job,read_json(args.receipt))
        else:
            if not args.approve_reviewed_plan:
                raise ValueError('Review the plan first, then explicitly pass --approve-reviewed-plan')
            result = core.apply_repair(args.workspace,args.job,read_json(args.plan),args.output)
        emit(result,args.json_out)
        # Nonzero means the selected job is not fully verified, not a command crash.
        current = result.get('fresh',result)
        return 2 if current.get('decision') in ('REVISE','UNRESOLVED') or result.get('status') in ('STALE','INVALID_EVIDENCE') else 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'No audit acceptance: {exc}',file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
