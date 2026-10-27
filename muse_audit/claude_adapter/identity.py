"""Effective source, declarations and runtime binding. Not an authenticity signature."""
import hashlib
import json
import platform
import sqlite3
import subprocess
from pathlib import Path
from importlib.metadata import version
ROOT = Path(__file__).resolve().parents[2]
def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',',':'), allow_nan=False).encode()
def digest(obj): return sha(canonical(obj))
def sources():
    paths = list((ROOT/'muse_audit').rglob('*.py')) + list((ROOT/'muse_audit').rglob('*.mjs'))
    paths += [p for p in (ROOT/'scripts').rglob('*') if p.is_file() and p.suffix in ('.py','.sh','.json','.mjs')]
    paths += list((ROOT/'.github/workflows').glob('*.yml'))
    paths += [ROOT/n for n in ('requirements.txt','constraints-python312.txt','pyproject.toml','run_mcp.py')]
    return {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(paths)}
LOADED = sources()
def implementation():
    current=sources()
    node=subprocess.run(['node','--version'],capture_output=True,text=True,timeout=5,check=True).stdout.strip()
    return {'sources':current,'source_digest':digest(current),'restart_required':current!=LOADED,
      'runtime':{'python':platform.python_version(),'node':node,'sqlite':sqlite3.sqlite_version,
        'packages':{n:version(n) for n in ('mcp','pydantic','openpyxl','python-docx','lxml')}},
      'trust':'Trusted local filesystem/process and generated code. Dependencies bound by declarations and installed versions, not signed distribution hashes. Claude executable version captured by host; no credential, service authenticity or sandbox claim.'}
