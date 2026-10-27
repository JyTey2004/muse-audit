"""Executable acceptance against original approved contracts and separate provider reads."""
import json
from collections import Counter
from .contracts import validate
from .identity import implementation
from .provider import Provider
from .store import Store, now
from ..io import digest


def context(store, provider, run_id, owner):
    run = store.owned_run(run_id, owner)
    contract = store.contract(run['contract_id'], owner)
    approval = store.approval(run['contract_id'], owner)
    original = json.loads(contract['body'])
    validate(original)
    events = store.events(run_id, owner)
    source, result = provider.read_pair(run_id, owner)
    def pin(row):
        return None if row is None else {k: row[k] for k in ('seq','run_id','kind','label','available','hash')}
    impl = implementation()
    bindings = {'run_id': run_id, 'contract_id': run['contract_id'], 'contract': contract['hash'], 'approval': approval['hash'],
                'events': digest(events), 'execution_events': digest([e for e in events if not e['kind'].startswith('repair.')]),
                'source': pin(source), 'result': pin(result), 'implementation': digest(impl),
                'configuration': digest({'principal': owner, 'provider': 'synthetic-sqlite-v1', 'scope': 'explicit local store only'})}
    return original, events, source, result, bindings, impl


def plan_context(bindings):
    return {k: v for k, v in bindings.items() if k != 'events'}


