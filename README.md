# Current cloud backend and native Muse checkpoint — 29 October 2026

New file tasks use the additive [taskflow engine](README-TASKFLOW.md), with frozen
per-request requirements and readable receipts. The same reviewed cloud backend
is deployed at `https://mcp.stardive.xyz`, synced to the Mac, and connected to Muse
through its Secure Credentials Store. The cloud implementation checkpoint is
`fb3fe1da1f8701d1ec5c71082be0ccd207f56628`; the deployed Mac release is `bcc3ec9`.

Two fresh ordinary requests automatically ran freeze, generation, upload,
read-only MCP review, receipt persistence and snapshot delivery. Independent Mac
replay matched the delivered Markdown and CSV bytes, all six and three selected
checks respectively, and both receipts rechecked **FRESH**. The first native
discovery failure and the five earlier skill failures remain preserved.
See [current native acceptance](docs/MUSE-NATIVE-ACCEPTANCE.md) and
[phase-by-phase history](TASKFLOW-VALIDATION.md).

Muse is configured to prefer this connector for artifact creation and verification.
That preference is not a platform-enforced completion gate: a missing receipt
means the task is unverified. Meaning, checklist completeness, source authenticity,
privacy and external provider state remain outside the deterministic checks.

Start with [BACKEND-QUICKSTART.md](BACKEND-QUICKSTART.md) for the persisted synthetic runner and read-only MCP `review_run`. Existing native-file tools, fixtures and instructions below are preserved. The web Workcheck artifact remains separate and unchanged. No remote push or public connector submission was performed.

Earlier, on 28 October, consumer Muse generated a budget workbook and ran the four-tool native-file MCP server on its cloud computer: **7 PASS, 0 FAIL, 1 UNKNOWN**, with a **FRESH** recheck. [CONSUMER-VALIDATION.md](CONSUMER-VALIDATION.md) preserves that bounded task-local trial. It is distinct from the later registered HTTPS connector and from the Mac's Claude `review_run` store.

---

# Muse audit companion — offline MCP prototype

**A real MCP stdio server, a shared audit/repair kernel, and two unrelated synthetic native-file jobs.**
The original offline demos below need no live model call. Later manual consumer
trials are documented above. No connector submission or automatic local sync is
implied, and no credentials are stored in this project.
The user's wider Muse audience is the product direction; this is a narrow testable tool, not universal verification.

