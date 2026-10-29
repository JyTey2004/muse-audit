# Private native Muse acceptance — 29 October 2026

The existing cloud implementation at `fb3fe1da1f8701d1ec5c71082be0ccd207f56628`
is deployed at `https://mcp.stardive.xyz` on Stardive's existing infrastructure.
Its 117 deployed source files matched Mac release `bcc3ec9` exactly. Later local
documentation updates do not change the deployed runtime. The service has its
own account, restricted persistent store and resource limits; the existing demo
routes and services were preserved.

## Observed native flow

Muse's registered `custom.stardive-task-assurance` connector uses its Secure
Credentials Store with API-key bearer placement and the sole credential host
`mcp.stardive.xyz`. Live initialization, enumeration of all three read-only tools,
their schemas and annotations, and a capability call were observed. Intake,
artifact upload and receipt persistence remain separate REST writes. No key,
surrogate, private task state or raw execution results are included in Git.

An ordinary fresh Markdown request initially skipped the connector and returned
no receipt. That failure is retained. Actual catalog inspection showed the
descriptor was current; the description was clarified for create/draft/transform
requests and the supported preferred-connector setting was applied. The user
also explicitly approved a remembered website permission covering `stardive.xyz`
and its subdomains. The credential remains restricted to the single MCP host;
global permission defaults remain unchanged and TLS/proxy controls remain enabled.

Two untouched requests in new chats then ran the full flow automatically:

| Test scenario | Independently checked result | Saved receipt |
|---|---|---|
| Markdown handover | 21 words against a 60-word maximum; supplied owner, dates and risk retained | Six selected checks passed; exact 138 delivered bytes matched; FRESH |
| CSV plan | Three supplied cost rows; total 36 against cap 45, leaving 9 | Three selected checks passed; exact 45 delivered bytes matched; FRESH |

Neither prompt named Stardive, task IDs, commands or setup paths. App activity
shows the original request frozen before artifact writing, a new immutable
version uploaded, native MCP review executed, a separate receipt saved and its
exact snapshot downloaded. Independent Mac replay compared the original request
and selected source pins, executed checks, counts, decisions and delivered bytes.
These are manufactured acceptance scenarios exercised through the ordinary
selected-input path, not independently authenticated real-world project facts.

The app returns the useful file, a short checked-value breakdown, material
unverified conditions and the saved receipt reference/date. A presentation-only
follow-up clarified the first Markdown display; its original receipt and artifact
were not regenerated. The later CSV display included its receipt reference on
the first response. Private evidence retains full references and protocol output
outside Git, rather than presenting an evidence package as the daily user result.

## Verification and preserved failures

The cloud/Mac runtime passed 208 unit tests and both independent sets of 14 checks.
The deployed host passed 41 taskflow and 44 connector checks. The native REST
helper initially failed seven of eight separately authored guard checks: local
limits, extra fields, symlink components, exclusive output creation and malformed
JSON handling. Those observations and source snapshots were preserved. The fixed
helper passed all eight, plus eleven offline helper tests in Muse. The final
source-only client exports were synced to the Mac and their manifests verified;
the approved key was absent. Backend runtime code was unchanged by these client
and presentation fixes.

Five earlier skill-based automatic failures, the native-discovery failure,
20-second setup timeouts and one unattributed HTTP 403 remain historical failures.
Later authenticated reads succeeded with the same saved credential and host;
the earlier 403 body was not captured and its cause is not asserted retrospectively.
Guided task-local tests and Claude/stdio tests remain distinct evidence streams.

## Scope and operational limits

This is a preferred workflow, not a platform-enforced global completion gate.
The tests demonstrate the two observed ordinary requests, not guaranteed use on
every future request. If Muse skips the connector or no receipt is returned, the
task remains unverified. Existing saved-skills automatic inclusion stays off.

Checks cover the model-interpreted checklist and exact artifact/source bytes.
Checklist completeness, source authenticity, broad semantics, privacy and
external provider state are not established. Workspace confinement does not
prove that every file the agent reads was selected for the task; the CSV run used
an earlier synthetic task contract as a structural example. The exported CSV
source bindings were independently checked against the new request's own inputs.
No general workspace-isolation or privacy certification is claimed.

The launch policy explicitly admits selected current-task inputs, retaining their
caller-declared classification; the declaration is not a privacy/authenticity
detector. Source/artifact bodies are bounded and stored-byte growth is capped at
256 MiB per owner. The backend never evicts earlier evidence to recover quota.
Changing bound source, artifact, checker or configuration requires a new recheck;
historical receipts do not silently become fresh assurance.
