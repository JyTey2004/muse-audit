"""Append-only host records. Only trusted local CLI writes; MCP never accepts records."""
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from .identity import canonical, digest
class Store:
 def __init__(self, root, readonly=False):
  self.root=Path(root).resolve(strict=True)
  self.path=self.root/'claude-runs.sqlite3'
  self.db=sqlite3.connect(f'{self.path.as_uri()}?mode=ro' if readonly else str(self.path),uri=readonly)
  self.db.row_factory=sqlite3.Row
  if not readonly:
   self.db.execute('CREATE TABLE IF NOT EXISTS records (seq INTEGER PRIMARY KEY, kind TEXT, run TEXT, principal TEXT, body TEXT)')
   for operation in ('UPDATE','DELETE'):
    self.db.execute(f"CREATE TRIGGER IF NOT EXISTS no_{operation} BEFORE {operation} ON records BEGIN SELECT RAISE(ABORT,'append only'); END")
   self.db.commit()
 def append(self,kind,run,principal,body):
  self.db.execute('INSERT INTO records(kind,run,principal,body) VALUES(?,?,?,?)',(kind,run,principal,canonical(body).decode()));self.db.commit()
 def records(self,run,principal,kind=None):
  if not re.fullmatch('[a-f0-9]{32}',run):raise ValueError('Invalid run ID')
  rows=self.db.execute('SELECT * FROM records WHERE run=? AND principal=? ORDER BY seq',(run,principal)).fetchall()
  return [json.loads(r['body']) for r in rows if kind is None or r['kind']==kind]
 def original(self,run,principal):
  rows=self.records(run,principal,'contract')
  if len(rows)!=1:raise ValueError('Unknown/foreign run or principal')
  body=rows[0]
  if body['root']!=str(self.root):raise ValueError('Store root binding mismatch; explicitly prepare a fresh local run')
  if digest(body['contract'])!=body['contract_hash']:raise ValueError('Contract binding mismatch')
  return body

def prepare(root,principal,workspace,contract):
 from .contract import CONTRACT
 if not isinstance(contract,dict) or not isinstance(contract.get('requirements'),dict) or set(contract['requirements'])!=set(CONTRACT['requirements']):raise ValueError('All original obligation IDs required')
 root=Path(root);root.mkdir(parents=True,exist_ok=True)
 workspace=Path(workspace).resolve()
 if workspace.exists():raise ValueError('Workspace must be new; originals are never overwritten')
 workspace.mkdir(parents=True)
 if root.resolve()==workspace or root.resolve() in workspace.parents or workspace in root.resolve().parents:raise ValueError('Store and generated workspace must be separate')
 if not principal or len(principal)>200:raise ValueError('Explicit principal required')
 run=uuid.uuid4().hex; s=Store(root)
 body={'run_id':run,'root':str(root.resolve()),'workspace':str(workspace),'contract':contract,'contract_hash':digest(contract),'created_at':time.time()}
 s.append('contract',run,principal,body)
 return body

def approve(root,principal,run,expected):
 s=Store(root);c=s.original(run,principal)
 if expected!=c['contract_hash']:raise ValueError('Review exact contract hash before approval')
 if s.records(run,principal,'host'):raise ValueError('Cannot replace original approval after execution')
 s.append('approval',run,principal,{'contract_hash':expected,'approved_at':time.time(),'decision':'approved'})
