# Receipt-required backend completion

The existing private HTTPS backend now requires explicit server completion before
canonical result delivery. This is enforced by the service, including the old
receipt result URL. Muse exposes no supported final-response veto in the inspected
interfaces; a chat that never contacts Stardive can still create a local file and
say done. Client instructions and preferences do not remove that boundary.

Flow: freeze original request and interpreted checklist before generation, upload
an immutable version, review, save a server-recomputed verification receipt, POST
`/api/tasks/{task_id}/complete` with only `receipt_ref`, require `COMPLETED`, then
retrieve the receipt result. `GET /api/tasks/{task_id}/completion` revalidates the
current completion. These writes use the existing receipt scope. MCP remains
exactly three read-only tools.

Saving a receipt returns `AUDIT_SAVED`, not completion. Failed audits remain
historical records. Missing/failed/unknown/unsupported/stale/incomplete verification
or changed receipt/result bytes return HTTP409 BLOCKED on completion and delivery.
Every frozen supported requirement must pass; checklist completeness, source
truth, meaning, privacy and external provider state remain unverified.

New versions receive server sequence numbers and append-only upload intents.
The latest upload wins regardless of version name; replaying an old upload does
not reactivate it. A missing latest version or incomplete intent blocks completion.
Legacy multiple-version tasks need a new upload to establish unambiguous order.
Historical records are preserved. Old receipts without an integrity manifest need
fresh verification and receipt persistence; runtime/config changes also stale
prior evidence. No historical receipt is silently promoted.

Completion uses the owner lock, recomputes evidence before atomic publication,
counts staging and records toward quota, and is idempotent for the same receipt.
Delivery returns already-read hash-bound bytes under the same lock. The filesystem
and process are trusted: hashes do not protect against an operator replacing the
entire trusted store. This is not a publicly signed receipt protocol.

Validation: 23 new backend HTTP/state/race tests, plus the original 208 tests,
pass locally. Existing advisory-result tests now expect denial until explicit
completion; their failed/unknown evidence remains accessible as history. Actual
consumer Muse skipped/failed and ordinary-request tests are recorded separately
from these local tests; global host enforcement is not inferred from backend409.

## Observed consumer acceptance, 29 October 2026

The change is live at the existing private HTTPS origin, release `de6d568`.
All121 staged source files matched the Mac archive; actual ARM host validation
passed41 taskflow and67 connector tests. The231 local unit tests, standalone
protocol checks, fresh demos and dependency check passed. Independent public
HTTPS probes verified missing/failed/unknown receipts, forged verdict rejection,
save-only delivery denial, valid idempotent completion and newer-upload staleness.

| Actual fresh Muse test | Server and visible app outcome |
| --- | --- |
| Skipped review and receipt persistence | HTTP409 BLOCKED; no audit receipt or completion record; no completed file attached |
| Notebook8 plus pen5, fixed cap10 | 2 PASS,1 FAIL, total13; completion409 and canonical result409; no repair or completed file |
| Ordinary Cedar handover request | 6 PASS; server COMPLETED; 20 words under40; result, breakdown and receipt together in the app |

Cedar receipt: `receipt-cc60ec53f94f4bfab4a52776f0401048`, task
`task-39d44c75812f41b9`. Independent checks confirmed the exact original prompt,
selected request source pins, FRESH server recheck, identical134-byte app download
and receipt snapshot, and matching independent Mac checker results. No prior Vega
facts occur in the transferred source. The agent did read earlier local examples;
this is not proof of local workspace privacy or isolation.

Failed audit: `receipt-333b143abda445df80fc6299234938d5`, task
`task-81ff092559cb43f2`; the failed receipt remains valid historical failed evidence,
not successful completion. Skipped task `task-878508dd4a3f4fb7` has neither audit
nor completion record. Both negative tests paraphrased the request at intake;
the targeted fixed costs/cap and deliberate missing receipt were preserved and
independently checked. They do not prove exact original-prompt capture.

The separate bypass control refused to create/deliver the unverified file by
following connector/skill instructions. This is observed agent compliance, not
host interception. Available Muse interfaces still provide no completion veto;
the absolute claim that every Muse chat is technically unable to say done is
not established. Earlier advisory acceptance/failures remain history. All106
pre-upgrade retained files were verified unchanged after the new consumer tests.
