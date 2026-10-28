# Claude Code expense task: two-phase local handoff

This is an **additional adapter in the existing Python repository**, not a replacement for the native file tools, synthetic backend, or Workcheck Site. It does not edit `muse_audit/task_backend/review.py` or `runner.py`. Mac planning/staging and the remote GitHub repository are untouched. The Mac now has preservation checkpoint `a247171553c22e438f21cd67dec1712ec1c1b37f` on base `93eede95f8f85e61bf911754bfcbc9aaf7aa273c`. It reports 54 native + 41 backend tests, independently of this cloud adapter validation. Its five protected paths are `muse_audit/task_backend/review.py`, `muse_audit/task_backend/runner.py`, `tests_backend/test_assurance_gate.py`, `docs/BASELINE-ASSURANCE.md`, `BACKEND-QUICKSTART.md`; none are in this integration delta. Do not overlay the cloud full-source snapshot onto those newer Mac files. The Mac assurance patch is not available here and is not claimed reconciled. Its reported source digest is `f491a54859bdd7d5ef01f5351408a5a3135869a7b27f8736d9c87c199b1351a2`; patch SHA-256 `11f21ebe13bb090fa95b84c1d65dfa6a5b47bcc51bb640316d2117a80bcc0bf2`. Preserve staged AND unstaged planning documents. The earlier Mac base was `93eede9` (ported original cloud `48cf72d` onto upstream `d93ada2`); this cloud change is a path-scoped delta from `48cf72d`, not a request to merge unrelated Git histories.

## Transfer into the dedicated Mac integration checkout

Download/extract the accompanying package **outside** any working tree. Do not overlay an active checkout. The coordinating Mac chat can materialize the Library file into a separate folder using its supported file flow. This cloud runtime has no Mac shell/file transfer connector: the archive is ready for transfer, but a Mac sync or real Claude run has not been performed here.

In the isolated `muse-audit-claude-integration` checkout, inspect `git status --short` first. If there are unrelated modifications, preserve them and stop rather than stashing/resetting/overwriting them. Inspect `BASE-TO-FINAL.patch` and `CHANGED-FILES-SHA256.json` from the package. Then:

```bash
git apply --check /absolute/extracted/package/BASE-TO-FINAL.patch
git apply /absolute/extracted/package/BASE-TO-FINAL.patch
```

This adds `muse_audit/claude_adapter/`, `tests_adapter/`, this document, and changes only the offline CI workflow. It does not touch the concurrently edited original review/runner files, original native tests/fixtures, dependencies, launchers or planning documents. Do not apply a full source overlay. The package's `source/` is also a standalone clean copy; `cloud-history.bundle` recovers the cloud history independently. A bundle is not a claim of upstream ancestry.

## Environment and offline checks

Mac reported: Claude Code 2.1.305 authenticated, Node 22.22.3, Python 3.12 with pinned dependencies. Cloud validation uses Python 3.12 / Node 24.22.1. No credentials are transferred. Use the Mac's existing authenticated subscription; no cloud API key is needed. These model-driven commands invoke Claude and may consume that account's allowance. No account/billing setup is included.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -c constraints-python312.txt
.venv/bin/python -m pip check
node --version
claude --version
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s tests_backend -v
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests_adapter -v
PYTHONPATH=. .venv/bin/python tests_adapter/test_protocol_adapter.py
PYTHONPATH=. .venv/bin/python tests_adapter/demo.py --output /tmp/stardive-offline-adapter-1
```

The adapter offline collector streams are explicitly **test doubles**. The fixed Node code and the official SDK MCP subprocess really execute. They are not Claude-host integration proof. Do not re-label the offline stream as a live Claude session. CI now runs native + backend + adapter suites/protocols and demos, without model calls. Workflow changes are packaged but not pushed or run on GitHub.

## Real two-phase Claude run (Mac only)

Choose **new**, dedicated absolute directories outside the source tree. The generated app directory must be absent before `prepare`. The evidence store and app directory must not contain each other. Replace the example paths as needed; no existing files are overwritten.

```bash
.venv/bin/python -m muse_audit.claude_adapter.cli \
  --store /tmp/stardive-claude-evidence-1 --principal jiaye \
  prepare --workspace /tmp/stardive-expense-app-1
```

Read the printed original contract, run ID and `contract_hash`. This contract is the user's **real app** task, not the synthetic backend's edited-total fixture: Lunch 1000 + Travel 500 = 1500; editing Lunch to 1500 while retaining Travel gives 2000; deleting Travel gives 1500. It checks stable IDs/labels, reload and invalid amount nonmutation. String and safe-integer IDs are accepted.

Explicitly approve the exact printed hash (placeholders below must be replaced):

```bash
.venv/bin/python -m muse_audit.claude_adapter.cli \
  --store /tmp/stardive-claude-evidence-1 --principal jiaye \
  approve RUN_ID --contract-sha256 CONTRACT_HASH
```

Phase 1 launches Claude with Read/Write/Edit only, no MCP servers, restricted mode, explicit settings disabling hooks, fresh session, bounded turns and a 600-second timeout. The collector finalizes stdout/stderr, nested tool events and original artifact copies before phase 2. A failed or interrupted execution cannot become observed success through imported JSON.

```bash
.venv/bin/python -m muse_audit.claude_adapter.cli \
  --store /tmp/stardive-claude-evidence-1 --principal jiaye build RUN_ID
