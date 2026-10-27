#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  print -u2 'Set up the local virtualenv first; see QUICKSTART-MAC.md.'
  exit 1
fi
mkdir -p .local
run_dir=$(.venv/bin/python -c 'import tempfile; print(tempfile.mkdtemp(prefix="demo-",dir=".local"))')
.venv/bin/python -m muse_audit.demo --output "$run_dir/checkpoint"
open "$run_dir/checkpoint/index.html"
