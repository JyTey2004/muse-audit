# Independent backend correctness review

A separate reviewer agent read the implementation and ran its own temporary-store reproductions, without editing source. The review was targeted correctness analysis, not a production/security certification.

| Finding | Reproduction | Correction and independent retest |
|---|---|---|
| Agent-event provenance could yield false condition PASS | Agent-supplied event named tool.response satisfied a kind-only coverage check | Only collector-origin requests/responses with matching IDs, valid order and successful terminal result count. Error/foreign response cannot substitute. Retest: 5 UNKNOWN |
| Correct total on wrong item identity could pass | `unrelated:1500` passed arithmetic-only checks | Exact approved lunch/replacement/travel keys and amounts plus coherent total required. Retest: edit/add/cap FAIL |
| Completion ledger crash window | Provider and repair_results committed, completion event failed; retry omitted it | Result/completion ledger atomic in collector transaction; idempotent reconciliation after external provider write. Retest both interruption windows: one effect + one completion |
| Disk identity could mislabel old loaded code | Long-lived interpreter hashed changed disk while executing old imports | Startup project-source manifest; disk mismatch produces restart-required UNKNOWN and prior STALE. Retest confirmed |
| Repair action absent from allowed-action evidence | Original checker included only original tool.request | Include approved repair requests and matching completion/result records; incomplete repair coverage blocks PASS. Retest confirmed |
| Denials were not retained | Unreviewed contract/repair attempt only raised | Append-only contract decisions and authorized-run repair.denied events; never log/retrieve a foreign run. Retest confirmed |
| Source race at repair insertion | Change source after prepare validation, immediately before result insert | Source-hash CAS plus result-parent CAS inside one provider BEGIN IMMEDIATE; source/result read as one snapshot. Independent retest: stale write rejected, zero repair operation rows |

Final reviewer statement: no remaining reproducible false PASS or unsafe retry was found in these targeted scenarios. Required privacy remained UNKNOWN throughout; earlier findings were condition-level false passes, not whole-task certification. Final independent race retest also confirmed interrupted repair produces 5 UNKNOWN until exact recovery, then 4 PASS / 1 privacy UNKNOWN.

Tests cover these reproductions explicitly. Remaining boundaries: local principal is harness configuration, not authenticated identity; no real service/host/Muse verification; no adversarial filesystem or distributed transaction guarantee; incomplete natural-language/semantic coverage; advisory review only.

Final retention-only wrappers were sanity-reviewed: authorized preparation denials and provider write errors are persisted before reraising, without changing CAS or atomic completion. The reviewer identified the conservative pre-write-error lifecycle limitation; it is disclosed in the quickstart and validation report. The final unsupported-semantic branch was independently tested (1/1): unsupported checks remain UNKNOWN/unchecked through pending and source changes, without reopening earlier issues.
