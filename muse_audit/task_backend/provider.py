"""Separate synthetic service DB. Acknowledgements do not contain acceptance verdicts."""
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from .store import now
from ..io import canonical, digest


class Provider:
    def __init__(self, root, readonly=False):
        self.path = Path(root).resolve() / 'synthetic-provider.sqlite3'
        self.readonly = readonly
        if readonly:
            if not self.path.is_file():
                raise ValueError('Synthetic provider is unavailable')
        else:
            with self.connection() as db:
                db.executescript('''CREATE TABLE IF NOT EXISTS versions(seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, owner TEXT NOT NULL, kind TEXT NOT NULL, label TEXT NOT NULL, body TEXT NOT NULL, available INTEGER NOT NULL, parent INTEGER, operation_key TEXT UNIQUE NOT NULL, observed TEXT NOT NULL, hash TEXT NOT NULL);''')
                for op in ('UPDATE', 'DELETE'):
                    db.execute(f'CREATE TRIGGER IF NOT EXISTS provider_no_{op} BEFORE {op} ON versions BEGIN SELECT RAISE(ABORT,"immutable provider version"); END')

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

    def write(self, run_id, owner, kind, body, label='v1', available=True, operation_key=None, parent=None, expected_source_hash=None):
        from .store import identifier
        if kind not in ('source', 'result'):
            raise ValueError('Unsupported provider record')
        observed = now()
        value = dict(run_id=run_id, owner=owner, kind=kind, label=label, body=body, available=bool(available), parent=parent, operation_key=operation_key or identifier(), observed=observed)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if expected_source_hash is not None:
                selected = db.execute('SELECT hash FROM versions WHERE run_id=? AND owner=? AND kind=? ORDER BY seq DESC LIMIT 1', (run_id, owner, 'source')).fetchone()
                if not selected or selected['hash'] != expected_source_hash:
                    raise ValueError('Source changed; stale repair write rejected atomically')
            if parent is not None:
                head = db.execute('SELECT seq FROM versions WHERE run_id=? AND owner=? AND kind=? ORDER BY seq DESC LIMIT 1', (run_id, owner, kind)).fetchone()
                if not head or head['seq'] != parent:
                    raise ValueError('Provider parent changed; stale write rejected')
            cursor = db.execute('INSERT INTO versions(run_id,owner,kind,label,body,available,parent,operation_key,observed,hash) VALUES(?,?,?,?,?,?,?,?,?,?)', (run_id, owner, kind, label, canonical(body), int(available), parent, value['operation_key'], observed, digest(value)))
            row = db.execute('SELECT * FROM versions WHERE seq=?', (cursor.lastrowid,)).fetchone()
        return self._decode(row)

    def _decode(self, row):
        if row is None:
            return None
        result = dict(row)
        body = json.loads(result['body'])
        value = {k: result[k] for k in ('run_id','owner','kind','label','parent','operation_key','observed')}
        value.update(body=body, available=bool(result['available']))
        if digest(value) != result['hash']:
            raise ValueError('Provider bytes or run binding changed')
        result['body'] = body if value['available'] else None
        result['available'] = value['available']
        return result

    def read(self, run_id, owner, kind):
        with self.connection() as db:
            row = db.execute('SELECT * FROM versions WHERE run_id=? AND owner=? AND kind=? ORDER BY seq DESC LIMIT 1', (run_id, owner, kind)).fetchone()
        return self._decode(row)

    def read_pair(self, run_id, owner):
        """Source/result from a single SQLite snapshot; not a continuous observer."""
        with self.connection() as db:
            db.execute('BEGIN')
            rows = [db.execute('SELECT * FROM versions WHERE run_id=? AND owner=? AND kind=? ORDER BY seq DESC LIMIT 1', (run_id, owner, kind)).fetchone() for kind in ('source', 'result')]
            decoded = tuple(self._decode(row) for row in rows)
            db.rollback()
        return decoded

    def operation(self, key, run_id, owner):
        with self.connection() as db:
            row = db.execute('SELECT * FROM versions WHERE operation_key=? AND run_id=? AND owner=?', (key, run_id, owner)).fetchone()
        return self._decode(row)


def execute_tracker(source, corrected=False):
    """Actual arithmetic operations, ported from Workcheck's seeded Tracker case."""
    lunch, replacement, travel = source['lunch'], source['edited_lunch'], source['travel']
    items = {'lunch': lunch}
    total = lunch
    old = items['lunch']
    items['lunch'] = replacement
    total += replacement - old if corrected else replacement
    probe_items = {'lunch': lunch}
    probe_total = lunch
    probe_items['travel'] = travel
    probe_total += travel
    return {'items': items, 'total_cents': total, 'add_probe': {'items': probe_items, 'total_cents': probe_total}, 'implementation': 'replace-edit' if corrected else 'append-edit'}
