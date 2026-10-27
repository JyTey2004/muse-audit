# Baseline assurance acceptance report

Scope: supervised, low-risk, offline testing of the controlled synthetic expense task. Reviewed starting revision: `93eede95f8f85e61bf911754bfcbc9aaf7aa273c`. This hardening checkpoint is local and has not been pushed or synchronized back into the cloud package.

**Justified claim:** at the recorded review time, this checker executed the identified supported comparisons against the approved contract, validated captured runner records and selected source/result versions. Results apply to that captured scope and implementation. They do not establish general correctness, privacy, complete host history, real-provider authenticity or insurance coverage.

## Requirement-to-evidence map

| Requirement | Evidence and executed comparison | Who controls it / limit |
|---|---|---|
| Edited expense total | Original approved integer-cent expectation; current result item identities, values and recomputed sum; exact total equality | Synthetic provider SQLite state, read separately from success acknowledgements; same local operator controls both stores |
| Protected add behavior | Captured synthetic add-probe items, recomputed sum and original expected total | An assertion over the stored controlled-run probe; no arbitrary application/browser execution or real provider is verified |
| Budget cap | Coherent current result versus the original approved cap | Explicit contract selected/approved through local CLI; changing a cap requires a newly approved contract |
| Allowed actions | Complete approved runner recipe, request/response IDs, event order, source/result read-back versions, compound add/edit/read operations and approved repair records | Instrumented local collector only; no visibility into uninstrumented host tools or hidden Muse logs |
| Expense privacy | No adequate authentication/access-control checker exists | Always required UNKNOWN; neither arithmetic repair nor a model opinion proves privacy |

Shared preconditions apply to the supported comparisons: unavailable source evidence abstains; a current source snapshot different from the approved typed snapshot reports a source-precondition FAIL. That does not assert that every arithmetic value is independently wrong; read the per-condition explanation.

The contract/approval, collector, provider and verifier run within a trusted local environment. Their provenance labels distinguish roles, not independent organizations or cryptographic identities. Hashes and append-only API rules detect certain inconsistencies relative to retained records; an actor controlling all code/files can forge the entire environment. Imports remain unverified assertions.

## Acceptance gate

Before any supported condition can PASS, the captured evidence must fit this runner's known recipe: one matching approval before one start, complete typed request/scope, selected source read-back, matching successful terminal response, result read-back and one finish in the required order. Duplicate, missing, wrong-run, reordered or unsupported records withhold condition passes. Repair records require exact approved plan/run/owner/result links and a completed original run.

A known open request with no terminal response is PENDING. A missing completion after a terminal response is UNKNOWN, not assumed still running. Unsupported privacy/semantic conditions remain UNKNOWN in every lifecycle. Missing evidence or a corrupt/hash-invalid store provides no assurance; some corruption classes refuse review with an error rather than returning a receipt.

Overall success requires every original required condition to have an executed PASS. Required FAIL, UNKNOWN or PENDING prevents it. This fixture's required privacy UNKNOWN means whole-task completion remains **UNRESOLVED**, including after a successful arithmetic repair. A prior STALE receipt cannot be reused as current proof; a new review recomputes conditions and records current bindings. State/source/implementation changes are noticed on review, not by continuous monitoring.

## Reproduced defects and focused fixes

| Before this checkpoint | Fix and regression evidence |
|---|---|
| Compound runner performed add/probe operations although add permission was absent; action condition could PASS | Require approved add/edit/read permissions before a run/effect; include compound operations and observed reads in the action comparison |
| Truncated request or absent read-back records could coexist with 4 condition PASS results | Validate captured recipe, typed request fields, approval and read-back scope before establishing execution coverage |
| Duplicate start/finish or reordered read-back records could leave condition passes | Require a unique coherent lifecycle; ambiguous or incomplete records abstain |
| Equal-valued JSON floats could compare equal to approved integer source values | Compare canonical typed JSON for source and request bindings |
| Orphan/inconsistent repair records could be ignored | Validate approval decision/run/owner/plan and completion linkage; inconsistent records withhold assurance |

These were condition-level overclaims; the required privacy UNKNOWN already prevented whole-task success. The fixes strengthen the supported evidence gate without creating a new platform or authentication system.

## Verification evidence

`tests_backend/test_assurance_gate.py` adds 14 focused adversarial tests. Existing backend tests retain contradictory success claims, wrong-run/principal IDs, altered hash chains, fresh contract approval, stale sources and same-label implementation changes, exact repair approval, two interruption/retry windows, and UNKNOWN preservation through repair/reset/import. All original native XLSX/DOCX tests remain applicable.

Final local checks passed: **54 native tests and 41 backend tests** (including the 14 new cases), both real MCP protocol scripts, both synthetic demos, and pip check. Effective project source digest: `f491a54859bdd7d5ef01f5351408a5a3135869a7b27f8736d9c87c199b1351a2`.

Commands, exit codes, counts, implementation-file hashes and demo results are retained in ignored `.local/assurance-baseline-20261027/`. Use its `verification.json` and `source-manifest.json` with this Git revision. Protocol smoke is an actual official-SDK subprocess initialize/list/call test; it is not a Claude or consumer Muse host integration. Workcheck remains a separate artifact and is not retested or modified here.

## Manual supervised test

From the repository root, use a new output path:

```sh
.venv/bin/python -m muse_audit.task_backend.demo --output .local/baseline-user-test-1
```

Inspect `initial.json` (2 FAIL / 2 PASS / 1 UNKNOWN), `repaired.json` (4 PASS / 1 privacy UNKNOWN), `changed-state.json` (prior STALE), `missing.json` (4 UNKNOWN / 1 PASS), and `new-supported-cap.json` (the tighter approved cap still FAILS). The demo uses disclosed scripted synthetic approvals; it is not human acceptance.

Then follow BACKEND-QUICKSTART.md to register/review an explicit contract and a repair plan yourself. Withhold the approval flag and check that no provider effect occurs; approve only the exact reviewed plan, then recheck. Use synthetic, disposable copies only. Do not reuse an existing output folder or mistake a subprocess protocol result for a live host result.

## Remaining limits

Ready for low-risk supervised offline testing of this bounded synthetic workflow, with all recorded final checks passing. No population error rate or real-world accuracy estimate was measured. Because the standard fixture always retains required privacy UNKNOWN, its lack of whole-task green outcomes is not itself a calibrated false-assurance-rate result. Consumer Muse access is waitlisted. Real-provider authenticity, authenticated multi-user access, general natural-language translation, arbitrary semantic/privacy checks and trustworthy coverage outside the instrumented runner are unsupported. Review is advisory outside an enforcing harness. Some pre-write repair failures require reset/new run; general distributed recovery is not implemented. No production accuracy, zero-error, tamper-proof, financial/insurance or deployment claim is made.
