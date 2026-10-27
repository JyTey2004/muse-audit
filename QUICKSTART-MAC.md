# Local user testing on macOS

This checkout is a local handoff of a cloud-developed prototype. No API key or model call is needed for the offline demo. The [GitHub repository](https://github.com/JyTey2004/muse-audit) is private; no license has been selected.

## Start the prepared demo

In this repository, double-click `start-demo.command`, or run:

```sh
./start-demo.command
```

It creates a fresh report under the ignored `.local/` directory and opens it in your browser. It copies synthetic examples and repairs only those copies. It does not connect to Muse or call a model.

Expected results:

1. The XLSX delivery fee is missing. Repairing it makes the total 78,000 cents against the unchanged 75,000-cent cap. The cap failure remains; the ergonomic claim is UNKNOWN.
2. The DOCX says 30 minutes where its synthetic source says 20. Repair fixes the quote while preserving the title and weekly plan. The claim about guaranteed exam improvement remains UNKNOWN.
3. Changing a source amount without updating its version label makes the earlier receipt STALE. Full checks run again.

Open the generated XLSX and DOCX files in the report's repaired folders to inspect them in Excel/Numbers or Word. Native-app rendering and spreadsheet-engine recalculation require separate user testing.

## Recreate the isolated environment

Use Python 3.12 for the supplied cloud dependency constraints. No global packages are changed.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple -r requirements.txt -c constraints-python312.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/test_protocol.py
```

If a pinned dependency is unavailable, retain the error and stop. Do not silently upgrade the MCP SDK or discard the constraints. Local setup logs, protocol output and demo reports are under `.local/` and are excluded from Git. `REVIEW.md` records historical Linux cloud results; it is not a claim of Mac or live Muse execution.

## Review and apply a patch yourself

Activate the environment, choose unused output paths, and inspect the exact proposal:

```sh
source .venv/bin/activate
python -m muse_audit.cli --workspace examples plan study_summary/job.json --json-out /tmp/study-plan.json
cat /tmp/study-plan.json
```

After reviewing the proposal, explicitly apply it to a new folder:

```sh
python -m muse_audit.cli --workspace examples apply study_summary/job.json \
  --plan /tmp/study-plan.json --output /tmp/study-repaired-1 --approve-reviewed-plan
python -m muse_audit.cli --workspace /tmp/study-repaired-1 audit job.json \
  --report /tmp/study-repaired-report.html
open /tmp/study-repaired-report.html
```

Exit 2 is an expected usable audit result with failures, unknowns or stale evidence; exit 1 means a command/input error. Do not loosen a contract to make the result green.

## Consumer Muse testing

For the tested local developer-host route, use [CLAUDE-CODE.md](CLAUDE-CODE.md) and `./start-claude-code.command`. Its tools are limited to copied synthetic bundles and its configuration is session-scoped. This is separate from consumer Muse validation.

The B2C validation target is consumer Muse. Follow [CONSUMER-VALIDATION.md](CONSUMER-VALIDATION.md) for access checks, the unresolved connector interface, and synthetic cases. Consumer access and tool calls have not passed. The public personal Custom Connector route does not establish a Mac-local stdio connection.

The prepared ignored `.local/muse-settings-entry.json` is a **Muse Code-only** developer example. It does not configure consumer Muse. No Muse Code installation is required for the offline demo or a substitute for consumer validation. Its server workspace is restricted to `examples`, and no host settings have been changed.

All four prototype tools are read-only. No tool applies a patch. Credentials, OAuth grants, spending/billing, legal acceptance and public connector submission require separate explicit authorization. Do not put keys in chat, source or Git.

## Feedback to bring back

Record which job you tried, whether you could locate the evidence, whether UNKNOWN and STALE were understandable, and the time spent selecting files, mapping sources and reviewing a patch. Keep private files out while evaluating this bounded synthetic checkpoint. This is exploratory feedback, not a controlled user study.
