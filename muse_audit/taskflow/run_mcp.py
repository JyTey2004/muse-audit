#!/usr/bin/env python3
"""Absolute-path entrypoint for hosts that do not set the process working directory."""

import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from muse_audit.taskflow.server import main

if __name__ == "__main__":
    main()