def review_run(root, owner, run_id, claimed_outcome):
    if not isinstance(claimed_outcome, str) or len(claimed_outcome) > 10000:
        raise ValueError('Claim must be bounded text; never proof')
    store, provider = Store(root, readonly=True), Provider(root, readonly=True)
    original, events, source, result, bindings, impl = context(store, provider, run_id, owner)
    started_events = [e for e in events if e['kind'] == 'run.started' and e['origin'] == 'collector_observed']
    finished_events = [e for e in events if e['kind'] == 'run.finished' and e['origin'] == 'collector_observed']
    started, finished = bool(started_events), bool(finished_events)
    pending = started and not finished
    coverage = []
    checks = []
    source_ok = bool(source and source['available'] and source['body'] == original['source'])
    action_events = [e for e in events if e['kind'] == 'tool.request' and e['origin'] == 'collector_observed']
    terminal_events = [e for e in events if e['kind'] in ('tool.response','tool.error') and e['origin'] == 'collector_observed']
    request_ids = [e['body'].get('request_id') for e in action_events]
    observed_requests = started and finished and bool(action_events) and len(set(request_ids)) == len(request_ids) and all(isinstance(i, str) for i in request_ids)
    for request in action_events:
        replies = [e for e in terminal_events if e['body'].get('request_id') == request['body'].get('request_id')]
        if not finished or len(replies) != 1 or not (started_events[0]['seq'] < request['seq'] < replies[0]['seq'] < finished_events[-1]['seq']) or replies[0]['kind'] != 'tool.response' or replies[0]['body'].get('success') is not True:
            observed_requests = False
    if any(e['body'].get('request_id') not in request_ids for e in terminal_events):
        observed_requests = False
    repair_requests = [e for e in events if e['kind'] == 'repair.request' and e['origin'] == 'collector_observed']
    repair_completions = [e for e in events if e['kind'] == 'repair.completed' and e['origin'] == 'synthetic_provider_confirmed']
    for request in repair_requests:
        key = request['body'].get('plan_hash')
        with store.connection() as db:
            approval = db.execute('SELECT * FROM repair_approvals WHERE plan_hash=? AND run_id=?', (key, run_id)).fetchone()
            applied = db.execute('SELECT * FROM repair_results WHERE plan_hash=? AND run_id=?', (key, run_id)).fetchone()
        completion = [e for e in repair_completions if e['body'].get('plan_hash') == key and e['seq'] > request['seq']]
        if not approval or digest(json.loads(approval['body'])) != approval['hash'] or not applied or len(completion) != 1 or completion[0]['body'].get('revision') != applied['revision'] or request['body'].get('approved_digest') != key:
            observed_requests = False
    if result and result['operation_key'].startswith('repair:'):
        key = result['operation_key'][len('repair:'):]
        if not any(e['body'].get('plan_hash') == key for e in repair_requests) or not any(e['body'].get('plan_hash') == key and e['body'].get('revision') == result['seq'] for e in repair_completions):
            observed_requests = False
    all_action_events = action_events + repair_requests
    implementation_current = not impl.get('source_changed_since_process_start', False)
    for r in original['requirements']:
        status, explanation, executed = 'UNKNOWN', 'Unsupported requirement; no executed adequate checker.', False
        actual = None
        if r['checker'] == 'privacy':
            explanation = 'Privacy remains required UNKNOWN: synthetic service has no authentication/access-control verifier.'
        elif r['checker'] not in ('edited_total', 'add_total', 'max_total', 'allowed_actions'):
            explanation = 'Unsupported semantic/generated checker remains UNKNOWN in every lifecycle state.'
        elif not implementation_current:
            explanation = 'Implementation bytes changed after process import. Restart required; loaded checker cannot attest to new code.'
        elif pending:
            status, explanation = 'PENDING', 'Instrumented operation started but has not reached observable completion.'
        elif not source or not source['available']:
            explanation = 'Selected source read-back unavailable.'
        elif not source_ok:
            status, explanation, executed = 'FAIL', 'Current source differs from the ORIGINAL approved source.', True
        elif not observed_requests or not finished:
            explanation = 'Necessary instrumented execution evidence is missing; claims cannot replace it.'
        elif r['checker'] == 'allowed_actions':
            actual = [e['body'].get('action') for e in all_action_events]
            status = 'PASS' if all(x in original['allowed_actions'] for x in actual) else 'FAIL'
            explanation, executed = 'Compared captured requests to original allowed-action list.', True
        elif not result or not result['available']:
            explanation = 'Provider result read-back unavailable; acknowledgement does not establish fulfillment.'
        elif r['checker'] in ('edited_total', 'add_total', 'max_total'):
            executed = True
            body = result['body']
            try:
                if r['checker'] == 'add_total':
                    actual = body['add_probe']['total_cents']
                    values = body['add_probe']['items'].values()
                else:
                    actual = body['total_cents']
                    values = body['items'].values()
                values = list(values)
                if type(actual) is not int or any(type(v) is not int for v in values):
                    raise ValueError('State amounts are not integer cents')
                expected_items = {'lunch': original['source']['lunch'], 'travel': original['source']['travel']} if r['checker'] == 'add_total' else {'lunch': original['source']['edited_lunch']}
                observed_items = body['add_probe']['items'] if r['checker'] == 'add_total' else body['items']
                coherent = sum(values) == actual and observed_items == expected_items
                match = actual <= r['expected'] if r['checker'] == 'max_total' else actual == r['expected']
                status = 'PASS' if coherent and match else 'FAIL'
                explanation = f'Independent read and integer-cent assertion: expected {r["expected"]}, observed {actual}; item-sum agreement={coherent}.'
            except (KeyError, TypeError, ValueError, AttributeError):
                status, explanation = 'UNKNOWN', 'Malformed/incomplete provider result; checker abstained.'
        if status in ('UNKNOWN', 'PENDING'):
            coverage.append({'requirement': r['id'], 'gap': explanation})
        checks.append({'requirement_id': r['id'], 'original_condition': r, 'status': status, 'expected': r['expected'], 'observed': actual,
                       'explanation': explanation, 'origin': 'independently_derived',
                       'checker': {'id': r['checker'], 'executed': executed, 'implementation_digest': bindings['implementation'], 'scope': 'original explicit synthetic expense condition only'},
                       'evidence_refs': {'events': [e['seq'] for e in all_action_events], 'source': bindings['source'], 'result': bindings['result']}})
    prior = store.prior_receipt(run_id, owner)
    freshness = 'STALE' if prior and prior['bindings'] != bindings else 'FRESH'
    required = [c for c in checks if c['original_condition']['required']]
    complete = bool(required) and all(c['status'] == 'PASS' and c['checker']['executed'] for c in required)
    receipt = {'schema': 1, 'run_id': run_id, 'reviewed_at': now(), 'claim': {'origin': 'agent_supplied', 'text': claimed_outcome, 'authoritative': False},
               'original_contract': original, 'bindings': bindings, 'implementation': impl,
               'freshness': {'prior_assurance': freshness, 'observed_now_only': True, 'prior_digest': digest(prior) if prior else None},
               'conditions': checks, 'counts': dict(Counter(c['status'] for c in checks)), 'coverage_gaps': coverage,
               'current_decision': 'SELECTED_CHECKS_PASS' if complete else 'UNRESOLVED', 'completion_assured': complete,
               'observations': {'observed_at': now(), 'origin': 'synthetic_provider_confirmed', 'source': source, 'result': result},
               'repair_guidance': 'Review an exact copy-only repair plan; keep original requirements/source/privacy. Rerun every condition.',
               'restart_required': not implementation_current, 'scope': 'Bounded synthetic expense tracker. Advisory outside an enforcing harness; no hidden host/Muse calls observed.', 'synthetic': True, 'model_calls': 0}
    receipt['digest'] = digest(receipt)
    return receipt


def inspect_import(receipt):
    if not isinstance(receipt, dict) or receipt.get('schema') != 1 or 'digest' not in receipt:
        raise ValueError('Malformed imported receipt')
    body = {k: v for k, v in receipt.items() if k != 'digest'}
    if digest(body) != receipt['digest']:
        raise ValueError('Imported receipt digest changed')
    return {'origin': 'imported_agent_assertions', 'origin_verified': False, 'completion_assured': False,
            'freshness': 'STALE' if receipt.get('bindings', {}).get('implementation') != digest(implementation()) else 'UNVERIFIED',
            'note': 'No import may create a contract, observed event, provider state or observed PASS. Execute review_run against the authorized local store.'}
