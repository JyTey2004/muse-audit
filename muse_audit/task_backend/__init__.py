"""Bounded offline task acceptance backend. Synthetic provider; no host visibility."""

from pathlib import Path as _Path
import hashlib as _hashlib
_PACKAGE = _Path(__file__).resolve().parents[1]
LOADED_SOURCES = {p.relative_to(_PACKAGE.parent).as_posix(): _hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(_PACKAGE.rglob('*.py')) + [_PACKAGE.parent / n for n in ('requirements.txt','constraints-python312.txt','pyproject.toml','run_mcp.py')]}
