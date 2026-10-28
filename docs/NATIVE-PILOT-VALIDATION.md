# Private hosted pilot validation — 28 October 2026

Runtime: existing cloud Work Linux x86_64, Python 3.12.14, Node 24.22.1. Existing virtualenv with pinned MCP 1.29.0/HTTPX/Starlette/Uvicorn. `pip check` passed. This is a cloud source executor, not a deployed server. No live credentials, external ingress, model call, native registration, GitHub push, Site update, tunnel or terms acceptance occurred.

The uploaded archive hash and every one of its 91 manifest entries were verified before reconciliation. `30c72a6` imports the reviewed cumulative Mac content (`3ab1929`); `e918664` implements the pilot. No existing runtime modules in taskflow, native adapters, task_backend or claude_adapter, or original fixtures/tests, were modified by the native implementation after reconciliation. The source is on a new branch of the existing repository; ignored evidence is retained. No unrelated-history merge was used.

Final execution results:

| Suite | Passed |
|---|---:|
| Original native | 54 |
| Hardened synthetic backend | 41 |
| Claude adapter | 28 |
| Per-request taskflow | 37 |
| New connector | 26 |
| Attached independently authored adversarial script | 14 of 14 |

The preserved 160 suite tests plus 26 new connector tests passed. Original native/backend/Claude stdio protocol scripts passed, as did actual loopback TCP Streamable HTTP initialization, tools/list, review/recheck and separate REST writes. Native and backend demos passed. CI includes the connector and attached independent script, but no GitHub CI run was performed because no push was authorized.

Actual HTTP pilot: normal-language synthetic picnic task, selected items apples 12 and water 8, cap65. Task/source/checklist were frozen before the artifact upload. Existing taskflow checkers returned **3 PASS /1 UNKNOWN**, overall **UNRESOLVED**. Table values include exact columns, source rows and total20 versus cap65. “Everyone will like the picnic choices” remained UNKNOWN; checklist/source authenticity also remain disclosed, not silently certified. The compact response contains an inline receipt/date, with machine records behind authenticated details and result references.

Actual changed-version test: uploading apples90/water8 as a new version retained the first version, produced2 FAIL/1 PASS/1 UNKNOWN and made the earlier receipt STALE when rechecked against that version. Actual protocol refused invalid auth (401), foreign owner access and traversal IDs; it enumerated exactly three read-only tools with no owner/root/command argument. Every persisted file hash remained unchanged during review/recheck. Receipt/result persistence was tested separately as an authenticated write and retained exact original snapshot bytes.

Focused regressions also cover original contract edits needing a new intake, idempotency-key conflicts, missing sources/version metadata, source/artifact/checker changes without label changes, altered old receipt assertions, unsupported semantic checks, oversized uploads, invalid base64/JSON, source/parent symlinks, reserved evidence filenames, scope denial, origin/host denial, rate limit, duplicate version no-overwrite and changes during verification. Nonfatal Pydantic incomplete-field and Starlette HTTPX deprecation warnings are retained in logs.

The 14-check script is unchanged from the user's attachment. No new independent agent was spawned, as requested. The 26 connector tests are implementer-authored; do not call them independent consumer acceptance.

**Not run / blocked:** externally reachable HTTPS, TLS/reverse-proxy configuration, Docker build (no engine), live credential provisioning/rotation and accepted native Muse setup, automatic ordinary-request invocation, physical mobile/UI checks, production/adversarial security assessment. Official Meta Help supports asking Muse for a chat-created Custom Connector, but does not establish a mandatory OAuth/remote-MCP settings interface. Bearer/API/Streamable HTTP pilot registration must be observed in the account. If OAuth is required by that account, this pilot does not supply an authorization server. The five failed automatic consumer trials remain failures; guided MCP evidence remains distinct. No zero-error/completion-enforcement/insurance claim follows from these tests.

Complete commands, stdout/stderr, actual raw SDK results, synthetic store and generated receipt/result are packaged under `evidence/`. Snapshot directories in that evidence are synthetic and contain no live key. Use `NATIVE-CONNECTOR-PILOT.md` for local commands and the unexecuted concrete hosting/auth decision. User-facing result presentation should stay compact; machine diagnostics remain behind the downloadable package.
