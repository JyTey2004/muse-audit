# Backend checkpoint validation — 27 October 2026

## Final source evidence

- Python 3.12.14 / Linux cloud Work executor; not a configured reusable Codex Cloud environment, Dot connection or Mac runtime.
- Isolated fresh virtualenv installed unchanged `requirements.txt` with unchanged Python 3.12 constraints. `pip check`: no broken requirements. Installed package versions retained in evidence; wheel distributions are not hash-locked.
- **54/54 original native-file tests passed** against final source. Original runtime/test/fixture/dependency blobs remain unchanged from `d93ada24baefcfde898ae8811dd4f9591ceb7b01`. Original runtime code hash verified: `c39a92e89634ba9a9a16d7820fd4d08dc8ad78da1b485a729d9db7cf423c62ea`.
- **27/27 new backend tests passed** against final implementation bytes. Coverage includes current-state mutation under identical claim, success-with-wrong-fulfillment, source/result gaps, unsupported checks, PENDING, explicit new contract approval, immutable originals, cross-run/principal IDs, event-chain corruption, same-label source mutation, stale loaded-code restart requirement, actual new-process replay, exact repair approvals, two crash windows, source-CAS race and unchanged unknowns/import authority.
- **38/38 Workcheck Node tests passed** in the separate unchanged Site source at `ea11a855a68313bafa6ede095984f894da3b2d25`. Counts are separate artifacts, not one combined test suite or proof of synchronization.

## Actual MCP protocol

Official Python MCP SDK **1.29.0**, real subprocess stdio, negotiated **2025-11-25**:
- initialize PASS; tools/list exposed all original four tools plus read-only review_run.
- tools/call review_run returned 2 FAIL / 2 PASS / 1 UNKNOWN for the seeded case.
- With the exact same claim, changed actual provider state returned 4 PASS / 1 UNKNOWN and prior assurance STALE.
- SHA-256 hashes of both SQLite DB files were unchanged by review calls.
- Cross-principal run and path-like run IDs rejected; original native budget audit still 6 PASS / 1 FAIL / 1 UNKNOWN.
- SDK/Pydantic forward-reference warning remains on stderr, retained in evidence. It did not corrupt protocol framing or fail the tested calls. No Muse host or real service was tested.

## Executed demo and persistence

`python -m muse_audit.task_backend.demo --output NEW_DIRECTORY` computes all outcomes, uses explicit scripted synthetic approvals and refuses overwriting prior output. It persists the original contract/approval, collector event chain, separate source/result DB versions, repair approvals and completion links. The demo retains failed/corrected/mutated/missing/pending receipts, imported-origin withholding, reset/new run and a fresh supported-cap contract. Current implementation manifest is exported with the evidence.

Initial: 2 FAIL / 2 PASS / 1 UNKNOWN. Repaired: 4 PASS / 1 required privacy UNKNOWN. Same-label result mutation: prior STALE, current 2 FAIL / 2 PASS / 1 UNKNOWN. Missing read-back: 4 UNKNOWN / 1 allowed-actions PASS. New approved 1,400-cent cap: 3 PASS / 1 FAIL / 1 UNKNOWN after repair. Known pending operation: 4 PENDING / 1 privacy UNKNOWN. No whole-task assurance is issued.

Actual separate-process regression reopens a repaired store and confirms identical conditions, FRESH previous bindings and required privacy UNKNOWN. Repeated and interrupted post-write repairs reconcile once; no original rows are changed/deleted. Imports occupy a separate untrusted table and cannot create observed events, provider state or approved contracts.

Native two-job demo rerun: home-office repair remains 6 PASS / 1 FAIL / 1 UNKNOWN (78,000 against unchanged protected 75,000 cap). DOCX repair remains 3 PASS / 1 UNKNOWN. These tests do not imply arbitrary native-format or semantic coverage.

## Independent review

See BACKEND-INDEPENDENT-REVIEW.md. Separate reviewer reproduced and independently retested the provenance, identity, wrong-item, approval-retention, crash-recovery and source-race corrections. It also ran the final unsupported-semantic lifecycle regression independently. No remaining reproducible false PASS/unsafe retry was found in the targeted scenarios; this is not a production safety statement.

Known limitation disclosed after review: a confirmed pre-write error can leave the run UNKNOWN and require reset/new run; general retry recovery is not claimed. No continuous monitor, authenticated multi-tenant service, external side-effect enforcement, real provider/Muse validation, paid model calls, public license/release or distribution authenticity established.