```

Inspect the generated files if desired, then phase 2 launches a **different restricted Claude session** with no built-in tools and one read-only MCP tool. It must actually call `mcp__stardive__review_run` with the exact run ID and claim. There are no mutation tools, Stop hooks, hidden completion loops or retries. An unsupported host stream/result fails closed and is retained for diagnosis.

```bash
.venv/bin/python -m muse_audit.claude_adapter.cli \
  --store /tmp/stardive-claude-evidence-1 --principal jiaye review RUN_ID
```

Outputs in `/tmp/stardive-claude-evidence-1/RUN_ID/`:

- `build-stream.jsonl`, `build-stderr.txt`, `build-artifacts/` original generated bytes.
- `build-mcp.json`, `review-mcp.json` exact local launch configuration.
- `review-stream.jsonl`, `review-stderr.txt` including actual MCP tool_use/tool_result.
- `completion-receipt.json` fresh independently recomputed receipt plus bound host review observation.

The SQLite store persists approvals, original contract, host evidence and recorded receipts across processes. MCP review does not change its bytes. Moving/copying a store root is refused; make a fresh locally approved run instead. The principal is a launch-scoped local selector, **not authentication**.

An explicit repeat of the `review` command starts another Claude session. It retains the first review files and receipt, and writes the new attempt under `RUN_ID/review-attempts/SESSION_ID/`. The returned `claude_review_observation.evidence_directory` identifies the attempt containing that completion receipt. There are no automatic model retries.

Freshness also binds the currently available build stream, stderr and launch configuration. Withholding or changing those files makes prior evidence STALE and removes supported PASS results. Changes during verification cause the current check to abstain. Restoring the original files does not erase the retained failed or missing-evidence observations.

To obtain another current check without Claude (no model call):

```bash
.venv/bin/python -m muse_audit.claude_adapter.cli \
  --store /tmp/stardive-claude-evidence-1 --principal jiaye inspect RUN_ID
```

This directly executes the independent checker again; it is not a second Claude review. Current changed app bytes change outcomes and stale a recorded receipt once observed. Source/checker changes require process restart and stale old bindings even under unchanged labels. Original approved contract cannot be replaced in a run; changed requirements require a new prepared run and approval. Unsupported changed obligations abstain.

## What the receipt can establish

The fixed parent Node assertions execute calls against `createExpenseStore` in the generated self-contained `app.mjs`. They check exact arithmetic, Travel retention, identity/label, delete, key-specific persistence and invalid amounts with no state/storage changes. The target runs separately in a worker VM without Node globals, module imports/dynamic imports or string evaluation. Assertions/reporting stay outside the target context; stdout cannot supply a verdict. Python enforces an outer 10-second verifier timeout and before/after artifact + implementation identity checks. Missing files, invalid modules, changed evidence, failed/pending execution, unsupported checks or untrusted imports cannot certify.

**Browser UI is required UNKNOWN** until actually observed separately; no browser-evidence ingestion is provided here. File presence is a narrow separate condition and does not establish UI functionality. **Privacy/authentication/security remain required UNKNOWN.** Even four supported PASS conditions yield UNRESOLVED, not a whole-task certificate. Review is advisory; no tested host completion gate is claimed.

## Trust and practical limits

This executes **trusted local generated code only**. Node VM/worker isolation is not an adversarial-code security boundary. Do not point it at untrusted downloaded code. It has no hostile-code sandbox, signatures or general semantic coverage. The bounded loader rejects external imports; multi-module app logic is unsupported. Browser files are delivered but not executed by this checker. Node experimental VM warnings are retained on stderr.

The host collector observes only its own spawned process. It cannot see other Claude/Muse calls. It checks actual nested `assistant.message.content` tool_use and `user.message.content` tool_result IDs/order/session, terminal status, return code and captured file paths. Path validation detects observed violations after the host call; it is not an OS filesystem sandbox. Claude `--restricted` confines supported file tools, but managed host settings/authentication remain trusted. No claim of a real Mac run is made until its retained evidence is reviewed. A local user with filesystem/process access can fabricate the database or code; hashes are byte bindings, not proof of origin.

The manifest binds **all** project Python and adapter JavaScript, scripts, CI configuration, dependency declarations, installed dependency versions and Python/Node/SQLite versions. Build argv/version/config and stream digests are persisted; review argv/config and observation are bound in the exported receipt. Installed dependency distribution bytes, Node/Claude binaries, OS/kernel and managed Claude settings are not signed/attested or fully content-hashed. Restarts/reviews are explicit; no continuous observer exists. An interrupted build remains pending/failed and requires a new run; failed review evidence remains available and does not create a receipt. No endless automatic retry.

No GitHub push, deployment/tunnel, license decision, consumer Muse integration, cloud model calls or existing Site change is included.

Official setup references checked 27 October 2026: https://code.claude.com/docs/en/cli-reference , https://code.claude.com/docs/en/headless , https://code.claude.com/docs/en/mcp . Node limitation: https://nodejs.org/docs/latest-v22.x/api/vm.html . Flags are checked against current official docs; compatibility and returned content on the reported Mac 2.1.305 remain a **real-host validation step**, not an offline-test claim.
