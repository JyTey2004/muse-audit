# Backend-first local testing checkpoint

An **agent-callable task acceptance engine**, not a memory/log-summary service. `review_run(run_id, claimed_outcome)` retrieves the original approved contract, resolves a locally authorized run and **executes deterministic conditions against current separately stored provider state**. The claim is data and cannot establish PASS. No new receipt UI, hosting, tunnel or model integration was built.

This extends the separate Python native-file package at `d93ada24baefcfde898ae8811dd4f9591ceb7b01`. The existing Workcheck Site/JS project at `ea11a855a68313bafa6ede095984f894da3b2d25` is unchanged. Its expense-tracker case and binding principles were ported to Python; no shared live engine, store or automatic sync is claimed. Four original native-file tools remain unchanged; the new entrypoint exposes those plus read-only `review_run`.

## Fresh folder, fresh environment

Extract the `source/` folder from the supplied checkpoint package into a **new** directory on your Mac. Do not overlay the existing Mac checkout or its staged/unstaged planning files.

```sh
cd /path/to/extracted/source
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -c constraints-python312.txt
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s tests_backend -v
.venv/bin/python tests/test_protocol.py
.venv/bin/python tests_backend/test_protocol_backend.py
.venv/bin/python -m muse_audit.task_backend.demo --output /tmp/stardive-task-demo-new-1
```

Use a **new** output directory. The demo refuses overwrite. Existing native XLSX/DOCX fixtures remain byte-for-byte unchanged, including the 78,000 total against the protected 75,000 cap. They are negative controls, not failures to hide. Do not replace the original `run_mcp.py` configuration: the backend has a distinct entrypoint below.

## Read-only MCP invocation

After creating a demo store, use a local MCP host that can launch stdio, or run the included official-SDK protocol script. This is a developer/local host path, **not consumer Muse validation**.

```sh
.venv/bin/python -m muse_audit.task_backend.server \
  --workspace /absolute/path/to/source/examples \
  --store /tmp/stardive-task-demo-new-1/store \
  --principal local-demo
```

The store must already exist. `--principal` is a trusted local launch scope, **not a user authentication credential**; do not expose this stdio process as a multi-tenant service. The caller cannot choose another principal through the tool arguments. Use the `run_id` printed in `summary.json`:

```json
{"name":"review_run","arguments":{"run_id":"RUN_ID_FROM_SUMMARY","claimed_outcome":"Done. Your expense tracker is correct."}}
```

Tools: `audit_capabilities`, `audit_job`, `prepare_repair`, `recheck_job`, `review_run`. All read-only. No approval/write tool was added. MCP review does not persist reviews, observations or claims and does not modify either database; it returns fresh execution evidence. Current state can change returned values/timestamps, so it is not advertised as output-idempotent.

## Interactive contract and repair CLI

Every CLI command below operates only on the explicitly selected **synthetic local** store. Do not use real user data.

```sh
.venv/bin/python -m muse_audit.task_backend.cli --store /tmp/stardive-user-test-store template --max-total-cents 2000 > /tmp/task-contract.json
.venv/bin/python -m muse_audit.task_backend.cli --store /tmp/stardive-user-test-store register --contract /tmp/task-contract.json
# Review the contract; use the exact contract_id and contract_hash returned above.
.venv/bin/python -m muse_audit.task_backend.cli --store /tmp/stardive-user-test-store approve-contract --contract-id CONTRACT_ID --digest CONTRACT_HASH --approve-reviewed-contract
.venv/bin/python -m muse_audit.task_backend.cli --store /tmp/stardive-user-test-store run --contract-id CONTRACT_ID
.venv/bin/python -m muse_audit.task_backend.cli --store /tmp/stardive-user-test-store review --run-id RUN_ID --claim 'Done' --record-receipt
.venv/bin/python -m muse_audit.task_backend.cli --store /tmp/stardive-user-test-store plan --run-id RUN_ID --output /tmp/review-plan-new.json
# Read this exact plan. Copy its digest; applying creates a new result version.
.venv/bin/python -m muse_audit.task_backend.cli --store /tmp/stardive-user-test-store apply --plan /tmp/review-plan-new.json --approved-digest PLAN_DIGEST --approve-reviewed-plan
.venv/bin/python -m muse_audit.task_backend.cli --store /tmp/stardive-user-test-store review --run-id RUN_ID --record-receipt
```

