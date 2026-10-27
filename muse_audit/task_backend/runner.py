"""Controlled synthetic collector and approval-bound, idempotent copy repair. No network."""
import json
from copy import deepcopy
from .contracts import validate
from .provider import Provider, execute_tracker
from .review import context, plan_context, review_run, inspect_import
from .store import Store, identifier, now
from ..io import canonical, digest


class Runner:
    def __init__(self, root, owner='local-demo'):
        self.store = Store(root)
        self.provider = Provider(root)
        self.owner = owner

    def start(self, contract_id, pending=False, fail=False):
        contract = self.store.contract(contract_id, self.owner)
        approved = self.store.approval(contract_id, self.owner)
        original = json.loads(contract['body'])
        validate(original)
        if 'synthetic.edit' not in original['allowed_actions']:
            raise ValueError('Synthetic edit not allowed by original contract')
        run_id = identifier()
        with self.store.connection() as db:
            db.execute('INSERT INTO runs VALUES(?,?,?,?)', (run_id, self.owner, contract_id, now()))
        self.store.event(run_id, self.owner, 'contract.approval', 'collector_observed', json.loads(approved['body']))
        self.store.event(run_id, self.owner, 'run.started', 'collector_observed', {'synthetic': True, 'collector': 'controlled-runner-v1'})
        source = self.provider.write(run_id, self.owner, 'source', original['source'])
        self.store.event(run_id, self.owner, 'source.readback', 'synthetic_provider_confirmed', source)
        request_id = identifier()
        self.store.event(run_id, self.owner, 'tool.request', 'collector_observed', {'request_id': request_id, 'action': 'synthetic.edit', 'operations': [['add', 'lunch', original['source']['lunch']], ['edit', 'lunch', original['source']['edited_lunch']], ['probe_add', 'travel', original['source']['travel']]], 'source_revision': source['seq']})
        if pending:
            return run_id
        try:
            if fail:
                raise RuntimeError('Disclosed synthetic provider failure')
            body = execute_tracker(original['source'])
            result = self.provider.write(run_id, self.owner, 'result', body)
            # Acknowledgement is deliberately not a checker verdict.
            self.store.event(run_id, self.owner, 'tool.response', 'collector_observed', {'request_id': request_id, 'success': True, 'provider_revision': result['seq']})
            self.store.event(run_id, self.owner, 'result.readback', 'synthetic_provider_confirmed', self.provider.read(run_id, self.owner, 'result'))
            self.store.event(run_id, self.owner, 'agent.claim', 'agent_supplied', {'text': 'Done. Your expense tracker is correct.'})
        except Exception as error:
            self.store.event(run_id, self.owner, 'tool.error', 'collector_observed', {'request_id': request_id, 'type': type(error).__name__, 'message': str(error)})
        self.store.event(run_id, self.owner, 'run.finished', 'collector_observed', {'synthetic': True})
        return run_id

    def review(self, run_id, claim='Done. Your expense tracker is correct.', save=True):
        receipt = review_run(self.store.root, self.owner, run_id, claim)
        if save:
            self.store.save_receipt(receipt, self.owner)
        return receipt

    def mutate(self, run_id, kind, body=None, available=True):
        self.store.owned_run(run_id, self.owner)
        old = self.provider.read(run_id, self.owner, kind)
        if not old:
            raise ValueError('No provider version to copy')
        return self.provider.write(run_id, self.owner, kind, body if body is not None else old['body'], label=old['label'], available=available, parent=old['seq'])

    def prepare(self, run_id):
        receipt = self.review(run_id, save=False)
        original, events, source, result, bindings, impl = context(self.store, self.provider, run_id, self.owner)
        if not result or not result['available'] or not source or not source['available'] or source['body'] != original['source']:
            raise ValueError('Repair needs adequate current approved source/result evidence')
        if not any(c['status'] == 'FAIL' for c in receipt['conditions']) or result['body'].get('implementation') != 'append-edit':
            raise ValueError('No supported current seeded repair')
        if 'synthetic.repair_copy' not in original['allowed_actions']:
            raise ValueError('Repair forbidden by original contract')
        after = deepcopy(result['body'])
        after['total_cents'] = sum(after['items'].values())
        after['implementation'] = 'replace-edit'
        plan = {'schema': 1, 'run_id': run_id, 'owner': self.owner, 'context': plan_context(bindings), 'before': result['body'], 'after': after,
                'before_revision': result['seq'], 'source_hash': source['hash'], 'contract_hash': bindings['contract'],
                'effect': 'Replace prior expense amount instead of adding it again; new result copy. Source, requirements, cap and add-probe unchanged.'}
        plan['digest'] = digest(plan)
        return plan

    def apply(self, plan, approved_digest, reviewed=False, interrupt_after_write=False):
        if reviewed is not True or not isinstance(plan, dict) or approved_digest != plan.get('digest'):
            if isinstance(plan, dict) and plan.get('owner') == self.owner:
                self.store.owned_run(plan.get('run_id'), self.owner)
                self.store.event(plan['run_id'], self.owner, 'repair.denied', 'collector_observed', {'plan_hash': plan.get('digest'), 'decision': 'denied', 'reason': 'Exact reviewed approval absent'})
            raise ValueError('Explicit approval of this exact plan is required')
        body = {k: v for k, v in plan.items() if k != 'digest'}
        if digest(body) != plan['digest'] or plan.get('owner') != self.owner:
            if plan.get('owner') == self.owner:
                self.store.owned_run(plan.get('run_id'), self.owner)
                self.store.event(plan['run_id'], self.owner, 'repair.denied', 'collector_observed', {'plan_hash': plan['digest'], 'decision': 'denied', 'reason': 'Modified plan'})
            raise ValueError('Modified or unauthorized repair plan')
        run_id = plan['run_id']
        self.store.owned_run(run_id, self.owner)
        op = self.provider.operation('repair:' + plan['digest'], run_id, self.owner)
        if op:
            # Crash recovery/retry: never apply a second provider effect.
            with self.store.connection() as db:
                approval = db.execute('SELECT * FROM repair_approvals WHERE plan_hash=? AND run_id=?', (plan['digest'], run_id)).fetchone()
            original, events, source, latest, bindings, impl = context(self.store, self.provider, run_id, self.owner)
            if not approval or digest(json.loads(approval['body'])) != approval['hash'] or json.loads(approval['body'])['plan_hash'] != plan['digest']:
                raise ValueError('No recorded exact repair approval for recovery')
            if latest['seq'] != op['seq'] or source['hash'] != plan['source_hash'] or bindings['implementation'] != plan['context']['implementation'] or bindings['contract'] != plan['contract_hash'] or op['body'] != plan['after'] or op['parent'] != plan['before_revision']:
                raise ValueError('Stale repair recovery state')
            self._finish_repair(plan, op)
            return {'revision': op['seq'], 'idempotent_retry': True, 'original_preserved': True}
        try:
            expected = self.prepare(run_id)
        except ValueError as error:
            self.store.event(run_id, self.owner, 'repair.denied', 'collector_observed', {'plan_hash': plan['digest'], 'decision': 'denied', 'reason': str(error)})
            raise
        if canonical(expected) != canonical(plan):
            self.store.event(run_id, self.owner, 'repair.denied', 'collector_observed', {'plan_hash': plan['digest'], 'decision': 'denied', 'reason': 'Stale plan'})
            raise ValueError('Stale or modified repair plan')
        approval = {'plan_hash': plan['digest'], 'run_id': run_id, 'owner': self.owner, 'decision': 'approved', 'observed_at': now(), 'identity_authenticated': False}
        with self.store.connection() as db:
            old = db.execute('SELECT * FROM repair_approvals WHERE plan_hash=?', (plan['digest'],)).fetchone()
            if not old:
                db.execute('INSERT INTO repair_approvals VALUES(?,?,?,?)', (plan['digest'], run_id, canonical(approval), digest(approval)))
        self.store.event(run_id, self.owner, 'repair.request', 'collector_observed', {'plan_hash': plan['digest'], 'action': 'synthetic.repair_copy', 'approved_digest': approved_digest})
        try:
            result = self.provider.write(run_id, self.owner, 'result', plan['after'], label='repaired-copy', operation_key='repair:' + plan['digest'], parent=plan['before_revision'], expected_source_hash=plan['source_hash'])
        except Exception as error:
            self.store.event(run_id, self.owner, 'repair.error', 'collector_observed', {'plan_hash': plan['digest'], 'type': type(error).__name__, 'message': str(error), 'effect_confirmed': False})
            raise
        if interrupt_after_write:
            raise RuntimeError('Disclosed interruption after provider write; retry exact approved plan')
        self._finish_repair(plan, result)
        return {'revision': result['seq'], 'idempotent_retry': False, 'original_preserved': True}

    def _finish_repair(self, plan, result):
        # Provider and collector have separate databases. Recovery reconciles the provider
        # operation key, then records result + completion atomically in the collector DB.
        with self.store.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM repair_results WHERE plan_hash=?', (plan['digest'],)).fetchone()
            if old and (old['run_id'] != plan['run_id'] or old['revision'] != result['seq']):
                raise ValueError('Repair completion binding mismatch')
            if not old:
                db.execute('INSERT INTO repair_results VALUES(?,?,?)', (plan['digest'], plan['run_id'], result['seq']))
            completed = [json.loads(r['body']) for r in db.execute('SELECT body FROM events WHERE run_id=? AND kind=? AND origin=?', (plan['run_id'], 'repair.completed', 'synthetic_provider_confirmed'))]
            if not any(e.get('plan_hash') == plan['digest'] for e in completed):
                self.store._append_event(db, plan['run_id'], 'repair.completed', 'synthetic_provider_confirmed', {'plan_hash': plan['digest'], 'revision': result['seq'], 'copy_of': plan['before_revision']})

    def reset(self, run_id):
        run = self.store.owned_run(run_id, self.owner)
        return self.start(run['contract_id'])

    def import_receipt(self, receipt):
        withheld = inspect_import(receipt)
        with self.store.connection() as db:
            db.execute('INSERT INTO imports(owner,body,hash) VALUES(?,?,?)', (self.owner, canonical(receipt), digest(receipt)))
        return withheld
