"""Hosted boundary identity, including deployment/harness configuration. No authenticity claim."""
from pathlib import Path
import hashlib
from importlib.metadata import version
from ..io import digest
ROOT=Path(__file__).resolve().parents[2]
def files():
    paths=list((ROOT/'muse_audit').rglob('*.py'))+list((ROOT/'muse_audit').rglob('*.mjs'))
    paths += [p for folder in ('scripts','deploy','.github/workflows') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT/n for n in ('requirements.txt','constraints-python312.txt','pyproject.toml','run_mcp.py')]
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
LOADED=files()
def identity():
    current=files()
    return {'files':current,'sha256':digest(current),'restart_required':current!=LOADED,
        'transport_dependencies':{n:version(n) for n in ('mcp','starlette','uvicorn','httpx','jsonschema')},
        'trust_scope':'Project source and deployment/harness bytes, declared dependencies and runtime package versions. Not signed distribution/binary/OS attestation. Launch config is separately bound; no live ingress/authentication establishment implied.'}
