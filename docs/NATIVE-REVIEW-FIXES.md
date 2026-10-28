# Independent Mac review fixes — 28 October 2026

## Preserved baseline and failed observations

Baseline cloud checkpoint remains recoverable: `d9e0a444d784ed36175dd56ca16777b9981c9385`. Its original archive still hashes to `0fc4f9f391e89e9d37d9fd1fe5dcac449d3280edccd8473f58b92a7294c387b5`, exactly matching the Mac download. The initial independent report is retained unchanged with the external validation records. The Mac sync excludes the generated observation JSON from Git, following AGENTS.md. It records all three failures: partial rejected intake, silently ignored minimum-word mapping, and a word count mislabeled as a total. Those observations are not replaced by the passing regressions.

The account's actual recipe is retained unchanged in `docs/MUSE-ACCOUNT-CONNECTOR-RECIPE.md`; it supersedes the earlier uncertainty about required OAuth in `NATIVE-CONNECTOR-PILOT.md`. No connector was registered and no credential was generated or transferred. The five ordinary-consumer automatic failures remain failures; guided replays remain separate evidence. Mac docs-only checkpoint `3cd0601` and its staged/unstaged work must be preserved during sync. This delta does not edit the existing `CONSUMER-VALIDATION.md`, `MUSE-TASKS.md`, `README-TASKFLOW.md`, or original Mac validation documents.

## 1. Atomic intake

Native intake validates every requirement and supported config plus all source IDs, filenames and duplicate IDs/names before creating an intake. It builds a complete task, frozen sources/checklist/request and pilot metadata in a fresh staging directory on the owner store's filesystem, then publishes with one atomic directory rename. Idempotency metadata lives inside that same committed task. Existing d9e0a44 idempotency indexes are still read, never replaced or removed. New invalid requests leave no visible task, source, index or quota entry. Cleanup owns only the new aborted staging directory; existing tasks, failures and snapshots are never removed.

Regressions cover duplicate ID only, duplicate filename only, both duplicates, invalid requirements, an injected failure before metadata publication, preservation of existing files byte-for-byte, and a subsequent successful intake. This is a single-process/worker pilot with owner locks, not a distributed transaction or WORM/power-loss guarantee. Earlier partial directories from the original defect are not silently deleted.

## 2. Exact checker config schemas

`muse_audit/taskflow/config_schemas.py` defines exact Draft 2020-12 schemas for all ten text/Markdown/JSON/CSV kinds, with additionalProperties:false. These schemas are enforced by the shared checker functions, including existing task reviews, not only by the HTTP wrapper. Unknown or invalid config fields return UNKNOWN instead of partial PASS. Native intake rejects unsupported mappings before publishing. Minimum-word checking remains unsupported: `{max_words:100,min_words:50}` cannot pass by checking only the maximum. Requirements expressed incompletely in natural language still need human review; no general interpretation-completeness claim is introduced.

The same catalog is returned by `taskflow_capabilities.config_schemas` in native HTTP MCP and existing taskflow stdio, and in OpenAPI `x-checker-config-schemas`. Intake's OpenAPI requirement schema discriminates kind/config via oneOf. Native XLSX/DOCX retain existing exact guards. Unknown kinds remain explicit unresolved cases. JSON Schema package version is included in runtime checker identity, and the new validator code is included in full source bindings. Old receipt identity therefore changes and needs a fresh explicit review; no historical receipt is rewritten.

Regressions reject extra fields for every text/Markdown/JSON/CSV kind, missing/wrong types, boolean-as-integer, duplicate columns and nonfinite caps. Real HTTP MCP calls compare the live capability catalog with OpenAPI, while review/recheck leave persistent bytes unchanged.

## 3. Compact view

The view receives actual frozen requirements. Numeric summaries dispatch on exact checker kind, never an arbitrary requirement ID: csv.total_cap may say Total; text/markdown.word_limit says Word count. Other numeric checks are not guessed into a budget. Failed, blocked and unknown rows include short reasons. The view retains interpreted-checklist/source-authenticity uncertainty and one inline receipt/date. Machine hashes, paths, protocol details and expanded report attachments stay behind details. A valid maximum-only `word_cap` case for “Hi there.” now says `Word count 2; maximum 100`; the unsupported minimum case does not produce a passing intake.

## Account-native route: confirmed setup recipe, still not registered

