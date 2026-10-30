# Dedicated Muse controlled task workflow

This entry point accepts one normal request in `args.request`. It supports text,
Markdown, JSON and CSV artifacts through the existing private HTTPS backend.
It creates no new credential, permission, endpoint, scheduled job or cloud service.
The three native MCP tools stay read-only.

`workflow.js` awaits two native Promise-returning stages: "Working on your
request", then "Checking before delivery". The first stage selects the checklist,
freezes the exact request before generating any result, creates a private draft
and uploads it. The second runs `controller.py finalize`: an actual read-only
MCP `taskflow_review` through the installed fixed-host client, followed by separate
REST receipt persistence, mandatory completion and guarded release. The MCP
result and saved receipt must match on every field except their check timestamp.
Missing MCP evidence, failed/unknown checks or changed bindings block delivery.
The final view is the requested file, compact checked values, pass count and a
shortened real receipt reference/date; the full reference remains in run state.

The existing SCS credential, backend and three read-only MCP tools are reused.
No verdict is accepted from the agent. Runtime suspension/provider errors remain
native errors; they are never swallowed by a generic catch. Production accepts
only the exact normal request, with no skip/override options. The internal
`verify` and `deliver` commands remain separately testable; `finalize` invokes
delivery only after real verification succeeds, without another agent handoff.

Delivery is a separate code path, never a copy of the worker's local draft. It
requires this run's persisted receipt, checks its request/version/artifact bindings,
revalidates current server completion, downloads through the existing gated result
URL and checks the exact bytes before exclusive creation of the final output.
No implicit verification, repair, cap change or draft fallback happens in the
`deliver` command. `finalize` explicitly checks first, then calls it.
A new upload or changed evidence blocks later retrieval. Earlier files/history
are preserved, and changed final files are never overwritten.

In Muse install controller.py beside the existing connector helpers, then create
the saved workflow from workflow.js. Use a dedicated chat to route a plain user
request to `workflow.launch(name='stardive-controlled-task',args={request:exact})`.
Render only the curated final return: useful file, compact checked-value summary
(or a small observed/required table when useful), receipt/date and one scope sentence. Do not attach scratch/plan/receipt JSON.

The saved workflow and publisher source plus private run context are trusted.
Native child agents retain normal workspace access: this is not an OS sandbox
against a malicious process rewriting that trusted source/context. JavaScript
stage schema validation does not authenticate model prose; authoritative checks
and file release remain in the backend, and the publisher independently retrieves
them. The controlled entry point does not add a global Muse final-response veto.
Dedicated-chat routing itself is a scoped agent instruction; other chats remain
outside this workflow.

Production accepts no skip/override flags. The separately named negative-test
snapshot changes only SKIP_VERIFICATION_TEST to true, deliberately omits verify,
and calls the same guarded publisher to prove actual missing-receipt refusal.
It always returns blocked and exposes no final file. It is not the user entry point.

Validation: `python -m unittest discover -s tests_controlled -v` exercises the
controller against the actual local ASGI backend with synthetic credentials.
`node tests_controlled/test_workflow.mjs` executes the exact workflow JavaScript
with manufactured stage outputs. Actual native runs are separate acceptance.

## Live entry point and acceptance

