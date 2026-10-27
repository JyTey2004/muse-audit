#!/usr/bin/env python3
"""Absolute-path entrypoint for hosts that do not set the process working directory."""
from muse_audit.server import main

if __name__ == '__main__':
    main()
