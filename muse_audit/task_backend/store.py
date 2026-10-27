"""Append-only local evidence store; local principal isolation is not authentication."""
import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
from ..io import canonical, digest


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier():
    return uuid.uuid4().hex


TABLES = ('contracts', 'approvals', 'runs', 'events', 'receipts', 'repair_approvals', 'repair_results', 'imports', 'contract_decisions')


class Store:
    def __init__(self, root, readonly=False):
        self.root = Path(root).resolve()
        self.path = self.root / 'runs.sqlite3'
        self.readonly = readonly
        if readonly:
            if not self.path.is_file():
                raise ValueError('Run store must already exist')
        else:
            self.root.mkdir(parents=True, exist_ok=True)
            with self.connection() as db:
                db.executescript('''
                CREATE TABLE IF NOT EXISTS contracts(id TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS approvals(contract_id TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, owner TEXT NOT NULL, contract_id TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, kind TEXT NOT NULL, origin TEXT NOT NULL, body TEXT NOT NULL, observed TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts(seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS repair_approvals(plan_hash TEXT PRIMARY KEY, run_id TEXT NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS repair_results(plan_hash TEXT PRIMARY KEY, run_id TEXT NOT NULL, revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS contract_decisions(seq INTEGER PRIMARY KEY AUTOINCREMENT, contract_id TEXT NOT NULL, owner TEXT NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS imports(seq INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL);
                ''')
                for table in TABLES:
                    for op in ('UPDATE', 'DELETE'):
                        db.execute(f'CREATE TRIGGER IF NOT EXISTS immutable_{table}_{op} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT,"immutable evidence"); END')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(f'file:{self.path}?mode=ro', uri=True) if self.readonly else sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            yield db
            if not self.readonly:
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def owned_run(self, run_id, owner):
        if not isinstance(run_id, str) or len(run_id) != 32 or any(c not in '0123456789abcdef' for c in run_id):
            raise ValueError('Unknown or unauthorized run')
        with self.connection() as db:
            row = db.execute('SELECT * FROM runs WHERE id=? AND owner=?', (run_id, owner)).fetchone()
        if not row:
            raise ValueError('Unknown or unauthorized run')
        return dict(row)

    def contract(self, contract_id, owner):
        with self.connection() as db:
            row = db.execute('SELECT * FROM contracts WHERE id=? AND owner=?', (contract_id, owner)).fetchone()
        if not row or digest(json.loads(row['body'])) != row['hash']:
            raise ValueError('Missing, unauthorized or modified contract')
        return dict(row)

    def approval(self, contract_id, owner):
        with self.connection() as db:
            row = db.execute('SELECT * FROM approvals WHERE contract_id=? AND owner=?', (contract_id, owner)).fetchone()
        if not row or digest(json.loads(row['body'])) != row['hash']:
            raise ValueError('Original contract needs exact approval before execution')
        contract = self.contract(contract_id, owner)
        if json.loads(row['body'])['contract_hash'] != contract['hash']:
            raise ValueError('Contract approval mismatch')
        return dict(row)

    def event(self, run_id, owner, kind, origin, body):
        self.owned_run(run_id, owner)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            self._append_event(db, run_id, kind, origin, body)

    def _append_event(self, db, run_id, kind, origin, body):
        prior = db.execute('SELECT hash FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1', (run_id,)).fetchone()
        previous = prior['hash'] if prior else ''
        observed = now()
        pin = digest([run_id, kind, origin, body, observed, previous])
        db.execute('INSERT INTO events(run_id,kind,origin,body,observed,previous,hash) VALUES(?,?,?,?,?,?,?)', (run_id, kind, origin, canonical(body), observed, previous, pin))

    def events(self, run_id, owner):
        self.owned_run(run_id, owner)
        with self.connection() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM events WHERE run_id=? ORDER BY seq', (run_id,))]
        previous = ''
        for r in rows:
            body = json.loads(r['body'])
            if r['previous'] != previous or r['hash'] != digest([run_id, r['kind'], r['origin'], body, r['observed'], previous]):
                raise ValueError('Event chain changed or cross-run evidence mixed')
            previous = r['hash']
            r['body'] = body
        return rows

    def save_receipt(self, receipt, owner):
        self.owned_run(receipt['run_id'], owner)
        with self.connection() as db:
            db.execute('INSERT INTO receipts(run_id,body,hash) VALUES(?,?,?)', (receipt['run_id'], canonical(receipt), digest(receipt)))

    def prior_receipt(self, run_id, owner):
        self.owned_run(run_id, owner)
        with self.connection() as db:
            r = db.execute('SELECT * FROM receipts WHERE run_id=? ORDER BY seq DESC LIMIT 1', (run_id,)).fetchone()
        if not r:
            return None
        p = json.loads(r['body'])
        if digest(p) != r['hash'] or p['run_id'] != run_id:
            raise ValueError('Stored receipt changed')
        return p
