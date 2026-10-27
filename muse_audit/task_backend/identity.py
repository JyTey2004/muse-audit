"""Full effective project source binding plus explicit runtime/config trust scope."""
from pathlib import Path
import hashlib
import sys
from importlib.metadata import version
from ..io import digest
from . import LOADED_SOURCES


def implementation():
    package = Path(__file__).resolve().parents[1]
    root = package.parent
    files = sorted(package.rglob('*.py')) + [root / 'requirements.txt', root / 'constraints-python312.txt', root / 'pyproject.toml', root / 'run_mcp.py']
    sources = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    packages = {name: version(name) for name in ('mcp','pydantic','openpyxl','python-docx','lxml')}
    return {'revision_label': 'task-backend-1', 'sources': sources, 'source_digest': digest(sources), 'loaded_source_digest': digest(LOADED_SOURCES), 'source_changed_since_process_start': sources != LOADED_SOURCES,
            'runtime': {'python': sys.version.split()[0], 'sqlite': __import__('sqlite3').sqlite_version, 'packages': packages},
            'trust_scope': 'All project Python modules and dependency declarations; installed package version strings, not signed distribution/code hashes. Trusted local filesystem/process; no source authenticity or completeness proof.'}
