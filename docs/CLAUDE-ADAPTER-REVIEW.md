# Independent Claude adapter review

A separate reviewer inspected the new adapter without editing its source. Initial findings and fixes:

1. Generated target stdout could mint checker PASS. Assertions/reporting now run in a parent verifier, while generated code executes in a separate worker VM without Node globals, imports/dynamic imports or eval. The original stdout spoof now abstains.
2. Unrestricted target imports allowed ordinary filesystem writes. The self-contained pure-JS loader rejects those capabilities; static/dynamic node:fs and eval repros abstained without creating outside files. **Node VM is not a security sandbox. Only trusted local generated code is supported.**
3. Terminal-first / missing-session streams were accepted. Parsing now validates ordering, session IDs, tool ID pairing and message roles. Phase 2 also requires the actual tool result to match a freshly executed independent receipt's schema, run, bindings and conditions.
4. Tool names alone did not establish file scope. Captured paths must resolve to the fixed app files under the approved workspace. This is post-hoc detection, not an OS filesystem sandbox. Malformed input types now return False and have a regression.
5. The delivery condition overclaimed functionality. It now establishes required file presence only; browser functionality remains a separate required UNKNOWN.

Independent retest: 25 then-existing adapter tests passed, including real official-SDK MCP initialize/list/call with unchanged SQLite bytes and current-state rechecks. Targeted manual stdout/import/eval/path/order repros were closed. One additional actual-source-mutation/restart regression was added afterward by the implementer; see final logs for final suite count. No critical remaining issue was reproduced in the reviewed cases. This is a bounded correctness review, not adversarial sandbox certification, host validation or production assurance.

Cloud model-driven tests: NOT RUN. Claude Code 2.1.305 on Mac is the intended real host; its final evidence must be reviewed separately. No fake Claude or Muse integration is claimed. Offline host streams are labeled test doubles.
