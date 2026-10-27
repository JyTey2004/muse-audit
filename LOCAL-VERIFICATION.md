# Mac verification — 27 October 2026

Executed locally with CPython 3.12.13 on macOS 27.0.1, Apple silicon (arm64).

| Check | Actual result |
|---|---|
| Fresh isolated dependency installation | PASS, official PyPI, supplied requirements and constraints unchanged |
| Unit/integration suite | PASS, 54 tests |
| Standalone official-SDK MCP subprocess smoke | PASS, initialize/list/call, protocol 2025-11-25 |
| Error recovery and path traversal refusal | PASS |
| Dependency consistency | PASS, pip check |
| Synthetic two-job demo | PASS, expected unresolved outcomes retained |
| Imported Python runtime, tests and example bytes | Unchanged |
| Consumer Muse Custom Connector/tool flow | BLOCKED at access gate; connector setup and calls NOT RUN |
| Live Muse Code | NOT RUN; separate developer host, not a B2C substitute |
| Word/Excel/Numbers rendering and recalculation | NOT RUN |
| Historical older-project 78 tests | NOT RUN on Mac; excluded projects |

MCP inventory contains only `audit_capabilities`, `audit_job`, `prepare_repair` and `recheck_job`. All are read-only. No model/API call was made. The installed SDK emits the previously observed nonfatal Pydantic forward-reference warning on stderr; protocol framing and recovery passed.

Runtime implementation SHA-256: `c39a92e89634ba9a9a16d7820fd4d08dc8ad78da1b485a729d9db7cf423c62ea`.

The local demo keeps the budget at 6 PASS / 1 FAIL / 1 UNKNOWN after the fee repair: 78,000 cents exceeds the preserved 75,000-cent cap. The DOCX becomes 3 PASS / 0 FAIL / 1 UNKNOWN. Source-content mutation makes prior evidence STALE. Original examples and contracts remain unchanged.

Detailed setup/test logs, local environment metadata, generated reports, and the prepared absolute-path Muse Code settings entry are retained in ignored `.local/`. Full private research and historical generated evidence were not imported. The user selected the private [GitHub repository](https://github.com/JyTey2004/muse-audit) and no license. Its initial source checkpoint contains only the standalone project; local logs and results are excluded. Hosted CI is NOT RUN; local verification does not establish a consumer release.

## Follow-up launch verification

The existing local `start-demo.command` was run again successfully on 27 October 2026. It generated a fresh synthetic report, and the report was visibly opened in Chrome. The 54-test suite and standalone real MCP subprocess check passed again, including the absolute-path entrypoint from another working directory, read-only tool inventory, path refusal and recovery. The negotiated protocol remains 2025-11-25. `pip check` passed and all 33 supplied dependency pins match the isolated Python 3.12.13 environment.

No runtime, test or example bytes changed. The expected budget failure, unsupported claims and source-change STALE result remain visible. Native-app rendering/recalculation remains NOT RUN. No reproducible runtime setup failure was found; the constraints file's stale comment about macOS setup was corrected without changing any pins.

Consumer Muse's access gate did not permit reaching Custom Connector setup. Its accepted API/MCP method, transport, authentication, file-transfer route, actual tool calls, evidence display and correction/recheck flow remain UNKNOWN or NOT RUN; see CONSUMER-VALIDATION.md. Account-specific observations and local command logs are retained only in ignored `.local/`. No consumer connection, deployment or credentials were created.
