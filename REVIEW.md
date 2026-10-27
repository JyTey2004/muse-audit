# Independent cloud review — Muse audit checkpoint 1

**Result:** 54 tests pass; the two-job demo and real MCP stdio launcher work. Four correctness defects were found, fixed by the builder, and independently retested. No blocking defect remains in this bounded functional review. This is not security certification or evidence of actual Muse integration.

## Exact reviewed version

- Prototype: `0.1.0`, CPython `3.12.14` on Linux.
- Runtime implementation SHA-256: `c39a92e89634ba9a9a16d7820fd4d08dc8ad78da1b485a729d9db7cf423c62ea`.
- Reviewed source/tests/docs/dependencies/examples file-manifest SHA-256: `d243d633f424a5197b2c0b46e4f92227b4c0c77a19b2004a718d2b910eaa6e0e`.
- This document summarizes prior Linux cloud review. Full historical evidence remains in the private checkpoint archive. This standalone repository does not import its workspace history.
- The runtime hash above identifies the unchanged imported Python implementation. The broader reviewed file-manifest hash describes the original cloud tree; local setup documentation has since been adapted.

## Findings fixed and verified

| Finding | Original consequence | Verified correction |
|---|---|---|
| R1 — output metadata/source name collision | A selected `receipt.json` source was overwritten by output metadata; immediate recheck became STALE | Reserved output names rejected, including case aliases; copied sources remain intact |
| R2 — currency omitted on both sides | `None == None` could incorrectly PASS an amount mapping | Explicit uppercase three-letter mapping currency and matching source currency required; unavailable mappings abstain |
| R3 — non-object source JSON | A valid JSON list caused an uncaught attribute error | Source/amounts object shape validated; unsupported source shape returns UNKNOWN |
| R4 — manifest changed during repair | A concurrent save could adopt unreviewed requirements into output | Output derives from approved snapshot; current manifest is reread and checked before publication; changed input discards output |

These were reproduced with temporary synthetic copies, not private files. Dedicated regression tests named in the JSON evidence now cover each fix. Exact XLSX mapping fields also reject extra unsupported configuration; DOCX does the same. Documentation now includes required `schema_version` and matches the declared Python range.

## What was independently checked

- **54-test suite:** binding changes for artifact, source, contract and implementation; old-result recomputation; altered/stale plan refusal; missing/unsupported input; exact source quotation; preserved commitments; native ZIP payload preservation; read-only MCP tool inventory; errors followed by successful calls.
- **Arithmetic controls:** a shortened SUM range fails required-cell inclusion; comma-argument SUM, addition formulas and literal totals abstain. The final suite also confirms a planted cached total is ignored. These are narrow independent calculations, not a spreadsheet engine.
- **Repair truthfulness:** budget fee correction exposes the unchanged cap failure (`78,000 > 75,000`), rather than hiding it. DOCX quote correction preserves title/plan and leaves the causal claim UNKNOWN. Original files remain unchanged.
- **Full demo:** XLSX remains `6 PASS / 1 FAIL / 1 UNKNOWN` and REVISE; DOCX becomes `3 PASS / 0 FAIL / 1 UNKNOWN` and UNRESOLVED. A source-content change without a version-label change yields STALE prior evidence.
- **Real protocol:** official installed MCP SDK subprocess client negotiates `2025-11-25`. Absolute-path `run_mcp.py` works from `/tmp` without `PYTHONPATH`. Four tools are read-only; no apply tool is exposed.
- **Local package/CLI:** a copied package installs without network using existing dependencies. Installed console entry points work outside the checkout. Audit exits 2; plan exits 0; apply without the approval flag exits 1 and creates no bundle; reviewed apply exits 2 for remaining issues; immediate recheck is FRESH and still exits 2. Example bytes remain unchanged.

## Reproduction commands

From this repository root with the local virtualenv activated:

```sh
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 tests/test_protocol.py
python3 -m muse_audit.demo --output /tmp/muse-review-demo-NEW
```

The demo destination must not already exist. For the packaging smoke, copy the prototype to a temporary directory, then run:

```sh
python3 -m venv --system-site-packages /tmp/muse-review-NEW/venv
/tmp/muse-review-NEW/venv/bin/python -m pip install   --no-index --no-deps --no-build-isolation /tmp/muse-review-NEW/package
```

This intentionally reuses the cloud's installed dependencies. It does **not** prove a fresh Mac install. Follow `QUICKSTART-MAC.md` for the separate user-run checkpoint.

## Open limits, not silently passed

- Muse Code/consumer Muse registration, live model invocation, provider access and all key/spending setup remain untested/unconfigured.
- Fresh-network dependency installation, macOS execution, Word/Excel/Numbers rendering and spreadsheet-engine recalculation were not performed. Dependency constraints have no distribution hashes.
- Source authenticity, semantic truth, complete requirement discovery, arbitrary formulas/formats and hostile-file containment are outside scope. Hashes bind bytes; they do not authenticate them. Human approval is caller-owned, not identity-enforced.
- The installed SDK emits a nonfatal Pydantic warning on stderr. Protocol framing and recovery still passed; this is not hidden as a Muse-host success.
- Review did not run or modify frozen prior POCs, private files, keys, paid calls, deployment, Mac access or external state. New ZIP packager execution is builder-owned, not independently certified here.