Do not substitute prose or an agent-written approval. The plan is re-derived and matched against the original contract, selected source, current provider parent/content, observed execution and full implementation. Source hash and result parent are checked again **inside the provider write transaction**. Exact retries recover one effect without overwriting the original; both provider-write and collector-completion crash windows are tested. Concurrent writers are not a distributed production transaction service; the two local SQLite databases are reconciled through a unique operation key and atomic completion ledger.

Supported live edit: create a **new** template/contract with cap `1400`, register and approve it, then run and repair that new run. Its repaired 1,500 total fails the 1,400 cap. It does not silently replace the old obligation or raise a protected cap. A draft/new contract cannot execute with an earlier contract's approval. The privacy condition is always required UNKNOWN.

Additional disclosed controls (run `--help`): `run --pending`, `mutate-synthetic --kind source|result --json FILE`, `mutate-synthetic --withhold`, `reset`, `export-receipt`, `import-receipt`. Mutation controls change actual local synthetic versions, not stored verdicts; labels can stay unchanged while bytes change. Reset creates a new run using the same immutable approved contract and retains old runs. Import only stores **untrusted assertions** in a separate table; it never populates contracts/events/provider state or produces observed PASS.

## What the demo genuinely does

- Persists explicit requirements, cap, allowed actions, forbidden changes and an exact approval before execution.
- Actual synthetic runner arithmetic has a seeded edit-double-count fault. Captured response says success; separate read-back shows 2,500 instead of 1,500.
- Initial outcome: **2 FAIL / 2 PASS / 1 UNKNOWN**. Five original conditions: edit total, protected add behavior, cap, required privacy, allowed actions.
- Reviewed copy repair and full check: **4 PASS / 1 UNKNOWN**; privacy UNKNOWN blocks task completion.
- Actual result-content mutation with the same label makes prior assurance STALE and changes current verdicts; missing read-back leaves **4 UNKNOWN / 1 PASS** (the only PASS is recorded allowed actions).
- Known unfinished operation: **4 PENDING / 1 privacy UNKNOWN**. An acknowledgement alone cannot pass.
- New supported, freshly approved 1,400-cent cap: **3 PASS / 1 FAIL / 1 UNKNOWN** after arithmetic repair.

The demo's approvals are explicitly **scripted synthetic test approvals**, not human acceptance. It neither sends email nor purchases/books/pays anything. No real providers, Muse calls, credentials or model spend.

## Persistence, identity and limits

`runs.sqlite3`: append-only contracts, approvals/decisions, runs, ordered/hash-chained collector events, locally recorded receipts, repair approvals/results and untrusted imports. `synthetic-provider.sqlite3`: separate immutable source/result versions, content/availability/parent bindings, unique operation keys. Ordinary updates/deletes are rejected. Hashes detect differences relative to retained records; they are not signatures or authenticity/completeness proof against an actor who controls the whole local filesystem.

Each receipt includes the **complete project Python source manifest**, dependency declarations, Python/SQLite and selected installed-package versions, configuration scope, original contract/approval hash, ordered event bindings and current source/result snapshot pins. All package `.py` modules (including parser/approval, store, runner, verifier, MCP and CLI) are included, rather than selected function strings. Dependency distribution bytes are not signed/hash-locked. A source change after import requires restart and produces UNKNOWN rather than pinning fresh PASS to code that was not loaded. After restart, changed source under the same label makes prior stored assurance STALE. No continuous observer is implied: freshness is compared **when review observes a snapshot**. Source/result are read in one SQLite snapshot; the immutable collector log is independently validated.

Review is advisory. No completion-enforcing host gate is implemented. MCP cannot see uninstrumented host tools or hidden Muse logs. Conditions cover only explicit supported arithmetic/state/source-key checks. Natural-language requirement translation, evidence completeness beyond the controlled runner, semantic/privacy verification, real-service authenticity, hostile-process isolation and general task coverage remain open.

Source manifest equality is platform-dependent through runtime/package versions: a Linux receipt may correctly become stale on a Mac until fresh local review. This is not an automatic cross-device sync mechanism. Consumer Muse access/transport remains unverified and access-gated; public GitHub/license decisions remain separate. No remote repository push was made.

A confirmed **pre-write** repair failure is retained as `repair.error` and may leave that run UNKNOWN because no completion exists for that request. Use a reset/new approved run for that failure class; automatic retry of every pre-write failure is not implemented. The tested idempotent recovery guarantee covers interruption **after** the provider effect and interruption within the collector completion transaction. No originals are overwritten in either case.
