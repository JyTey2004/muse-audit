"""Explicit local synthetic CLI; MCP remains read-only."""
import argparse
import json
from pathlib import Path
from ..io import read_json
from .contracts import expense_contract, create_contract, approve_contract
from .runner import Runner


def write_new(path, data):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Bounded synthetic task acceptance. No model or external-service calls.')
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--principal', default='local-demo')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('template');p.add_argument('--max-total-cents', type=int, default=2000)
    p = sub.add_parser('register');p.add_argument('--contract', type=Path, required=True)
    p = sub.add_parser('approve-contract');p.add_argument('--contract-id', required=True);p.add_argument('--digest', required=True);p.add_argument('--approve-reviewed-contract', action='store_true')
    p = sub.add_parser('run');p.add_argument('--contract-id', required=True);p.add_argument('--pending', action='store_true')
    p = sub.add_parser('review');p.add_argument('--run-id', required=True);p.add_argument('--claim', default='Done. Your expense tracker is correct.');p.add_argument('--record-receipt', action='store_true')
    p = sub.add_parser('plan');p.add_argument('--run-id', required=True);p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('apply');p.add_argument('--plan', type=Path, required=True);p.add_argument('--approved-digest', required=True);p.add_argument('--approve-reviewed-plan', action='store_true')
    p = sub.add_parser('mutate-synthetic');p.add_argument('--run-id', required=True);p.add_argument('--kind', choices=('source','result'), required=True);p.add_argument('--json', type=Path);p.add_argument('--withhold', action='store_true')
    p = sub.add_parser('reset');p.add_argument('--run-id', required=True)
    p = sub.add_parser('import-receipt');p.add_argument('--file', type=Path, required=True)
    p = sub.add_parser('export-receipt');p.add_argument('--run-id', required=True);p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    runner = Runner(args.store, args.principal)
    try:
        if args.command == 'template':
            result = expense_contract(args.max_total_cents)
        elif args.command == 'register':
            result = create_contract(runner.store, args.principal, read_json(args.contract))
        elif args.command == 'approve-contract':
            result = approve_contract(runner.store, args.principal, args.contract_id, args.digest, reviewed=args.approve_reviewed_contract)
        elif args.command == 'run':
            result = {'run_id': runner.start(args.contract_id, pending=args.pending)}
        elif args.command == 'review':
            result = runner.review(args.run_id, args.claim, save=args.record_receipt)
        elif args.command == 'plan':
            result = runner.prepare(args.run_id);write_new(args.output, result)
        elif args.command == 'apply':
            result = runner.apply(read_json(args.plan), args.approved_digest, reviewed=args.approve_reviewed_plan)
        elif args.command == 'mutate-synthetic':
            result = runner.mutate(args.run_id, args.kind, read_json(args.json) if args.json else None, available=not args.withhold)
        elif args.command == 'reset':
            result = {'run_id': runner.reset(args.run_id)}
        elif args.command == 'import-receipt':
            result = runner.import_receipt(read_json(args.file))
        elif args.command == 'export-receipt':
            result = runner.store.prior_receipt(args.run_id, args.principal)
            if not result:
                raise ValueError('No locally recorded receipt; use review --record-receipt')
            write_new(args.output, result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
