"""Logical retained-file byte accounting. No deletion or payload logging on quota refusal."""
import logging
import stat
from pathlib import Path

class QuotaExceeded(ValueError):pass

def stored_bytes(root):
    total=0
    for path in Path(root).rglob('*'):
        mode=path.lstat().st_mode
        if stat.S_ISLNK(mode):raise ValueError('Symlinked owner storage refused')
        if stat.S_ISREG(mode):total+=path.stat().st_size
        elif not stat.S_ISDIR(mode):raise ValueError('Unsupported owner storage entry')
    return total

def enforce(root,limit,additional,operation):
    used=stored_bytes(root)
    if used+additional>limit:
        # Diagnostic metadata goes to the operator's stderr/journal, NEVER a partial task
        # or an unbounded application file outside the quota. No selected data/keys logged.
        logging.getLogger('stardive.write_attempts').warning('stored_byte_quota_rejected operation=%s used=%d projected_additional=%d limit=%d',operation,used,additional,limit)
        raise QuotaExceeded(f'Stored-byte quota exceeded: {used} retained + {additional} projected bytes exceeds {limit}; preserve prior data and request operator review')
    return used
