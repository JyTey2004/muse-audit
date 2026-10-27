#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  print -u2 'Set up the local virtualenv first; see QUICKSTART-MAC.md.'
  exit 1
fi
if ! command -v claude >/dev/null 2>&1; then
  print -u2 'Install/sign in to the official Claude Code CLI first.'
  exit 1
fi
.venv/bin/python scripts/prepare_claude_code.py
project_dir=$PWD
session_dir=$(mktemp -d "${TMPDIR:-/tmp}/muse-audit-claude.XXXXXX")
cd -- "$session_dir"
exec claude \
  --restricted --tools "" --strict-mcp-config \
  --mcp-config "$project_dir/.local/claude-code/mcp.json" \
  --disable-slash-commands --no-chrome \
  --settings '{"disableAllHooks":true}' \
  --allowedTools mcp__muse_audit__audit_capabilities mcp__muse_audit__audit_job mcp__muse_audit__prepare_repair mcp__muse_audit__recheck_job \
  -- 'Use Muse Audit only on the synthetic inputs/home_office/job.json and inputs/study_summary/job.json bundles. Start with audit_capabilities. Show exact evidence locations and preserve every FAIL and UNKNOWN. Prepare proposals only; applying a repair requires a separately reviewed local CLI command. Consumer Muse integration remains UNTESTED.'
