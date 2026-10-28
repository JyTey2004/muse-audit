# Consumer Muse validation checklist

The latest per-request extension and five failed automatic fresh-chat trials are
recorded in [TASKFLOW-VALIDATION.md](TASKFLOW-VALIDATION.md). The backend supports
new file tasks, but the saved-skill route has not delivered the requested
automatic result/checks/receipt flow. The bounded historical budget trial below
is separate evidence and does not clear that acceptance requirement.

The B2C target is consumer Muse. Muse Code is a separate optional developer host. A bounded consumer-chat trial now runs the existing native-file MCP server on Muse's own cloud computer. This is a task-local Python client, not a registered connector or access to the Mac's local stdio server.

## Consumer app checkpoint — 28 October 2026

The signed-in Muse Mac app (version 9.0) was accessible. Settings listed built-in connectors but no custom MCP URL field. A read-only diagnostic reached the selected Mac configuration file. Muse reported that its exposed Mac tools could not spawn a local shell or MCP client, and made no local `review_run` invocation. Local file access is not local process access.

Muse then generated a new home-office XLSX on its own computer from synthetic quotes: desk $450, chair $250 and delivery $80, with a fixed $800 cap and the existing monitor retained. The operator froze the separate test contract and sources before generation. This is a new scenario; the shipped $750-cap fixture is unchanged. The generated file was downloaded, preserved byte-for-byte and independently audited on the Mac: **7 PASS, 0 FAIL, 1 UNKNOWN**. Chair comfort remains unsupported and the overall decision is **UNRESOLVED**. No natural generation defect was observed and no defect was planted.

The existing backend source at implementation checkpoint `e082a027381e4714741f83e945ef03d3cf96248d`, a hash manifest, the frozen task and a small SDK client were then uploaded to the same private Muse chat. The client first verifies package and artifact hashes. It starts `run_mcp.py` in a subprocess using the official MCP SDK 1.29.0, checks the exact four read-only tools, calls `audit_capabilities`, `audit_job` and `recheck_job`, and verifies the selected inputs remain unchanged. It does not expose an apply tool. Muse used a fresh virtualenv with the existing pinned dependencies on Python 3.12.3/Linux. The returned protocol is `2025-11-25`.

Muse returned the actual receipt, raw MCP responses, fresh recheck, environment record, stderr, original workbook and original package manifest. Independent Mac replay matched the checks and counts, artifact bytes, manifest and backend code binding. The cloud result is **7 PASS, 0 FAIL, 1 UNKNOWN**, with **FRESH** recheck. The nonfatal Pydantic warning remains in stderr.

Native-app generation and download were observed directly. The later upload, execution activity and receipt delivery were exercised through the signed-in Muse web view of the same conversation after native UI automation stopped responding. This is consumer Muse execution on its cloud computer, not Muse Code. No hosted endpoint, tunnel, directory submission, new account credential or permission-policy change was needed.

Evidence is retained outside Git: frozen inputs, original downloaded workbook, raw protocol results, execution activity observations, exported receipts and cross-host comparison. The probe observes only its own subprocess; it does not capture unrelated Muse tools or hidden host logs. Returned evidence is unsigned, source quotes are synthetic, and there is no hostile-file sandbox or blanket completion certification. This trial does not connect the Claude run store to Muse or validate the separate `review_run` adapter in Muse.

### Tested app experience

One setup installs the trusted, bounded verifier in Muse's task workspace. The user then asks for the task in ordinary language. New tasks need a confirmed supported checklist; existing tasks can be rechecked with a short request. Technical identifiers, package installation, source pins and protocol details belong behind the result, not in repeated user prompts.

The chat should lead with the useful outcome, for example: **“Budget checks pass: $780 total, $20 under cap.”** Then show **“Not verified: chair comfort.”** Attach the workbook and a readable receipt; keep raw diagnostics outside the ordinary answer. Keep prior results and make changed or missing bound inputs block acceptance. Review repairs separately before any new artifact is written. This historical trial is a bounded budget workflow; it does not prove general task understanding.

A local Muse skill, **Stardive Budget Check**, was saved with the frozen bindings and reviewed from its downloaded copy. Its generic connector fallback was removed, and new-budget confirmation asks for ordinary task requirements while setup owns technical mappings and pins. The short request **“Recheck my budget”** then loaded that skill, executed the unmodified MCP probe into a fresh output directory and delivered the concise result, workbook, fresh receipt and raw evidence in the same conversation. The second receipt has a later execution time and identical original bindings/checks. Both cloud receipts and the Mac replay were retained. Cross-chat discovery and a new-budget setup flow were not tested.

