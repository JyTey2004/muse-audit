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
