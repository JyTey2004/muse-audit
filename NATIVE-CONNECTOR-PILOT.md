# Stardive private native connector pilot — 28 October 2026

**29 October deployment and acceptance update:** the same cloud backend is now
hosted on Stardive's existing infrastructure, registered in Muse, and tested with
two fresh ordinary requests and independent receipt replay. Read
[current native acceptance](docs/MUSE-NATIVE-ACCEPTANCE.md) first. The remaining
sections preserve the earlier source-build observations and their limitations.

Historical reviewed cloud checkpoint: `550df9842273081bd14b21248ffa70b44d6c8d9d`.
The Mac independently passed **196 tests, both sets of 14 adversarial checks,
all four protocol paths and three offline demos**. See
[review fixes](docs/NATIVE-REVIEW-FIXES.md) for atomic intake, exact config schemas
and the corrected nonbudget summary. The server is a synthetic private pilot;
no native connector or live HTTPS service is registered. Hosting is a capability
gap in the current Work executor, not merely an unset URL.

## Historical source state and preserved history

This extends the **same Muse Audit Python backend**. Reviewed Mac archive SHA256 `073e7daa8c6f61ac452b2c8dd14603224a5c112319badded3fafbe0c510f453f`, reported runtime `3ab1929163c5875277cb1464f9e0bb74af36423e`, was verified against all 91 manifest entries and reconciled on cloud branch `cloud-native-pilot-3ab1929`, commit `30c72a6`. No unrelated Git histories were merged. `docs/NATIVE-SOURCE-RECONCILIATION.json` records exact incoming pins. The cumulative source preserves a247171/e082a02 hardening, original fixtures, existing stdio tools and taskflow checkers. Native changes live in `muse_audit/native_connector/` and do not replace old entrypoints. The attached separately authored regression script is retained unchanged under `tests_independent/`.

**At this historical source-only checkpoint, consumer automatic acceptance was FAIL / not achieved.** Five ordinary Muse trials ignored or rejected saved skills, including the concise variant; automatic inclusion was turned off. Guided task-local MCP use for CSV (3 PASS/1 UNKNOWN) and Markdown (6 PASS/1 UNKNOWN) was observed and independently replayed, both UNRESOLVED. Neither guided use nor this generated endpoint/schema/config demonstrates automatic native acceptance. The supplied ZIP has runtime/docs, not the ignored Mac evidence directories: those remain on Mac and are not claimed transferred, deleted or rewritten. Existing ignored cloud evidence and the separate owner-private Workcheck Site are untouched.

## Original Work executor capability boundary — 28 October

Observed cloud Work executor: Linux x86_64, Python 3.12.14, Node 24.22.1, existing MCP SDK 1.29.0 / Starlette 1.6.0 / Uvicorn 0.52.1 / HTTPX 0.28.1. No `environment_status` tool or cloud-environment runtime skill is exposed in the current complete skill/tool inventory. No deployment CLI, Docker/Podman engine, inbound HTTPS binding, deployed endpoint, backend credential binding or usable hosting identity was identified. Environment variable names were inspected without printing values. Network-secret placeholders or unrelated connected-app credentials are not assumed to be an inbound service identity. No other cloud project or Site is substituted.

The implementation can be run on loopback and packaged for a compatible Python host. **It is not a live Muse-reachable service.** Missing capabilities: a reviewed persistent host, a Muse-reachable HTTPS origin/TLS ingress, a persistent owner store and an existing safely provisioned credential/secure Muse credential exchange. Docker recipe is provided but cannot be built here (no engine); base image digest must be selected/reviewed before production use. No hosting account, live credential, tunnel, terms acceptance, directory submission, billing change or public endpoint was created.

## Actual Muse interface, not an invented MCP registration screen

Official Meta Help says to ask Muse to create a Custom Connector for a service absent from its connector list; setup can retrieve API information and uses Secure Credentials Store:
https://www.meta.com/help/superintelligence/1687253048996149/

