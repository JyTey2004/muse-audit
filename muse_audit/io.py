"""Small-file boundary for selected, locally trusted audit bundles."""
from pathlib import Path
import hashlib
import json
import zipfile

MAX_FILE = 5_000_000
MAX_UNZIPPED = 20_000_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    if Path(path).stat().st_size > MAX_FILE:
        raise ValueError('JSON exceeds 5 MB limit')
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=no_duplicates,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def safe_path(root, relative, must_exist=True):
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Paths must be nonempty relative paths inside the selected workspace')
    if '\\' in relative or Path(relative).as_posix() != relative:
        raise ValueError('Paths must use normalized relative POSIX separators')
    parts = Path(relative).parts
    if any(p in ('.', '..') for p in parts):
        raise ValueError('Path traversal is not permitted')
    current = root
    for part in parts:
        current /= part
        if current.is_symlink():
            raise ValueError('Symlinks are not permitted in audit input paths')
    path = current.resolve()
    if not path.is_relative_to(root):
        raise ValueError('Path is outside selected workspace')
    if must_exist and not path.is_file():
        raise ValueError(f'Input file not found: {relative}')
    if path.exists() and path.stat().st_size > MAX_FILE:
        raise ValueError(f'Input exceeds 5 MB: {relative}')
    return path


def guard_archive(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 2000 or sum(item.file_size for item in entries) > MAX_UNZIPPED:
            raise ValueError('Native document exceeds archive limits')
        if len({entry.filename for entry in entries}) != len(entries):
            raise ValueError('Duplicate ZIP members are unsupported')
        if any(entry.flag_bits & 1 for entry in entries):
            raise ValueError('Encrypted native document is unsupported')
        # Reject DTDs before XML parsers; native office files here need no DTDs.
        for entry in entries:
            if entry.filename.endswith(('.xml', '.rels')):
                data = archive.read(entry)
                if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
                    raise ValueError('DTD/entity-bearing XML is unsupported')


def file_pin(path):
    path = Path(path)
    if not path.is_file():
        return {'sha256': None, 'bytes': None, 'available': False}
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'available': True}
