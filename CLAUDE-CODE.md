# Local Claude Code connection

This is a developer-host connection to the existing read-only MCP server. Consumer Muse integration remains **NOT RUN / UNTESTED**. Claude Desktop was replaced by Claude Code at the user's request; no Desktop extension is installed by this setup.

## Start

Use the existing isolated Python environment and official, signed-in Claude Code CLI. From this checkout, double-click `start-claude-code.command` or run:

```sh
./start-claude-code.command
```

The launcher prepares synthetic copies and starts Claude Code with only these tools:

- `audit_capabilities`
- `audit_job`
- `prepare_repair`
- `recheck_job`

The MCP configuration is passed for this session only with `--strict-mcp-config`. Global host settings are unchanged. Built-in tools, slash commands and browser integration are disabled, and the launcher disables hooks for the session. The session starts in a separate temporary directory. These choices narrow the host's tool surface; they are not an OS sandbox or hostile-file security certification.

Local paths/configuration and evidence stay under ignored `.local/claude-code/`. The server workspace is `.local/claude-code/sandbox/`, containing copies of the synthetic examples under `inputs/`. Re-running the preparer preserves an existing managed sandbox and refuses to replace an unmanaged directory. The server itself needs no credential; the Claude Code host uses your existing authentication and plan limits.

## Audit and propose

Ask Claude Code:

> Use audit_capabilities, then audit_job on inputs/home_office/job.json and inputs/study_summary/job.json. Explain the actual FAIL and UNKNOWN checks with observed/expected values and exact artifact/source locations. Use prepare_repair for both jobs and show the exact operations. Do not apply anything. Keep consumer Muse UNTESTED.

Expected initial outcomes: budget 6 PASS / 1 FAIL / 1 UNKNOWN, study summary 2 PASS / 1 FAIL / 1 UNKNOWN. The budget fee is missing at Budget!B6; the DOCX quote says 30 minutes instead of the supplied 20.

## Correct only after reviewing the proposal

All MCP tools remain read-only. In a separate Terminal, prepare a local CLI plan for the same synthetic copy and inspect it:

```sh
.venv/bin/python -m muse_audit.cli --workspace .local/claude-code/sandbox \
  plan inputs/home_office/job.json --json-out .local/claude-code/budget-plan.json
cat .local/claude-code/budget-plan.json
```

After reviewing the exact before/after operation, explicitly apply it to an unused output name:

```sh
.venv/bin/python -m muse_audit.cli --workspace .local/claude-code/sandbox \
  apply inputs/home_office/job.json --plan .local/claude-code/budget-plan.json \
  --output .local/claude-code/sandbox/budget-repaired-NEW --approve-reviewed-plan
```

Expected exit 2: the corrected 78,000-cent total exceeds the preserved 75,000-cent cap, and ergonomics remains UNKNOWN. Never raise the cap to make the check pass. Use a new output name for every repair.

Ask Claude Code to audit `budget-repaired-NEW/job.json`, then call `recheck_job` on that same job with the complete receipt it just received as `prior_receipt`. A stable receipt should be FRESH while retaining the cap failure and UNKNOWN. The CLI repair actor must remain distinct from the read-only host tools.

Repeat with the study summary. The corrected quote should yield 3 PASS / 0 FAIL / 1 UNKNOWN, with title and weekly plan preserved. An unchanged repaired receipt should be FRESH; the causal claim remains unsupported.

## Stale evidence and error recovery

Use the copied-source procedure in the private step-by-step guide, always on a new synthetic copy. Increase delivery from 8,000 to 9,000 cents without changing the source-version label, then ask `recheck_job` to compare that copy with the prior repaired budget receipt. Expected: STALE, changed source bindings, and a newly executed audit with 5 PASS / 2 FAIL / 1 UNKNOWN.

An out-of-workspace path such as `../README.md` must be rejected. A subsequent valid audit must still work. Retain the actual failed tool result and the valid recovery call; do not describe the intentional refusal as a successful file read.

## Evidence and limits

Record actual tool-use and tool-result events, final displayed text, file bindings, reviewed CLI operations and new receipts. A model's narrative alone is insufficient. The kernel makes zero model calls; Claude Code is a separate model-powered host. Keep raw events, local logs and account-specific details out of Git and the extension source.

The [private field guide](https://muse-audit-field-guide.tey-jia-ye.chatgpt.site) documents the full workflow. Local host evidence is under `.local/claude-code/host-evidence/`. No consumer Muse or Claude Desktop result is established by this connection.