It does **not** establish an arbitrary remote-MCP-URL settings field or this account's exact authentication/transport acceptance. The Mac observation was a built-in connector list without such a field. Third-party recipes conflict, so they are not the authority here. This pilot offers both authenticated OpenAPI/REST and standards-based Streamable HTTP MCP for the coordinating operator to test through the actual chat-created custom connector route. It implements **bearer authentication, not an OAuth authorization server**. If the actual account only accepts OAuth, that is a further integration requirement, not evidence this bearer pilot registered successfully. Official directory guidelines are a separate submission/review path: https://platform.muse.ai/docs . No submission is performed.

## API boundary and ordinary-use flow

Every route requires configured bearer auth; no query-string tokens. Credentials map to configured principals and least-privilege scopes. Callers cannot choose principals, roots, arbitrary paths, commands or URLs. Owners have separate taskflow stores. Failed auth returns 401; missing scope 403; malformed/foreign inputs generic 400; stale/no-overwrite/idempotency conflicts 409; oversized body 413; rate limit 429. Unknown task IDs do not reveal other owners. The origin/host checks reject unconfigured browser origins/hosts. Tokens and input bodies are not logged by the server. Run one application worker; it uses in-process owner locks, not a distributed-write design.

`GET /openapi.json` is the authenticated setup specification. These are **writes**, explicitly separate from MCP:

1. `POST /api/tasks` (`intake` scope), with Idempotency-Key: original request, interpreted requirements, bounded base64 selected sources, artifact filename/kind, `synthetic:true`. No generated artifact is accepted in intake. It freezes inputs before generation. Returning the same key/body retrieves the original; a changed contract with the same key is refused. Changed requirements need a fresh task/key. Only selected synthetic pilot data is authorized; the synthetic flag is a caller declaration, not a personal-data detector.
2. `PUT /api/tasks/{task_id}/versions/{version_id}` (`artifact` scope), raw octet-stream and If-Match with original frozen hash. Copies exact frozen inputs into a version-specific evaluation workspace. Complete versions are staged then atomically published. Same version/same bytes is idempotent; same version/different bytes is refused. New versions preserve earlier failed bytes and receipts. This is artifact storage, not generated truth or a tool-success assertion.
3. `POST /api/tasks/{task_id}/receipts` (`receipt` scope), body only `{"version_id":"…"}`: recomputes current comparisons, validates snapshot binding and writes a new receipt/result snapshot. Caller verdict JSON cannot be persisted as observed proof. Returns a compact view and authenticated result/details references, without embedding the full machine receipt. Receipt persistence is **not** described as a read.

Read routes inspect original task, historic receipt and exact delivered snapshot. Historic receipt retrieval is not a current recheck. Uploaded bytes/checklists/source content are caller-supplied, not independent evidence of source authenticity or completeness. Deterministic check outputs are computed by the backend from current bytes.

`POST /mcp` (Streamable HTTP; `review` scope) exposes exactly three **read-only** tools: `taskflow_capabilities`, `taskflow_review(task_id,version_id)`, `taskflow_recheck(task_id,version_id,prior_receipt)`. No creation, upload, receipt save, repair, shell or URL tool exists in MCP. It invokes the existing taskflow engine with `write_outputs=False`. Tests compare every persistent store file before/after MCP calls. Prior JSON is untrusted: recheck recomputes outcomes and detects content/config/checker changes as STALE; modified old outcomes are INVALID_EVIDENCE. Same-process implementation change blocks acceptance until restart.

The native integration owns technical IDs internally. After one reviewed setup, ordinary users should say, for example, “Make a CSV for the picnic items from these supplied quotes, keep the total below 65.” The integration freezes that actual request/checklist/sources, lets Muse generate, uploads the result, calls review, separately saves a fresh receipt and returns the useful result plus a small checked-value table and one inline receipt/date. No task IDs or setup language should be asked of the ordinary user. **This flow is a prepared contract; only a fresh observed ordinary Muse invocation proves it happens automatically.** If Muse does not invoke the connector, report FAIL rather than count the saved instructions or prose as success.

