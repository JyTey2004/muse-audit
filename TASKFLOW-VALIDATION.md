# General task workflow: observed validation

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
implementation is being prepared in the original cloud backend; its deployment,
registration and ordinary-request acceptance are not yet established.

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