Use [Stardive Controlled Tasks](https://muse.ai/thread/8e01a9ee-9db9-4391-8a1f-d04b96b87cd6)
and submit a normal text, Markdown, JSON or CSV request. The dedicated chat was
selected directly after the cross-chat setup-history message failed Muse's safety
check. No safety, credential or permission setting was changed.

Actual native v3 runs on29 October were independently rechecked on30 October2026:

| Request | Observed outcome |
| --- | --- |
| Willow rollout JSON | 4 PASS, server COMPLETED, exact96-byte result, checks and receipt together in Muse |
| Notebook8 plus pen5 under unchanged cap10 | 2 PASS/1 FAIL, backend409, blocked workflow, delivery stage never launched, no final file |
| Deliberately omitted verification in the fixed test snapshot | Actual missing-receipt409, no saved receipt/completion record, no final file |
| Original Willow note with only-these-facts condition | 6 PASS/1 UNKNOWN, backend409, no delivery; unsupported semantic condition preserved |

Normal receipt `receipt-18e84ac0c50346fcaa96cf5558c57e95` covers
`task-12662238a49f4e6b`. The actual UI download, native publisher file, server
snapshot and independently replayed checker result match. The enabled field is
JSON boolean false, not a string or numeric substitute. Selected source pins and
the exact original requests match for all four acceptance cases. Live MCP rechecks
of stored audits are FRESH; that label on failed/unknown audits means intact
historical evidence, not passing completion. Skipped verification created no audit.
All106 pre-upgrade retained files were checked unchanged, and the existing backend
release `de6d568` remains active without an upgrade or new credential.

The native installed helper matches the reviewed v3 manifest. The successful and
failed run scripts match production apart from runtime trailing-newline storage;
the omission snapshot has only the documented two-line test difference. Native
filesystem checks confirm that failed and omitted-verification runs have no final
publisher output. The successful native run is
`workflow-run-8b60c6cbf9c3459d885a1cb844c8e64d`; the failed-check run is
`workflow-run-40de4a2db5a24e79964fd1131190d7f3`; omission is
`workflow-run-437966148f8749258aecd7a6e9316ab1`.

Historical v3 validation had21 publisher/controller tests and23 asynchronous JavaScript tests, alongside
231 existing Python regressions and the required original protocol checks.
Initial v1 native runs failed integration after freeze because agent results were
not awaited; both were stopped and preserved, with no delivered file. They are
not counted as valid skipped-verification acceptance. A native minimal probe
confirmed the corrected await/result behavior before the v3 acceptance runs.

A supported file format does not make every requested condition automatically
checkable. Unsupported conditions remain UNKNOWN and block this workflow; the
original note was not weakened or repaired. The separate supported JSON request
is the positive acceptance case. Native routing remains scoped to this chosen
chat, and the source/private-context trust boundary above still applies.

## Final-check UX acceptance (30 October 2026)

The installed v4 workflow now has two user-visible phases, work and check, with
one bounded child per phase. A fresh ordinary request for `release-settings.json`
returned the file, a one-line four-check summary and a shortened dated receipt
in the same chat view. No commands, protocol steps or evidence-package attachment
were shown in that task view. Native activity records freeze before draft upload,
then the `finalize` command in the check child; the installed source performs the
actual read-only MCP call before receipt persistence and guarded publication.

| Fresh native case | Result |
| --- | --- |
| Maple release settings JSON | 4 PASS; COMPLETED; actual UI download equals the109-byte backend snapshot |
| Exact six-word text with at-most-three-word limit | 1 PASS/1 FAIL; BLOCKED; no completed file; backend result409 |
| Fixed omission snapshot | No MCP review or receipt; missing-receipt409; BLOCKED; no final file |

The positive run is `workflow-run-6cb3c11f8b9c444ab09c173242d367c4`, receipt
`receipt-e024e6806884456b97210d917d485146`. Failed verification is
`workflow-run-eb930d9a308e4c2090766839269cc97c`, receipt
`receipt-0180cc3e316f4c3f8aa84daf89095ece`. Omission is
`workflow-run-5bb22f871f10487fba7474096f44ddf0`, with no receipt.
Independent HTTPS reads confirmed exact original requests, current completion
states and download behavior; real read-only MCP rechecks of the two saved audits
were FRESH. A FRESH failed audit still blocks completion.

Current validation:27 controller tests against the actual local ASGI/MCP backend,
26 asynchronous JavaScript checks (also run in Muse), required54 core tests and
original protocol tests passed. The tests cover missing MCP evidence, mismatched
MCP/receipt evidence, failed/unknown checks, stale delivery and absent receipts.
The existing backend release and connection are unchanged. The same dedicated-chat
routing and trusted-source/private-context boundaries above still apply.

## Action card

The final check child reads the exact private `assurance-card.json` generated
by the controller and passes its `summary` object unchanged to the native
`widget.create_list_widget`. It returns the real embed token; the parent displays
it beside the normal guarded file attachment. Clicking "See what Muse did"
opens a simple action list in chat, with "Audited by Stardive" below it.

The controller records actual completed transitions, never model-written action
narrative. It saves an immutable, task-bound display snapshot under
`~/workspace/.stardive-assurance/cards/task-<id>.json` with private permissions.
The exact card-generated request carries that task ID. The configured parent
handles it separately from file requests: run only `controller.py card-details
--task-id task-<id>`, require the returned `detail_request` to match the clicked
message, then pass `widget_args` unchanged to `widget.create_list_widget` and
embed the real token. This command reads only that snapshot. It never contacts
the backend, checks again, creates a receipt or delivers a file.

The details list shows the recorded request/preparation/check/delivery actions,
check status and a short date/receipt footer. Audit branding requires a stored
audit matching the actual MCP review. Failed checks retain the audit but show
Delivery blocked and no delivered-file action; skipped verification says Audit
not completed. This is a dated snapshot of selected requirements and key task
actions, not certification of every hidden agent or tool action. Older card
records are never overwritten. Widget creation cannot approve delivery, and an
unavailable widget has the original honest text fallback.

Native HTML widgets failed to preview in this consumer client on30 October2026,
including a bare static probe, both file/inline variants and a parent-created
card. Those failures are retained. The built-in native list card rendered and
its tap successfully opened recorded actions. It uses a read-only follow-up in
chat rather than an in-place HTML expansion. The HTML renderer remains a private
source/snapshot artifact; it is not the active presentation route.

The same dedicated-chat routing and trusted-source/private-context boundaries
still apply; no global host interception or continuously live card is claimed.


Native v6 acceptance on30 October2026: a fresh ordinary Cedar JSON request
returned its normal file and a working native assurance card. Tapping the card
opened four recorded actions, the four selected check descriptions/status and
Audited by Stardive underneath. The actual UI download, native publisher output
and current backend snapshot matched exactly (108 bytes). The normal task was
`task-137c059478654e5b`, receipt `receipt-d840a915c89c42c0ad39ba4270704950`.
The failed six-word/three-word-cap request stayed BLOCKED with1 PASS/1 FAIL,
no final output and backend result409. Skipped verification also stayed BLOCKED,
with no MCP record/receipt/final output and result409. Both blocked card taps
opened their correct recorded action views; skipped verification displayed
Audit not completed instead of audit branding.

Installed helpers and all three run snapshots matched the reviewed v6 source,
with only the documented omission-test differences and newline normalization.
The private card records matched the original task/version/request/artifact/
receipt/actions context and had0600 permissions. Native MCP evidence digests
matched the stored audits, which independently rechecked FRESH. The36 controller,
29 asynchronous workflow checks (also executed in Muse), required54 core and
original protocol tests passed. No backend, credential, scope or permission
change was required. HTML preview failures remain part of the acceptance record.
