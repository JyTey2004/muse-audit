# Consumer Muse validation checklist

The B2C target is consumer Muse. Muse Code is a separate optional developer host. Current runtime: unchanged offline MCP stdio prototype; no consumer-host integration has passed.

## Latest local checkpoint — 27 October 2026

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