## Scope and trust

Existing text/Markdown/JSON/CSV and native XLSX/DOCX checkers run, preserving archive guards, typed comparisons, Decimal totals, original requirements and UNKNOWN claims. There is no fixed budget in the connector. Model-interpreted checklist completeness, source transcription/authenticity, semantics, privacy, provider state, sent/delivered claims and browser behavior cannot be certified. Missing or changed required evidence blocks; model agreement or successful upload never passes a task. This is advisory assurance, not a completion-enforcement gate or insurance.

All project Python/JavaScript, scripts, deployment configuration and workflow bytes are bound, with dependency declarations and runtime package versions. Launch configuration is bound without returning raw credential hashes. Binding detects byte changes, not source authenticity. Installed distribution/binary/OS identity is not signed/attested. No continuous observer exists. Current reviews notice changes when invoked. The local filesystem and single application process are trusted; this is not a hostile-file sandbox or a multi-tenant production security certification. Synthetic tests do not prove live service authenticity.

Immutable history is implemented as fresh task/version/receipt directories and no-overwrite APIs, not WORM storage against an OS administrator. Data counts and request sizes are bounded. Live retention, deletion/revocation operations, encryption/backup responsibility, TLS, credential rotation and monitoring require an explicit reviewed host setup. Stop/restart with changed credential configuration revokes the previous binding; there is no hidden credentials-management API.

## Reproducible validation (no model calls)

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -c constraints-python312.txt
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s tests_backend -v
.venv/bin/python -m unittest discover -s tests_adapter -v
.venv/bin/python -m unittest discover -s tests_taskflow -v
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests_connector -v
.venv/bin/python tests_independent/independent_regressions.py --source . --output /tmp/stardive-independent.json
PYTHONPATH=. .venv/bin/python tests_connector/test_http_protocol.py --output /tmp/stardive-http-pilot-1
```

The last command starts **loopback only**, runs actual HTTP/SDK MCP initialization/list/calls, freezes a normal-language synthetic request, uploads generated test bytes, verifies observed values, changes a version and proves STALE/FAIL, checks owner/auth refusal and no MCP store writes, separately saves the receipt/result. It retains actual protocol responses and the synthetic store. It makes no Muse/model call and tests no public HTTPS ingress. HTTPX's environmental proxy is disabled **only for this loopback test**, not to reach external destinations. Nonfatal Pydantic/Starlette warnings are retained.

## Concrete private setup decision, still unexecuted

Once the user selects/approves an existing host and credential binding, mount a private config (chmod 600) **outside the repo**, and a persistent restricted store. `deploy/native-pilot/config.example.json` is intentionally invalid; it contains no live credential and must not be used as-is. Do not paste secrets into prompts, URLs or logs. No credential generator is included. With an already provisioned credential hash/config:

```bash
.venv/bin/python -m muse_audit.native_connector.server \
  --config /approved/private/pilot-config.json --store /approved/persistent/pilot-store
```

Default bind is 127.0.0.1:8765. A separately reviewed reverse proxy may terminate TLS and forward to it. Non-loopback serving additionally requires a configured HTTPS public base origin and `--reviewed-external-ingress`; this flag is not granted by this document. No port is published automatically. A single-worker container recipe is at `deploy/native-pilot/Dockerfile`; no build/deployment was performed here.

The coordinating user will conduct native registration and independent ordinary-request acceptance. Setup must establish the actual accepted bearer/API/MCP mechanism and credential exchange, then fresh ordinary requests must yield retained tool/API execution evidence, matching replay, useful result, small value table and inline receipt. Check denial/revocation/foreign owner, missing source, original failures and new-request independence. Do not count guided use as automatic acceptance. Public GitHub/license/Muse listing and the separate Workcheck Site remain unchanged.