Meta's [connector help](https://www.meta.com/help/superintelligence/1687253048996149/) and [security architecture](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse), checked 28 October, describe chat-created custom connectors and Muse's cloud computer. They do not by themselves establish a native Mac stdio interface. The execution observations above establish only this tested task-local route.

## Prior local checkpoint — 27 October 2026

The consumer access check did not reach Custom Connector setup. Account-specific gate details are retained only in ignored local notes. Consumer tool invocation, evidence display and correction/recheck are **NOT RUN**. The accepted connection method, endpoint/transport, authentication and file exchange are **UNKNOWN**. No bridge, tunnel, hosted service, credentials or persistent grants were created.

The official Connector Platform guidelines request endpoint/authentication details and API or MCP documentation for directory submissions. They do not establish this account's personal Custom Connector interface or prove that a Mac-local stdio process is reachable. Confirm the actual consumer setup first; explain any required hosting and authentication and obtain approval before implementing or deploying it.

## Access and integration gate

1. Open the official [consumer Muse site](https://muse.ai/) with an account entitled to use it. A waitlist or region gate blocks host testing; do not bypass it or substitute a Muse Code run.
2. In the accessible consumer UI, inspect Settings > Connectors and the personal Custom Connector workflow. Record its actual accepted interface: API specification/URL or CLI package, transport, endpoint shape, authentication, file input/output route, and permission boundary. Keep secrets out of test notes.
3. These details are **UNVERIFIED** for this prototype. Public guidance supports personal Custom Connectors, and describes services with APIs or CLIs; it does not establish arbitrary Mac-local stdio support, a required remote MCP transport, or a specific endpoint. Do not deploy an HTTP bridge or tunnel until the accepted interface is confirmed. A Muse VM cannot be assumed to see the Mac checkout or its absolute paths.
4. Review a concrete proposed connection before granting credentials, OAuth or broader access. Use only synthetic bundles. No billing, legal acceptance, public submission or directory publication is part of this checkpoint.

## Synthetic cases once the host is connected

| Case | Required observable result |
|---|---|
| Tool inventory | Only audit_capabilities, audit_job, prepare_repair, recheck_job; read-only; no apply tool |
| Selected files | Native artifact, declared contract and selected source bytes reach the approved audit workspace; record their version/hash bindings |
| Budget audit | Missing delivery fee identified at Budget!B6; initial 6 PASS / 1 FAIL / 1 UNKNOWN |
| Budget proposal | Exact fee patch; preserved 75,000-cent cap; no silent file application |
| Reviewed local CLI repair | New copied bundle; total 78,000 cents exposes cap failure; 6 PASS / 1 FAIL / 1 UNKNOWN |
| DOCX audit/proposal | Quote differs: 30 versus supplied 20 minutes; title and weekly plan protected |
| DOCX repaired copy | 3 PASS / 0 FAIL / 1 UNKNOWN; guaranteed improvement remains unsupported |
| Staleness | Change a copied source amount without bumping its version; prior receipt becomes STALE and full checks rerun |
| Scope/error recovery | Attempt a path outside the selected synthetic workspace; reject it, then complete a valid audit |

Keep CLI repair outside the consumer connector until a separately reviewed write boundary exists. Preserve original artifacts, contracts and source files throughout.

For each case, record the user's request, actual host tool invocation, selected file bindings, raw result, user-visible explanation and final artifact. Mark missing observations UNKNOWN or NOT RUN. A model saying it checked something is not tool evidence. No blanket access to private Muse logs or unrelated artifacts is assumed.

## Official sources checked 27 October 2026

- [Meta Help: how Muse works with Connectors](https://www.meta.com/help/superintelligence/1687253048996149/): personal Custom Connectors are available for unlisted services; setup may retrieve API information. This is distinct from directory approval.
- [Meta: how safety is built into Muse](https://security.muse.ai/): consumer clients use a per-user cloud VM; custom connectors may work with services' APIs or CLIs. This does not prove this package can be installed or invoked there.
- [Muse Connector Platform guidelines](https://platform.muse.ai/docs): public directory submission/review route, including endpoint/auth documentation; no public submission is planned here.
