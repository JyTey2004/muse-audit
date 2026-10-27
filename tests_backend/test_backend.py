import json
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch
from pathlib import Path
from muse_audit.io import digest
from muse_audit.task_backend.store import Store
from muse_audit.task_backend.provider import Provider, execute_tracker
from muse_audit.task_backend.runner import Runner
from muse_audit.task_backend.contracts import create_contract, approve_contract, expense_contract
from muse_audit.task_backend.review import review_run


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runner = Runner(self.temp.name, 'alice')
        self.contract = create_contract(self.runner.store, 'alice', expense_contract())
        approve_contract(self.runner.store, 'alice', self.contract['contract_id'], self.contract['contract_hash'], reviewed=True, actor='scripted test review')
        self.run_id = self.runner.start(self.contract['contract_id'])

    def condition(self, receipt, key):
        return next(c for c in receipt['conditions'] if c['requirement_id'] == key)

    def repaired(self):
        plan = self.runner.prepare(self.run_id)
        self.runner.apply(plan, plan['digest'], reviewed=True)
        return self.runner.review(self.run_id)

    def test_identical_story_altered_current_state_changes_executed_verdict(self):
        before = self.runner.review(self.run_id, 'Done')
        self.assertEqual(self.condition(before, 'expense-edit')['status'], 'FAIL')
        self.assertEqual(before['counts'], {'FAIL': 2, 'PASS': 2, 'UNKNOWN': 1})
        self.runner.mutate(self.run_id, 'result', execute_tracker(expense_contract()['source'], True))
        after = self.runner.review(self.run_id, 'Done')
        self.assertEqual(after['claim'], before['claim'])
        self.assertEqual(self.condition(after, 'expense-edit')['status'], 'PASS')
        self.assertEqual(after['freshness']['prior_assurance'], 'STALE')
        self.assertFalse(after['completion_assured'])

    def test_success_ack_is_not_fulfillment_and_provenance_is_distinct(self):
        result = self.runner.review(self.run_id)
        events = self.runner.store.events(self.run_id, 'alice')
        self.assertTrue(any(e['kind'] == 'tool.response' and e['body']['success'] for e in events))
        self.assertEqual(self.condition(result, 'expense-edit')['status'], 'FAIL')
        self.assertEqual(result['claim']['origin'], 'agent_supplied')
        self.assertEqual(result['observations']['origin'], 'synthetic_provider_confirmed')
        self.assertEqual(self.condition(result, 'expense-edit')['origin'], 'independently_derived')
        self.assertEqual(sorted(e['seq'] for e in events), [e['seq'] for e in events])
        self.assertTrue(all(e['observed'] for e in events))

    def test_missing_readback_never_passes(self):
        self.repaired()
        self.runner.mutate(self.run_id, 'result', available=False)
        r = self.runner.review(self.run_id)
        self.assertEqual(self.condition(r, 'expense-edit')['status'], 'UNKNOWN')
        self.assertTrue(r['coverage_gaps'])
        self.assertEqual(r['freshness']['prior_assurance'], 'STALE')
        self.assertFalse(r['completion_assured'])

    def test_pending_is_not_unknown_fulfillment_or_pass(self):
        run = self.runner.start(self.contract['contract_id'], pending=True)
        r = self.runner.review(run)
        self.assertEqual(self.condition(r, 'expense-edit')['status'], 'PENDING')
        self.assertEqual(self.condition(r, 'private-expenses')['status'], 'UNKNOWN')

    def test_agent_kind_spoof_and_error_cannot_substitute_collector_coverage(self):
        run = self.runner.start(self.contract['contract_id'], fail=True)
        self.runner.provider.write(run, 'alice', 'result', execute_tracker(expense_contract()['source'], True))
        self.runner.store.event(run, 'alice', 'tool.response', 'agent_supplied', {'success': True})
        r = self.runner.review(run)
        self.assertFalse(any(c['status'] == 'PASS' for c in r['conditions']))
        self.assertTrue(any(e['kind'] == 'tool.error' for e in self.runner.store.events(run, 'alice')))

    def test_cross_request_response_id_does_not_close_pending_operation(self):
        run = self.runner.start(self.contract['contract_id'], pending=True)
        self.runner.store.event(run, 'alice', 'tool.response', 'collector_observed', {'request_id': 'different', 'success': True})
        self.runner.store.event(run, 'alice', 'run.finished', 'collector_observed', {})
        self.runner.provider.write(run, 'alice', 'result', execute_tracker(expense_contract()['source'], True))
        r = self.runner.review(run)
        self.assertFalse(any(c['status'] == 'PASS' for c in r['conditions']))

    def test_wrong_item_keys_with_correct_totals_fail(self):
        body = {'items': {'unrelated': 1500}, 'total_cents': 1500, 'add_probe': {'items': {'unrelated': 1500}, 'total_cents': 1500}, 'implementation': 'replace-edit'}
        self.runner.mutate(self.run_id, 'result', body)
        r = self.runner.review(self.run_id)
        for key in ('expense-edit', 'expense-add', 'expense-cap'):
            self.assertEqual(self.condition(r, key)['status'], 'FAIL')

    def test_malformed_state_and_unsupported_generated_check_abstain(self):
        self.runner.mutate(self.run_id, 'result', {'total_cents': True})
        self.assertEqual(self.condition(self.runner.review(self.run_id), 'expense-edit')['status'], 'UNKNOWN')
        contract = expense_contract()
        contract['requirements'].append({'id': 'generated', 'checker': 'generated_but_unexecuted', 'expected': None, 'required': True, 'description': 'A plausible AI-generated check plan.'})
        c = create_contract(self.runner.store, 'alice', contract)
        approve_contract(self.runner.store, 'alice', c['contract_id'], c['contract_hash'], reviewed=True)
        r = self.runner.review(self.runner.start(c['contract_id']))
        c = self.condition(r, 'generated')
        self.assertEqual(c['status'], 'UNKNOWN')
        self.assertFalse(c['checker']['executed'])

    def test_approval_precedes_run_and_changed_contract_needs_new_approval(self):
        original = self.runner.store.contract(self.contract['contract_id'], 'alice')['body']
        new = expense_contract(1400)
        c = create_contract(self.runner.store, 'alice', new)
        with self.assertRaises(ValueError):
            self.runner.start(c['contract_id'])
        with self.assertRaises(ValueError):
            approve_contract(self.runner.store, 'alice', c['contract_id'], self.contract['contract_hash'], reviewed=True)
        approve_contract(self.runner.store, 'alice', c['contract_id'], c['contract_hash'], reviewed=True)
        run = self.runner.start(c['contract_id'])
        p = self.runner.prepare(run)
        self.runner.apply(p, p['digest'], reviewed=True)
        self.assertEqual(self.condition(self.runner.review(run), 'expense-cap')['status'], 'FAIL')
        self.assertEqual(self.runner.store.contract(self.contract['contract_id'], 'alice')['body'], original)
        with self.runner.store.connection() as db:
            decisions = [json.loads(x['body'])['decision'] for x in db.execute('SELECT body FROM contract_decisions WHERE contract_id=?', (c['contract_id'],))]
        self.assertEqual(decisions, ['denied', 'approved'])

    def test_immutable_contract_cannot_be_updated(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.runner.store.connection() as db:
                db.execute('UPDATE contracts SET body=? WHERE id=?', ('{}', self.contract['contract_id']))

    def test_source_and_result_bytes_stale_without_label_bump(self):
        prior = self.runner.review(self.run_id)
        old = self.runner.provider.read(self.run_id, 'alice', 'source')
        new = deepcopy(old['body']);new['travel'] = 501
        self.runner.mutate(self.run_id, 'source', new)
        r = self.runner.review(self.run_id)
        self.assertEqual(r['bindings']['source']['label'], prior['bindings']['source']['label'])
        self.assertNotEqual(r['bindings']['source']['hash'], prior['bindings']['source']['hash'])
        self.assertEqual(r['freshness']['prior_assurance'], 'STALE')
        self.assertEqual(self.condition(r, 'expense-edit')['status'], 'FAIL')

    def test_wrong_owner_cross_run_and_path_ids_rejected(self):
        for run in ('../runs.sqlite3', '0' * 32, self.run_id):
            with self.assertRaises(ValueError):
                review_run(self.temp.name, 'bob', run, 'Done')
        with self.assertRaises(ValueError):
            self.runner.store.event(self.run_id, 'bob', 'tool.response', 'collector_observed', {})

    def test_tampered_event_chain_detected(self):
        # Simulate local corruption beyond ordinary immutable-write API; never accept it.
        with self.runner.store.connection() as db:
            db.execute('DROP TRIGGER immutable_events_UPDATE')
            db.execute('UPDATE events SET run_id=? WHERE run_id=? AND kind=?', ('f'*32, self.run_id, 'tool.response'))
        with self.assertRaises(ValueError):
            self.runner.review(self.run_id)

    def test_repair_plan_requires_exact_fresh_review_preserves_original(self):
        initial = self.runner.review(self.run_id)
        p = self.runner.prepare(self.run_id)
        with self.assertRaises(ValueError):
            self.runner.apply(p, p['digest'])
        q = deepcopy(p);q['after']['total_cents'] = 0
        with self.assertRaises(ValueError):
            self.runner.apply(q, q['digest'], reviewed=True)
        self.runner.apply(p, p['digest'], reviewed=True)
        r = self.runner.review(self.run_id)
        self.assertEqual(r['original_contract'], initial['original_contract'])
        self.assertEqual(r['counts'], {'PASS': 4, 'UNKNOWN': 1})
        self.assertEqual(self.condition(initial, 'expense-edit')['status'], 'FAIL')
        with self.runner.provider.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM versions WHERE run_id=? AND kind=?', (self.run_id, 'result')).fetchone()[0], 2)
        denials = [e for e in self.runner.store.events(self.run_id, 'alice') if e['kind'] == 'repair.denied']
        self.assertEqual(len(denials), 2)

    def test_stale_and_rehashed_modified_plan_rejected(self):
        p = self.runner.prepare(self.run_id)
        q = deepcopy(p);q['after']['total_cents'] = 0;q['digest'] = digest({k:v for k,v in q.items() if k!='digest'})
        with self.assertRaises(ValueError):
            self.runner.apply(q, q['digest'], reviewed=True)
        self.runner.mutate(self.run_id, 'result', execute_tracker(expense_contract()['source']))
        with self.assertRaises(ValueError):
            self.runner.apply(p, p['digest'], reviewed=True)

    def test_interruption_after_provider_write_retries_without_duplicate_effect(self):
        p = self.runner.prepare(self.run_id)
        with self.assertRaises(RuntimeError):
            self.runner.apply(p, p['digest'], reviewed=True, interrupt_after_write=True)
        self.assertEqual(self.condition(self.runner.review(self.run_id), 'expense-edit')['status'], 'UNKNOWN')
        recovered = self.runner.apply(p, p['digest'], reviewed=True)
        repeated = self.runner.apply(p, p['digest'], reviewed=True)
        self.assertEqual(recovered['revision'], repeated['revision'])
        self.assertEqual(self.runner.review(self.run_id)['counts'], {'PASS': 4, 'UNKNOWN': 1})
        events = self.runner.store.events(self.run_id, 'alice')
        self.assertEqual(sum(e['kind']=='repair.completed' for e in events), 1)

    def test_interruption_inside_completion_transaction_rolls_back_and_recovers(self):
        p = self.runner.prepare(self.run_id)
        original = self.runner.store._append_event
        def interrupt(db, run_id, kind, origin, body):
            if kind == 'repair.completed':
                raise RuntimeError('Injected collector completion interruption')
            return original(db, run_id, kind, origin, body)
        with patch.object(self.runner.store, '_append_event', side_effect=interrupt):
            with self.assertRaises(RuntimeError):
                self.runner.apply(p, p['digest'], reviewed=True)
        with self.runner.store.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM repair_results').fetchone()[0], 0)
        self.runner.apply(p, p['digest'], reviewed=True)
        self.runner.apply(p, p['digest'], reviewed=True)
        self.assertEqual(sum(e['kind']=='repair.completed' for e in self.runner.store.events(self.run_id, 'alice')), 1)

    def test_restart_replay_reset_import_preserve_privacy_and_failed_history(self):
        first = self.runner.review(self.run_id)
        after = self.repaired()
        restarted = Runner(self.temp.name, 'alice')
        r = restarted.review(self.run_id)
        self.assertEqual(r['counts'], after['counts'])
        self.assertEqual(r['freshness']['prior_assurance'], 'FRESH')
        imported = restarted.import_receipt(json.loads(json.dumps(after)))
        self.assertFalse(imported['completion_assured']);self.assertFalse(imported['origin_verified'])
        run2 = restarted.reset(self.run_id)
        reset = restarted.review(run2)
        self.assertEqual(self.condition(reset, 'private-expenses')['status'], 'UNKNOWN')
        self.assertTrue(self.condition(reset, 'private-expenses')['original_condition']['required'])
        self.assertEqual(self.condition(first, 'expense-edit')['status'], 'FAIL')
        self.assertEqual(restarted.store.owned_run(run2, 'alice')['contract_id'], self.contract['contract_id'])

    def test_repair_compare_and_swap_rejects_changed_provider_parent(self):
        old = self.runner.provider.read(self.run_id, 'alice', 'result')
        self.runner.mutate(self.run_id, 'result', old['body'])
        with self.assertRaises(ValueError):
            self.runner.provider.write(self.run_id, 'alice', 'result', old['body'], parent=old['seq'])

    def test_receipt_import_rejects_tamper_without_inserting_events(self):
        receipt = self.runner.review(self.run_id)
        before = len(self.runner.store.events(self.run_id, 'alice'))
        receipt['conditions'][0]['status'] = 'PASS'
        with self.assertRaises(ValueError):
            self.runner.import_receipt(receipt)
        self.assertEqual(len(self.runner.store.events(self.run_id, 'alice')), before)


if __name__ == '__main__':
    unittest.main()

class RaceTests(unittest.TestCase):
    setUp = BackendTests.setUp
    # Keep only the new race case rather than inheriting/repeating all parent tests.
    def test_source_change_at_insertion_rejects_stale_plan_before_effect(self):
        p = self.runner.prepare(self.run_id)
        original_write = self.runner.provider.write
        def changed_before_insert(run_id, owner, kind, body, **kwargs):
            if kwargs.get('operation_key', '').startswith('repair:'):
                source = self.runner.provider.read(run_id, owner, 'source')
                new = deepcopy(source['body']);new['edited_lunch'] = 1800
                original_write(run_id, owner, 'source', new, parent=source['seq'])
            return original_write(run_id, owner, kind, body, **kwargs)
        with patch.object(self.runner.provider, 'write', side_effect=changed_before_insert):
            with self.assertRaisesRegex(ValueError, 'Source changed'):
                self.runner.apply(p, p['digest'], reviewed=True)
        with self.runner.provider.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM versions WHERE operation_key=?', ('repair:'+p['digest'],)).fetchone()[0], 0)
        self.assertTrue(any(e['kind']=='repair.error' for e in self.runner.store.events(self.run_id,'alice')))

class ProcessRestartTests(unittest.TestCase):
    setUp = BackendTests.setUp
    def test_actual_new_process_replays_persisted_repaired_run(self):
        import subprocess
        import sys
        plan = self.runner.prepare(self.run_id)
        self.runner.apply(plan, plan['digest'], reviewed=True)
        receipt = self.runner.review(self.run_id)
        script = '''import json,sys
from muse_audit.task_backend.runner import Runner
r=Runner(sys.argv[1],"alice");p=r.review(sys.argv[2]);assert p["freshness"]["prior_assurance"]=="FRESH";assert p["counts"]=={"PASS":4,"UNKNOWN":1};assert not p["completion_assured"];print(json.dumps(p["counts"]))'''
        result = subprocess.run([sys.executable, '-c', script, self.temp.name, self.run_id], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), receipt['counts'])

class UnsupportedLifecycleTests(unittest.TestCase):
    setUp = BackendTests.setUp
    def test_unsupported_semantics_stay_unknown_through_pending_and_source_change(self):
        contract = expense_contract()
        contract['requirements'].append({'id':'comfort','checker':'semantic_comfort','expected':None,'required':True,'description':'It feels comfortable.'})
        c=create_contract(self.runner.store,'alice',contract)
        approve_contract(self.runner.store,'alice',c['contract_id'],c['contract_hash'],reviewed=True)
        pending=self.runner.start(c['contract_id'],pending=True)
        self.assertEqual(BackendTests.condition(self,self.runner.review(pending),'comfort')['status'],'UNKNOWN')
        run=self.runner.start(c['contract_id'])
        changed=deepcopy(contract['source']);changed['travel']=501
        self.runner.mutate(run,'source',changed)
        self.assertEqual(BackendTests.condition(self,self.runner.review(run),'comfort')['status'],'UNKNOWN')
