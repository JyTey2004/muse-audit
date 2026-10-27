"""Reproducible, disclosed synthetic task; results computed by actual acceptance checks."""
import argparse
import json
from pathlib import Path
from copy import deepcopy
from .runner import Runner
from .contracts import expense_contract, create_contract, approve_contract
from .identity import implementation


def demo(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    r = Runner(output / 'store')
    c = create_contract(r.store, r.owner, expense_contract())
    approve_contract(r.store, r.owner, c['contract_id'], c['contract_hash'], reviewed=True, actor='SCRIPTED SYNTHETIC DEMO APPROVAL, not human acceptance')
    run = r.start(c['contract_id'])
    first = r.review(run)
    plan = r.prepare(run)
    r.apply(plan, plan['digest'], reviewed=True)
    repaired = r.review(run)
    state = r.provider.read(run, r.owner, 'result')
    changed = deepcopy(state['body']);changed['total_cents'] += 1
    r.mutate(run, 'result', changed)
    stale = r.review(run)
    r.mutate(run, 'result', available=False)
    missing = r.review(run)
    restarted = Runner(output / 'store')
    replay = restarted.review(run)
    imported = restarted.import_receipt(repaired)
    reset_run = restarted.reset(run)
    reset = restarted.review(reset_run)
    new = create_contract(r.store, r.owner, expense_contract(1400))
    approve_contract(r.store, r.owner, new['contract_id'], new['contract_hash'], reviewed=True, actor='SCRIPTED NEW CONTRACT APPROVAL')
    new_run = r.start(new['contract_id'])
    new_plan = r.prepare(new_run);r.apply(new_plan, new_plan['digest'], reviewed=True)
    constrained = r.review(new_run)
    pending = r.review(r.start(c['contract_id'], pending=True))
    artifacts = {'initial': first, 'repair-plan': plan, 'repaired': repaired, 'changed-state': stale, 'missing': missing, 'restart': replay, 'import': imported, 'reset': reset, 'new-supported-cap': constrained, 'pending': pending, 'implementation-manifest': implementation()}
    for name, obj in artifacts.items():
        (output / f'{name}.json').write_text(json.dumps(obj, indent=2), encoding='utf8')
    summary = {'synthetic': True, 'review': 'scripted approvals, not human acceptance', 'run_id': run,
               'initial': first['counts'], 'repaired': repaired['counts'], 'changed_state': {'prior': stale['freshness'], 'current': stale['counts']},
               'missing': missing['counts'], 'restart_same_conditions': replay['conditions'] == missing['conditions'],
               'import_assured': imported['completion_assured'], 'new_cap': 1400, 'new_cap_counts': constrained['counts'],
               'pending': pending['counts'], 'model_calls': 0, 'muse_tested': False, 'advisory_only': True}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf8')
    return summary


def main():
    p = argparse.ArgumentParser();p.add_argument('--output', type=Path, required=True)
    args = p.parse_args();print(json.dumps(demo(args.output), indent=2))


if __name__ == '__main__':
    main()
