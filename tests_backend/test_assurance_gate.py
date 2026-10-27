"""Negative acceptance cases for the existing controlled synthetic runner."""
from copy import deepcopy
import json
import tempfile
import unittest
from unittest.mock import patch

from muse_audit.io import canonical, digest
from muse_audit.task_backend.contracts import approve_contract, create_contract, expense_contract
from muse_audit.task_backend.provider import execute_tracker
from muse_audit.task_backend.runner import Runner


class AssuranceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runner = Runner(self.temp.name, 'supervised-test')
        self.contract = expense_contract()
        self.contract_id = self.approve(self.contract)

    def approve(self, contract):
        c = create_contract(self.runner.store, self.runner.owner, contract)
        approve_contract(self.runner.store, self.runner.owner, c['contract_id'], c['contract_hash'], reviewed=True)
        return c['contract_id']

    def correct_state(self, run):
        self.runner.mutate(run, 'result', execute_tracker(self.contract['source'], True))

    def assert_withheld(self, receipt):
        self.assertFalse(receipt['completion_assured'])
        self.assertEqual(receipt['current_decision'], 'UNRESOLVED')
        self.assertFalse(any(c['status'] == 'PASS' for c in receipt['conditions']))
        self.assertEqual(receipt['execution_evidence']['status'], 'INCOMPLETE')
        self.assertTrue(receipt['execution_evidence']['gap'])

    def captured_run(self, transform):
        append = self.runner.store._append_event
        def capture(db, run_id, kind, origin, body):
            for new_kind, new_origin, new_body in transform(kind, origin, deepcopy(body)):
                append(db, run_id, new_kind, new_origin, new_body)
        with patch.object(self.runner.store, '_append_event', side_effect=capture):
            run = self.runner.start(self.contract_id)
        self.correct_state(run)
        return run

    def test_compound_recipe_requires_add_edit_and_read_permission_before_effects(self):
        for action in ('synthetic.add', 'synthetic.edit', 'synthetic.read'):
            with self.subTest(action=action):
                contract = expense_contract()
                contract['allowed_actions'].remove(action)
                key = self.approve(contract)
                with self.assertRaisesRegex(ValueError, 'requires approved'):
                    self.runner.start(key)
        with self.runner.store.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 0)
        with self.runner.provider.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM versions').fetchone()[0], 0)

    def test_positive_scope_lists_compound_actions_but_privacy_prevents_completion(self):
        run = self.runner.start(self.contract_id)
        self.correct_state(run)
        receipt = self.runner.review(run)
        check = next(c for c in receipt['conditions'] if c['requirement_id'] == 'allowed-actions')
        self.assertEqual(set(check['observed']), {'synthetic.add', 'synthetic.edit', 'synthetic.read'})
        self.assertEqual(receipt['execution_evidence']['status'], 'COMPLETE')
        self.assertEqual(receipt['counts'], {'PASS': 4, 'UNKNOWN': 1})
        self.assertFalse(receipt['completion_assured'])

    def test_truncated_request_fields_and_typed_operation_changes_cannot_pass(self):
        mutations = [lambda b: b.pop('operations'), lambda b: b.pop('source_revision'),
                     lambda b: b.update(request_id=''),
                     lambda b: b['operations'][0].__setitem__(2, 1000.0)]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                def transform(kind, origin, body):
                    if kind == 'tool.request':
                        mutate(body)
                    return [(kind, origin, body)]
                receipt = self.runner.review(self.captured_run(transform), 'Everything passed')
                self.assert_withheld(receipt)

    def test_missing_approval_or_provider_readback_record_cannot_pass(self):
        for omitted in ('contract.approval', 'source.readback', 'result.readback'):
            with self.subTest(omitted=omitted):
                run = self.captured_run(lambda kind, origin, body: [] if kind == omitted else [(kind, origin, body)])
                self.assert_withheld(self.runner.review(run))

    def test_duplicate_run_markers_cannot_hide_an_ambiguous_lifecycle(self):
        for marker in ('run.started', 'run.finished'):
            with self.subTest(marker=marker):
                run = self.runner.start(self.contract_id)
                self.correct_state(run)
                self.runner.store.event(run, self.runner.owner, marker, 'collector_observed', {'synthetic': True})
                self.assert_withheld(self.runner.review(run))

    def test_truncated_completion_after_terminal_response_is_unknown_not_pending(self):
        run = self.captured_run(lambda kind, origin, body: [] if kind == 'run.finished' else [(kind, origin, body)])
        receipt = self.runner.review(run)
        self.assert_withheld(receipt)
        self.assertNotIn('PENDING', receipt['counts'])

    def test_known_open_request_remains_pending_and_never_executed_pass(self):
        run = self.runner.start(self.contract_id, pending=True)
        receipt = self.runner.review(run)
        self.assertEqual(receipt['execution_evidence']['status'], 'PENDING')
        self.assertEqual(receipt['counts'], {'PENDING': 4, 'UNKNOWN': 1})
        self.assertFalse(any(c['checker']['executed'] for c in receipt['conditions']))
        self.assertFalse(receipt['completion_assured'])

    def test_duplicate_response_cannot_count_as_one_successful_operation(self):
        run = self.runner.start(self.contract_id)
        self.correct_state(run)
        response = next(e for e in self.runner.store.events(run, self.runner.owner) if e['kind'] == 'tool.response')
        self.runner.store.event(run, self.runner.owner, 'tool.response', 'collector_observed', response['body'])
        self.assert_withheld(self.runner.review(run))

    def test_reordered_readback_and_response_with_valid_hash_chain_cannot_pass(self):
        held = []
        def transform(kind, origin, body):
            if kind == 'tool.response':
                held.append((kind, origin, body))
                return []
            if kind == 'result.readback':
                return [(kind, origin, body), *held]
            return [(kind, origin, body)]
        self.assert_withheld(self.runner.review(self.captured_run(transform)))

    def test_wrong_run_readback_cannot_corroborate_the_current_run(self):
        for wrong in ('source.readback', 'result.readback'):
            with self.subTest(wrong=wrong):
                def transform(kind, origin, body):
                    if kind == wrong:
                        body['run_id'] = 'f' * 32
                    return [(kind, origin, body)]
                self.assert_withheld(self.runner.review(self.captured_run(transform)))

    def test_orphan_repair_completion_cannot_be_ignored(self):
        run = self.runner.start(self.contract_id)
        self.correct_state(run)
        self.runner.store.event(run, self.runner.owner, 'repair.completed', 'synthetic_provider_confirmed',
                                {'plan_hash': 'unapproved', 'revision': 999})
        self.assert_withheld(self.runner.review(run))

    def test_repair_records_on_an_open_request_are_unknown_not_merely_pending(self):
        run = self.runner.start(self.contract_id, pending=True)
        self.runner.store.event(run, self.runner.owner, 'repair.completed', 'synthetic_provider_confirmed',
                                {'plan_hash': 'not-approved', 'revision': 999})
        receipt = self.runner.review(run)
        self.assert_withheld(receipt)
        self.assertNotIn('PENDING', receipt['counts'])

    def test_self_consistent_but_denied_repair_approval_cannot_support_pass(self):
        run = self.runner.start(self.contract_id)
        plan = self.runner.prepare(run)
        self.runner.apply(plan, plan['digest'], reviewed=True)
        # Deliberate temporary-store corruption beyond the ordinary append-only API.
        # A new hash is not evidence that a denied approval authorized the write.
        with self.runner.store.connection() as db:
            row = db.execute('SELECT body FROM repair_approvals WHERE plan_hash=?', (plan['digest'],)).fetchone()
            body = json.loads(row['body'])
            body['decision'] = 'denied'
            db.execute('DROP TRIGGER immutable_repair_approvals_UPDATE')
            db.execute('UPDATE repair_approvals SET body=?,hash=? WHERE plan_hash=?',
                       (canonical(body), digest(body), plan['digest']))
        self.assert_withheld(self.runner.review(run))

    def test_same_numeric_value_with_changed_json_type_is_changed_source(self):
        run = self.runner.start(self.contract_id)
        self.correct_state(run)
        before = self.runner.review(run)
        source = deepcopy(self.contract['source'])
        source['lunch'] = 1000.0
        self.runner.mutate(run, 'source', source)
        after = self.runner.review(run, before['claim']['text'])
        self.assertEqual(after['freshness']['prior_assurance'], 'STALE')
        self.assertFalse(any(c['status'] == 'PASS' for c in after['conditions']))
        self.assertFalse(after['completion_assured'])
        self.assertEqual(after['original_contract'], before['original_contract'])


if __name__ == '__main__':
    unittest.main()
