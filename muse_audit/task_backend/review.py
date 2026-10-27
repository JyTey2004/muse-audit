"""Executable acceptance against original approved contracts and separate provider reads."""
import json
from collections import Counter
from .contracts import validate
from .identity import implementation
from .provider import Provider
from .store import Store, now
from ..io import canonical, digest


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


def execution_coverage(events, original, bindings):
    """Validate this controlled runner's complete recipe, not arbitrary host history."""
    def selected(kind, origin='collector_observed'):
        return [e for e in events if e['kind'] == kind and e['origin'] == origin]

    approvals, starts, finishes = selected('contract.approval'), selected('run.started'), selected('run.finished')
    requests = selected('tool.request')
    terminals = selected('tool.response') + selected('tool.error')
    source_reads = selected('source.readback', 'synthetic_provider_confirmed')
    result_reads = selected('result.readback', 'synthetic_provider_confirmed')
    gap = 'Incomplete or ambiguous instrumented evidence; no adequate executed check is established.'
    if len(approvals) != 1 or len(starts) != 1 or len(finishes) > 1 or len(requests) != 1:
        return 'INCOMPLETE', [], gap
    approval, start, request = approvals[0], starts[0], requests[0]
    body = request['body']
    if not isinstance(body, dict) or not isinstance(approval['body'], dict):
        return 'INCOMPLETE', [], gap
    expected_operations = [['add', 'lunch', original['source']['lunch']],
                           ['edit', 'lunch', original['source']['edited_lunch']],
                           ['probe_add', 'travel', original['source']['travel']]]
    if (digest(approval['body']) != bindings['approval'] or
            not (approval['seq'] < start['seq'] < request['seq']) or
            not isinstance(body.get('request_id'), str) or not body['request_id'] or
            body.get('action') != 'synthetic.edit' or canonical(body.get('operations')) != canonical(expected_operations) or
            type(body.get('source_revision')) is not int or body['source_revision'] < 1):
        return 'INCOMPLETE', [], gap
    if len(source_reads) != 1 or not isinstance(source_reads[0]['body'], dict):
        return 'INCOMPLETE', [], gap
    source = source_reads[0]
    if (not (start['seq'] < source['seq'] < request['seq']) or
            source['body'].get('run_id') != bindings['run_id'] or source['body'].get('kind') != 'source' or
            source['body'].get('seq') != body['source_revision'] or canonical(source['body'].get('body')) != canonical(original['source'])):
        return 'INCOMPLETE', [], gap
    actions = ['synthetic.read', 'synthetic.add', 'synthetic.edit', 'synthetic.add']
    if not finishes:
        if not terminals and not result_reads:
            return 'PENDING', actions, 'Captured request has no terminal response or completion yet.'
        return 'INCOMPLETE', [], 'Completion record is absent after a terminal response; fulfillment cannot be established.'
    if len(terminals) != 1 or len(result_reads) != 1:
        return 'INCOMPLETE', [], gap
    reply, readback, finish = terminals[0], result_reads[0], finishes[0]
    if not isinstance(reply['body'], dict) or not isinstance(readback['body'], dict):
        return 'INCOMPLETE', [], gap
    if (reply['kind'] != 'tool.response' or reply['body'].get('request_id') != body['request_id'] or
            reply['body'].get('success') is not True or type(reply['body'].get('provider_revision')) is not int or
            not (request['seq'] < reply['seq'] < readback['seq'] < finish['seq']) or
            readback['body'].get('run_id') != bindings['run_id'] or readback['body'].get('kind') != 'result' or
            readback['body'].get('seq') != reply['body']['provider_revision']):
        return 'INCOMPLETE', [], gap
    return 'COMPLETE', actions + ['synthetic.read'], ''


def review_run(root, owner, run_id, claimed_outcome):
    if not isinstance(claimed_outcome, str) or len(claimed_outcome) > 10000:
        raise ValueError('Claim must be bounded text; never proof')
    store, provider = Store(root, readonly=True), Provider(root, readonly=True)
    original, events, source, result, bindings, impl = context(store, provider, run_id, owner)
    execution_status, captured_actions, execution_gap = execution_coverage(events, original, bindings)
    pending = execution_status == 'PENDING'
    observed_requests = execution_status == 'COMPLETE'
    coverage = []
    checks = []
    source_ok = bool(source and source['available'] and canonical(source['body']) == canonical(original['source']))
    action_events = [e for e in events if e['kind'] == 'tool.request' and e['origin'] == 'collector_observed']
    repair_requests = [e for e in events if e['kind'] == 'repair.request' and e['origin'] == 'collector_observed']
    repair_completions = [e for e in events if e['kind'] == 'repair.completed' and e['origin'] == 'synthetic_provider_confirmed']
    for request in repair_requests:
        key = request['body'].get('plan_hash')
        with store.connection() as db:
            approval = db.execute('SELECT * FROM repair_approvals WHERE plan_hash=? AND run_id=?', (key, run_id)).fetchone()
            applied = db.execute('SELECT * FROM repair_results WHERE plan_hash=? AND run_id=?', (key, run_id)).fetchone()
        completion = [e for e in repair_completions if e['body'].get('plan_hash') == key and e['seq'] > request['seq']]
        approval_body = json.loads(approval['body']) if approval else None
        valid_approval = (isinstance(approval_body, dict) and digest(approval_body) == approval['hash'] and
                          approval_body.get('decision') == 'approved' and approval_body.get('owner') == owner and
                          approval_body.get('run_id') == run_id and approval_body.get('plan_hash') == key)
        finished = [e for e in events if e['kind'] == 'run.finished' and e['origin'] == 'collector_observed']
        if (not valid_approval or not applied or len(completion) != 1 or len(finished) != 1 or
                request['seq'] <= finished[0]['seq'] or
                completion[0]['body'].get('revision') != applied['revision'] or request['body'].get('approved_digest') != key):
            observed_requests = False
    repair_keys = [e['body'].get('plan_hash') for e in repair_requests]
    if len(set(repair_keys)) != len(repair_keys) or any(e['body'].get('plan_hash') not in repair_keys for e in repair_completions):
        observed_requests = False
    if result and result['operation_key'].startswith('repair:'):
        key = result['operation_key'][len('repair:'):]
        if not any(e['body'].get('plan_hash') == key for e in repair_requests) or not any(e['body'].get('plan_hash') == key and e['body'].get('revision') == result['seq'] for e in repair_completions):
            observed_requests = False
    if pending and (repair_requests or repair_completions):
        pending = False
        execution_status = 'INCOMPLETE'
        execution_gap = 'Repair evidence precedes original task completion; the recorded lifecycle is inconsistent.'
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
        elif not observed_requests:
            explanation = execution_gap or 'Necessary instrumented repair evidence is missing or inconsistent; claims cannot replace it.'
        elif r['checker'] == 'allowed_actions':
            actual = captured_actions + [e['body'].get('action') for e in repair_requests]
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
               'execution_evidence': {'status': execution_status if observed_requests or pending else 'INCOMPLETE', 'gap': execution_gap if observed_requests or pending else execution_gap or 'Repair evidence is incomplete or inconsistent.', 'scope': 'Controlled synthetic runner recipe only; no coverage of uninstrumented host calls.'},
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
