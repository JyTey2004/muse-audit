# General task workflow: observed validation

## Native consumer acceptance — 29 October 2026

The same cloud backend is now deployed behind authenticated HTTPS and connected
to consumer Muse. After a preserved native-discovery failure, the runtime catalog
description and supported preferred-connector setting were configured for artifact
creation and verification. Two new ordinary requests then automatically completed
the full workflow, without technical commands or tool names in their prompts.

The Markdown task had six selected checks and the CSV task had three. Independent
Mac replay matched every executed check, the original frozen prompts and sources,
and the exact files downloaded from Muse. Both saved receipts rechecked FRESH.
The source and client guard checks, actual app execution, and limits of the
preference are recorded in [native acceptance](docs/MUSE-NATIVE-ACCEPTANCE.md).

The following sections preserve the earlier skill and guided-client phases;
their failed trials are not reclassified as successful native runs.

## Implemented and installed

Runtime checkpoint `3ab1929163c5875277cb1464f9e0bb74af36423e` adds a per-request
task store, frozen request/source/checklist bindings, text/Markdown/JSON/CSV checks,
the existing native-file adapters, three read-only MCP tools, a real subprocess
SDK client, immutable output snapshots and readable completion receipts.

The exact source package was installed on Muse's per-user cloud computer:
91 manifest files matched, and all 37 taskflow tests passed there. The Mac passed
160 tests across the four suites, the standalone protocols, three offline demos,
dependency checks and 14 separately authored adversarial checks. These are
backend checks, not ordinary-chat consumer acceptance.

## Automatic fresh-chat acceptance: failed

The ordinary prompts were fixed before testing: a workshop CSV with new prices
and a new cap, and a short Atlas handover note with owner, two distinct dates and
a visible risk. Neither prompt named the verifier, task IDs, source paths or
technical commands.

| Trial | What the app returned | Fresh review and receipt |
| --- | --- | --- |
| First CSV | Correct-looking result and file | Missing |
| Second CSV | Read/reused an older file after a failed write; safety notice | Missing |
| First Markdown | Draft text | Missing |
| Third CSV, scoped skill | Draft/file and explicit verification-unavailable notice | Missing |
| Second Markdown, scoped skill | Draft text | Missing |

All five fail the requested automatic workflow. Activity labels such as
“Verified” are not accepted as proof of an MCP call or a fresh resulting file.
The first attempt read the skill but skipped the client. A stronger skill and
then a concise scoped rewrite were rejected by Muse's prompt-injection check.
Original failures and files were preserved, rather than repaired and counted
as fresh-chat successes. Safety controls and approvals were not weakened.

## Directly instructed consumer run: executed, independently replayed

The same two requests were then run as an explicitly instructed integration test
in the setup chat. They each received a new frozen task before generation and a
real MCP client review. This is guided use, not a sixth ordinary-chat success.

| New task | Independently inspected result | Actual receipt |
| --- | --- | --- |
| Workshop CSV | Three exact rows; total $57; $8 remaining under $65; snacks retained | 3 PASS, 1 UNKNOWN; UNRESOLVED |
| Atlas handover | Owner and both date relationships retained; visible risk; 26 whitespace-separated words | 6 PASS, 1 UNKNOWN; UNRESOLVED |

The Mac replay matched each executed check, count, decision and input binding.
The preserved raw SDK responses include initialization, the exact three
read-only tools, capabilities and review for the actual new task IDs, negotiating
protocol `2025-11-25`. Delivered snapshots match the reviewed artifact bytes.
All 91 source files matched the installed runtime manifest and its Git checkpoint.
Purchase/provider state and broad semantic correctness remain unsupported; neither
receipt certifies the entire task. Retained cloud observations are unsigned.

Automatic skill inclusion was turned off after repeated failed acceptance, while
retaining the skill for explicitly requested pilot checks. A new native connector
implementation was then built in the original cloud backend and synced to the Mac.
Deployment, registration and ordinary-request acceptance were unestablished at
that checkpoint; the dated native acceptance section above records the later work.

## Hosted connector implementation: tested, not deployed

Cloud checkpoint `550df9842273081bd14b21248ffa70b44d6c8d9d` adds authenticated,
owner-scoped REST intake, immutable artifact versions and receipt persistence,
plus three genuinely read-only Streamable HTTP MCP tools. The user view is a
compact result/checks table with short unresolved-item reasons and an inline
receipt/date. It is limited to caller-declared synthetic pilot inputs.

Mac verification passed 196 tests, the original 14 adversarial checks, 14 new
independent HTTP acceptance checks, all protocol paths and three offline demos.
The new independent checks first found partial rejected intake, ignored checker
config fields and an incorrect word-count summary; those failures are retained
outside Git. The corrected source passes all 14. Unknown config fields cannot
silently PASS; live capabilities/OpenAPI publish exact config schemas.

The source archive's 117 files were checked against the pinned cloud Git commit.
Only reviewed deltas were applied, preserving the Mac documentation checkpoint
and original planning edits. Raw generated review JSON stays outside the Mac Git
checkout, as required by AGENTS.md.

The original cloud executor exposes no general-purpose HTTPS publication,
deployment identity or persistent Python-service control. Loopback HTTP is
tested, but is not reachable by consumer Muse. The native app route accepts a
brokered API-key bearer connection; no key, tunnel, hosting project, live grant
or registered connector was created. The pending requirement is an actual host
and secure connection, followed by fresh ordinary-request app acceptance.

## Native connection boundary

Muse's account-specific inspection found no supported native model-tool
registration for a task-local stdio server. The installed CLI client creates no
native tool. The hosted connector route needs an actual HTTPS service,
authentication/connection setup and user approval; a draft configuration is not
a registration. No endpoint, credential, public submission or new grant was
created.

The [official connector help](https://www.meta.com/help/superintelligence/1687253048996149/)
confirms chat-created custom connectors, but does not establish local stdio
registration. The [connector guidelines](https://platform.muse.ai/docs) require
documented endpoints, authentication, scopes and tool classifications for their
platform route.

## User presentation

Lead with the useful result, then a compact table of observed checks, unresolved
items and limits, followed by an inline receipt reference and date. Full readable
receipts are secondary; avoid expanded previews repeating the report. Raw machine
receipts, hashes, protocol observations and logs stay behind that presentation.
Never attach an evidence archive as the ordinary task result.

These checks cover declared comparisons against retained files. The model's
requirement interpretation and source transcription are not independently
complete or authenticated. Unsupported semantics, real-world facts and provider
effects stay unverified. A guided integration run cannot establish automatic
fresh-chat behavior.
