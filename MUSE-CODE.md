# Muse Code local checkpoint — 27 October 2026

Muse Code is a separate developer host. This is the dated 27 October checkpoint. For the later bounded consumer Muse app trial on 28 October, see [CONSUMER-VALIDATION.md](CONSUMER-VALIDATION.md); it does not validate live Muse Code model use.

## Observed status

| Check | Result |
|---|---|
| Official Muse Code installation | PASS, 1.4.13 (1.4.13-R6996.1), macOS arm64 |
| Official device sign-in | PASS, after explicit user approval; CLI credential stored outside this repository |
| Developer portal | Accessible; this does not establish model entitlement |
| Read-only `muse usage --json` | Exit 0, `allowance: null`, `reason: no_allowance` |
| Muse Code starts the local MCP server | PASS with offline echo provider |
| Muse Code discovers audit tools | PASS, exactly the four expected names |
| Muse Code model-driven tool calls | NOT RUN |
| Muse Code evidence display and correction/recheck | NOT RUN |
| Consumer Muse connection, tool calls and UI | NOT RUN / UNTESTED |

The offline discovery run used a copied synthetic workspace, `--provider echo`, `--preset empty`, `--contributor-mode off` and `MUSE_CONTRIBUTOR_MODE=0`. Shell, file writes, web tools, reminders, foreign personal context and session logging were disabled. Project trust was not granted. A local metadata-only protocol probe observed `initialize`, `notifications/initialized` and `tools/list`, with `audit_capabilities`, `audit_job`, `prepare_repair` and `recheck_job` returned. It recorded method names and tool inventory, not protocol payloads.

An initial diagnostic incorrectly assumed a fixed `tools/list` order. The corrected comparison requires exactly four unique expected names, without imposing an ordering that MCP does not require. Both the original diagnostic and observed ordering remain in ignored local evidence.

This establishes host startup and discovery only. Echo output is not a Meta model response, an audit tool invocation or successful evidence presentation.

## Privacy and billing gate

No Meta model request was sent. Account-specific billing observations stay in ignored local evidence. The portal displayed a separate content-improvement notice for active promotional credits; the per-run Contributor flag has not been established to override that notice. The user explicitly chose to keep live model testing paused with no billing changes. Billing and promotional-credit settings were left unchanged. Do not resume model calls, use the credits, create another key, purchase a subscription or accept new terms without the applicable explicit authorization.

Meta documents a per-run `--contributor-mode off` flag and `MUSE_CONTRIBUTOR_MODE=0`. This checkpoint does not claim the saved interactive default was changed. Apply the explicit override to every future trial. For pay-as-you-go, also select a Standard model rather than a Contributor model, and establish the account's applicable data-use and billing rules before running it.

## Local configuration and next trial

The prepared absolute-path server entry, copied synthetic files, offline events and protocol probe are under ignored `.local/muse-code-setup-20261027/`. No global MCP configuration was installed. The working launch override addresses a single server:

```text
-c mcp_servers.muse_audit={"transport":"stdio","command":"<checkout>/.venv/bin/python","args":["<checkout>/run_mcp.py","--workspace","<synthetic-workspace>"]}
```

Replace the placeholders with local absolute paths and pass the entire key/value as one argument. The installed CLI rejected overriding the whole `mcp_servers` map. Enterprise-policy validation of an attempted settings envelope also failed; it is not recorded as validated user configuration. The successful echo launch and protocol observation establish only the specific per-server override above.

Once billing/privacy authorization is resolved, the live trial must use only the copied `inputs/home_office/job.json` and `inputs/study_summary/job.json`. Require actual host tool events and final text showing observed/expected values and exact evidence locations. Review each `prepare_repair` operation, apply it separately with the local CLI into a fresh output directory, then call `recheck_job` with the exact prior receipt. Check source-change STALE detection, traversal refusal and valid recovery. Keep outstanding FAIL and UNKNOWN outcomes visible. Do not count prior Claude Code results as Muse Code results.

The 54-test suite, standalone real MCP subprocess checks (protocol 2025-11-25) and `pip check` passed again. Runtime, tests and original example files were not changed by this setup.

## Official references

- [Installation and overview](https://dev.meta.ai/docs/muse-code)
- [Authentication and billing](https://dev.meta.ai/docs/muse-code/auth)
- [Contributor mode and subscriptions](https://dev.meta.ai/docs/muse-code/subscriptions)
- [MCP extension configuration](https://dev.meta.ai/docs/muse-code/extending)
- [Standard and Contributor model pricing](https://dev.meta.ai/docs/pricing-rate-limits)

For a model-free local report now, run `./start-demo.command`. For the already verified Claude Code developer-host flow, see [CLAUDE-CODE.md](CLAUDE-CODE.md).