The supplied account recipe supports **api_key with bearer_header**. Existing server `Authorization: Bearer` authentication matches that placement. An OAuth issuer is not needed for this route. The server stores only an externally provisioned credential hash; the client credential must be created/connected through Muse's hosted secure credential link, held in its Secure Credentials Store and brokered via the bundled surrogate helper for registered HTTPS hosts. Never put the real credential in chat, helper files, CLI arguments, environment variables, URLs or logs. The literal tokens in offline tests are explicitly synthetic and are not live credentials.

After a separately reviewed live setup, use the recipe order: secure connection; harmless authenticated read; exact operation; scaffold only the already-connected connector; fetch the live tool list through all pages; review live schemas and the read/write classification; allowlist only those reviewed names. Authenticated helper requests must disable redirects. Unknown/new tools remain blocked until reviewed. No saved skill or include_in_prompt setting is proof of ordinary-request automatic invocation. Read/upload/receipt approvals remain the user's account settings and are not changed here.

Backend contract remains:
- Fixed HTTPS origin/443 (not yet assigned); `/openapi.json` authenticated read.
- REST writes: POST `/api/tasks` freezes selected sources/request/checklist, PUT `/api/tasks/{task_id}/versions/{version_id}` transfers raw bytes, POST `/api/tasks/{task_id}/receipts` computes and persists a fresh receipt. Exact headers/fields are in OpenAPI. Only selected task files are transferred; MCP takes returned task/version IDs, not file bodies.
- MCP `/mcp`: exactly taskflow_capabilities, taskflow_review, taskflow_recheck; all read-only. No intake/upload/receipt-save/repair mutation tool.
- REST historical receipt/result reads remain owner-authenticated. Uncertain writes are inspected by their existing idempotency/task/version identifiers before a deliberate retry; no new automatic retry loop is added.

OpenAPI advertises `api_key`/`bearer_header` setup metadata without a key or invented host; configured HTTPS hostnames are supplied only from reviewed launch configuration. The native integration owns technical identifiers; ordinary users need not enter them. This prepares the accepted route but is not native registration or consumer acceptance.

## Precise Work runtime hosting gap

The inspection found **no general-purpose inbound/public HTTPS publish operation, deployment identity binding, or persistent Python-service lifecycle control for this source workspace**. No `environment_status` tool/cloud-runtime skill was exposed. The environment inventory also reported its managed environment unavailable. CLI inspection found no Docker/Podman engine, deployment CLI or configured backend identity. Loopback sockets are supported and actually tested, but are not reachable from Muse's cloud.

The available app toolset does include **Sites and Higgsfield website publishing**. Those operate on their own managed website projects/runtimes; they do not expose a supported operation to publish this existing Python/SQLite taskflow service in place, and their project credentials are not this backend's deployment identity. Reusing the separate Workcheck Site or creating a substitute project was explicitly excluded. We did neither. This is consequently more than an absent URL/key in application config: this workspace has no demonstrated inbound/service control path for this backend. It is not a claim that all ChatGPT products can never host services.

A real pilot still needs a specifically selected/authorized host with persistent owner storage, HTTPS TLS ingress on443, and approved existing credential provisioning/brokered connection. Docker recipe remains unbuilt (no engine). No tunnel/key/public service, broader audience, paid hosting, terms, public connector/GitHub/license change or Muse model call was authorized/performed by these fixes.

## Mac synchronization and verification

Use the **incremental d9e0a44-to-final patch** if the first native pilot is already applied. Use the **cumulative 3ab1929-to-final patch** only on the matching reviewed Mac runtime. Inspect `git status` and patch paths, then `git apply --check`; preserve `3cd0601` docs-only work and both staged/unstaged files. Do not overlay the full source snapshot, reset a branch or merge unrelated histories. Both patches, per-file base/final SHA256 manifests, full final source hashes, recoverable cloud Git bundle and actual protocol observations are packaged. No Mac sync is claimed performed here.

Reproduce using the existing pinned Python3.12 environment:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s tests_backend -v
.venv/bin/python -m unittest discover -s tests_adapter -v
.venv/bin/python -m unittest discover -s tests_taskflow -v
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests_connector -v
.venv/bin/python tests_independent/independent_regressions.py --source . --output /tmp/stardive-independent-fixed.json
PYTHONPATH=. .venv/bin/python tests_connector/test_http_protocol.py --output /tmp/stardive-http-fixed-1
```

Use fresh output directories. No model calls are involved. The protocol exercise includes actual HTTP rejects without persistent changes, a valid nonbudget Markdown word-count task, exact schema discovery, unchanged store bytes during MCP, owner refusal, CSV FAIL/STALE and separately written receipts. Real HTTPS and ordinary native Muse acceptance remain untested; no automatic-acceptance claim follows from offline or loopback evidence.