Start with [QUICKSTART-MAC.md](QUICKSTART-MAC.md). This standalone checkout imports the reviewed prototype for local user testing. Development remains cloud-first. The [GitHub repository](https://github.com/JyTey2004/muse-audit) is private. No license has been selected or granted by this checkpoint.

The [private step-by-step field guide](https://muse-audit-field-guide.tey-jia-ye.chatgpt.site) documents the earlier workflow. For the scoped local developer host, see [CLAUDE-CODE.md](CLAUDE-CODE.md) and `start-claude-code.command`. [MUSE-CODE.md](MUSE-CODE.md) records Muse Code installation and offline MCP discovery; its live model flow remains untested. The later consumer Muse trial is documented above.

## What is implemented

- Official Python MCP SDK **1.29.0**, pinned maintenance-line version already available in the cloud runtime. Actual subprocess `initialize`, `tools/list`, `tools/call` and error/recovery tests negotiate **2025-11-25**. This is not a hand-written protocol stub. Muse Code initialized/discovered the tools in an offline echo run; **live Muse Code model tool use remains untested**. Consumer Muse's separate bounded trial is recorded above.
- `audit_capabilities`, `audit_job`, `prepare_repair`, `recheck_job`: all MCP tools are read-only. Patches must be reviewed and explicitly applied through the local CLI, to a **new** bundle only.
- Shared declared requirements, protected commitments, artifact/source versions and SHA-256 content pins, implementation-code hash, installed parser/SDK versions, exact evidence locations, full rechecks and stale/forged receipt detection.
- XLSX: actual cells/formulas read with openpyxl; exact integer-cent source comparisons; independently evaluate a narrow single-column `SUM` without trusting cached displayed values; required-cell inclusion; approved cap; protected cells.
- DOCX: actual top-level paragraphs read with python-docx; exact selected UTF-8 source-line transcription; protected paragraphs; coverage gate for unsupported structures.
- Narrow native-file repair writes a new copy, preserving other ZIP member payloads and rechecking every declared requirement. No source/contract edits to make a check pass.
- CLI JSON, HTML and Markdown reports, plus one-command demonstration. Static reports need no web server.

`model_adapter.py` is an explicit **unconfigured placeholder** that raises rather than generating canned “Muse” output. Model extraction, inferred requirements, ambiguous meaning, source authentication, image/audio/PDF auditing, a real XLSX recalculation engine, and app/browser checks are **not implemented**. No autonomous verification claim is made.

## The two jobs and honest outcomes

| Synthetic job | Before | After narrow repair | Still unresolved |
|---|---|---|---|
| Home-office XLSX budget | 6 pass, 1 fail, 1 unknown: delivery fee omitted | Delivery becomes correct, but total becomes 78,000 cents against unchanged 75,000-cent cap; 6 pass, 1 fail, 1 unknown | User must decide whether to change the setup; ergonomic claim remains unknown |
| DOCX study summary | 2 pass, 1 fail, 1 unknown: says 30 minutes instead of supplied 20 | 3 pass, 0 fail, 1 unknown; title and weekly plan remain intact | Claimed guaranteed exam improvement is unsupported |

Changing a source amount without changing its version label makes prior evidence **STALE**. `recheck_job` also returns newly executed results; it never treats a stale pass as current.

These are planted deterministic defects and hand-authored acceptance contracts, not observed Muse errors or empirical studies. The two jobs demonstrate kernel reuse, **not** automatic requirement understanding or market demand. No universal “ready” badge: required unknowns/blocked checks keep the scope unresolved. Even `SELECTED_CHECKS_PASS` covers only the explicitly declared checklist.

## Run from this checkout after local setup

From this directory:

```sh
python3 -m unittest discover -s tests -v
python3 tests/test_protocol.py
python3 -m muse_audit.demo --output /tmp/muse-audit-demo-1
# Open /tmp/muse-audit-demo-1/index.html on the same computer, or copy outputs locally.
```

Use a new output name on each demo run. The command never replaces existing work. Tests use temporary copies; shipped examples remain unchanged.

```sh
python3 -m muse_audit.cli --workspace examples audit home_office/job.json \
  --json-out /tmp/budget-receipt.json --report /tmp/budget-report.html
python3 -m muse_audit.cli --workspace examples plan home_office/job.json \
  --json-out /tmp/budget-plan.json
# Read /tmp/budget-plan.json first; this explicit command is the write boundary:
python3 -m muse_audit.cli --workspace examples apply home_office/job.json \
  --plan /tmp/budget-plan.json --output /tmp/budget-repaired-1 --approve-reviewed-plan
python3 -m muse_audit.cli --workspace /tmp/budget-repaired-1 recheck job.json \
  --receipt /tmp/budget-receipt.json
```

Exit codes: **0** command succeeded with no unresolved audit decision (e.g. plan/demo); **2** usable audit result contains fail/unknown/blocked/stale, or prior evidence is stale/invalid; **1** command/input error. An expected `2` is not a crashed test. Do not chain intentional failing audits with `&&` and expect later commands to run.

## Automated verification

[GitHub Actions](https://github.com/JyTey2004/muse-audit/actions/workflows/ci.yml) runs on pushes, pull requests and manual dispatch. The [workflow](.github/workflows/ci.yml) uses Python 3.12 on Ubuntu 24.04, installs the unchanged requirements and constraints, checks dependency consistency, runs the full unittest suite and standalone real MCP subprocess checks, runs the synthetic demo, and verifies the original examples remain unchanged. The protocol and demo steps still run after a test failure when dependency installation succeeded; a failed step keeps the job failed.

The workflow has read-only repository permissions and uses official actions pinned to commit hashes. No project credentials or model calls are needed. Consumer Muse is **NOT RUN in CI**; the manual consumer trial above is separate evidence. Other Python/OS combinations and native Office rendering are not covered by this job. Check a completed Actions run for its exact commit and result; workflow configuration alone is not passing CI evidence.

## Contract and trust boundary

Each selected bundle has `job.json`, one native artifact, and selected sources. JSON schema version 1 requires exactly:

- `schema_version: 1`, `job_id`, `title`, `intent`, `contract_version`
- `artifact: {path, version, kind}` (`xlsx_budget` or `docx_report`)
- `sources: [{id, path, version}]`
- `requirements: [{id, kind, description, mode, config}]`, mode `must_change`, `must_preserve` or `unknown`

The example manifests are complete templates. XLSX references use normal A1 cells and an exact sheet name; DOCX paragraph/source-line indexes are **1-based**. XLSX selected sources are `{currency:"USD", amounts:{...integer cents...}}`; currency must be explicit and match the mapping. Only exact `=SUM(B4:B6)`-style bounded single-column ranges of literal integers are evaluated. Other formula functions, formulas in the input range, booleans, numeric strings and floats abstain. A correct sum does not prove omitted requirements were captured; include required cells and source-mapping requirements explicitly.

The caller owns/approves the checklist and source selections. This prototype does not enforce a separate human identity or approval UI; it does not discover a complete checklist. A user deliberately changing the contract creates different evidence bindings, not proof that the previous obligation was met. All supplied file text is data, never an executable instruction.

Paths must be normalized, relative and contained inside the selected bundle, with no symlinks or traversal. Metadata filenames `job.json`, `receipt.json`, `repair-plan.json` are reserved, case-insensitively. Limits: 5 MB per file, 20 MB uncompressed native package, 100 requirements, 20 sources. No arbitrary shell/URL tool is exposed. This is a locally trusted-workspace prototype, **not** hardened hostile-document processing or an OS sandbox. Do not point it at sensitive folders or untrusted uploads. Hashes do not authenticate sources, sign receipts or defend against an attacker replacing code and evidence together.

`prepare_repair` cannot apply a patch. The CLI verifies the reviewed plan against current content and recomputed operations, rejects modified/stale plans and existing output paths, preserves the approved contract/source snapshot, and performs full protected-commitment rechecks. The environment must remain locally trusted; this is not concurrent-write isolation against a malicious process.

## Dependencies and verification limits

Python **3.11–3.14** is declared. The original cloud review used **3.12.14/Linux**. This local handoff also passed on **3.12.13/macOS arm64**; see [LOCAL-VERIFICATION.md](LOCAL-VERIFICATION.md). Direct requirements are pinned. `constraints-python312.txt` records the installed transitive closure including extras; there are no distribution hashes, so it is not a fully reproducible supply-chain lock. Fresh local macOS installation from official PyPI succeeded with these unchanged constraints. An isolated local package-install test reuses installed dependencies and does not prove fresh installation.

The installed SDK emits a Pydantic forward-reference warning on **stderr**. It did not corrupt stdout framing or prevent smoke tests. Do not hide this as a Muse-host result. The SDK's v2 API differs; do not remove the 1.29.0 pin without porting and rerunning protocol tests.

See [REVIEW.md](REVIEW.md) for the prior cloud review and `.local/` for locally generated logs and results. Broader historical research and older POCs were excluded from this standalone repository. This prototype chooses full checks; it claims no evidence-graph speedup, human-time gain, model quality or security certification.

## Primary implementation references (checked 27 October 2026)

- [Official MCP Python SDK v1 documentation](https://py.sdk.modelcontextprotocol.io/v1/) and [pinned 1.29.0 source](https://github.com/modelcontextprotocol/python-sdk/tree/v1.29.0): FastMCP/stdio and supported maintenance line.
- [MCP server guide](https://modelcontextprotocol.io/docs/develop/build-server): stdout is protocol-only for stdio servers.
- [Muse Code extension documentation](https://dev.meta.ai/docs/muse-code/extending): documented `mcp_servers` stdio configuration. The bounded [local host check](MUSE-CODE.md) verifies offline startup/discovery, **not live model tool use or consumer integration**.
