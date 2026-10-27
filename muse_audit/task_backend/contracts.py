"""Explicit hand-authored acceptance contracts, not natural-language translation."""
import json
from copy import deepcopy
from .store import identifier, now
from ..io import canonical, digest


def expense_contract(max_total_cents=2000):
    return {'schema': 1, 'version': 'task-contract-1', 'request': 'Edit my lunch expense and keep accurate totals and my expenses private.',
            'source': {'currency': 'SGD', 'lunch': 1000, 'edited_lunch': 1500, 'travel': 500},
            'allowed_actions': ['synthetic.add', 'synthetic.edit', 'synthetic.read', 'synthetic.repair_copy'],
            'forbidden_changes': ['original approved requirements', 'source amounts', 'privacy obligation', 'add-expense behavior'],
            'requirements': [
                {'id': 'expense-edit', 'checker': 'edited_total', 'expected': 1500, 'required': True, 'description': 'Edited lunch total equals 1500 cents.'},
                {'id': 'expense-add', 'checker': 'add_total', 'expected': 1500, 'required': True, 'description': 'Protected lunch plus travel total equals 1500 cents.'},
                {'id': 'expense-cap', 'checker': 'max_total', 'expected': max_total_cents, 'required': True, 'description': 'Result total stays within the explicitly approved cap.'},
                {'id': 'private-expenses', 'checker': 'privacy', 'expected': None, 'required': True, 'description': 'Only I can read my expenses.'},
                {'id': 'allowed-actions', 'checker': 'allowed_actions', 'expected': None, 'required': True, 'description': 'All recorded actions are allowed by the original contract.'}],
            'synthetic': True}


def validate(contract):
    required = {'schema','version','request','source','allowed_actions','forbidden_changes','requirements','synthetic'}
    if not isinstance(contract, dict) or set(contract) != required or contract['schema'] != 1 or contract['synthetic'] is not True:
        raise ValueError('Unsupported explicit synthetic contract schema')
    if not isinstance(contract['request'], str) or not 1 <= len(contract['request']) <= 10000:
        raise ValueError('Invalid task request')
    source = contract['source']
    if not isinstance(source, dict) or set(source) != {'currency','lunch','edited_lunch','travel'} or source['currency'] != 'SGD':
        raise ValueError('Unsupported source schema')
    for key in ('lunch', 'edited_lunch', 'travel'):
        if type(source[key]) is not int or not 0 <= source[key] <= 1000000:
            raise ValueError('Source values must be bounded integer cents')
    if not isinstance(contract['requirements'], list) or not 1 <= len(contract['requirements']) <= 50:
        raise ValueError('Explicit nonempty checklist required')
    ids = set()
    for r in contract['requirements']:
        if not isinstance(r, dict) or set(r) != {'id','checker','expected','required','description'} or not isinstance(r['id'], str) or r['id'] in ids or type(r['required']) is not bool:
            raise ValueError('Malformed or duplicate requirement')
        ids.add(r['id'])
        if r['checker'] in ('edited_total', 'add_total', 'max_total') and (type(r['expected']) is not int or not 0 <= r['expected'] <= 1000000):
            raise ValueError('Supported constraints must be bounded integer cents')
    privacy = next((r for r in contract['requirements'] if r['id'] == 'private-expenses'), None)
    if not privacy or privacy['checker'] != 'privacy' or privacy['required'] is not True:
        raise ValueError('Required privacy UNKNOWN must be preserved')
    if not isinstance(contract['allowed_actions'], list) or not contract['allowed_actions'] or any(x not in ['synthetic.add','synthetic.edit','synthetic.read','synthetic.repair_copy'] for x in contract['allowed_actions']):
        raise ValueError('Unsupported allowed-action policy')
    if not isinstance(contract['forbidden_changes'], list) or not contract['forbidden_changes']:
        raise ValueError('Protected commitments must be explicit')


def create_contract(store, owner, contract):
    validate(contract)
    contract = deepcopy(contract)
    key = identifier()
    with store.connection() as db:
        db.execute('INSERT INTO contracts VALUES(?,?,?,?,?)', (key, owner, canonical(contract), digest(contract), now()))
    return {'contract_id': key, 'contract_hash': digest(contract), 'approved': False}


def approve_contract(store, owner, contract_id, approved_hash, reviewed=False, actor='local CLI user'):
    contract = store.contract(contract_id, owner)
    decision = 'approved' if reviewed is True and contract['hash'] == approved_hash else 'denied'
    body = {'contract_id': contract_id, 'contract_hash': approved_hash, 'decision': decision, 'actor': actor, 'observed_at': now(), 'identity_authenticated': False}
    with store.connection() as db:
        db.execute('INSERT INTO contract_decisions(contract_id,owner,body,hash) VALUES(?,?,?,?)', (contract_id, owner, canonical(body), digest(body)))
        if decision == 'approved':
            db.execute('INSERT INTO approvals VALUES(?,?,?,?)', (contract_id, owner, canonical(body), digest(body)))
    if reviewed is not True:
        raise ValueError('Explicit contract approval required; denial retained')
    if decision == 'denied':
        raise ValueError('Contract changed since review; denial retained')
    return body
