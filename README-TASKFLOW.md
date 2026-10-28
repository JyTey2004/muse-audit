# General file tasks and readable receipts

The additive taskflow engine is installed in the private Muse cloud workspace
and synced to the Mac. It prepares new tasks instead of reusing the historical
budget. The old source, frozen budget, receipts and runtime paths are preserved.

Automatic fresh-chat use is **not working**: five ordinary-request trials across
CSV and Markdown returned no fresh verification receipt. Muse rejected the saved
skill instructions through its prompt-injection safety check, including after a
scoped rewrite. Installing a skill is not a native tool registration. The desired
one-look presentation below remains the target; see
[TASKFLOW-VALIDATION.md](TASKFLOW-VALIDATION.md) for observed acceptance status.

## What this adds

A small task-flow layer around the existing audit kernel:

- Prepare freezes a fresh task before generation: the actual user
  request, the model-interpreted checklist, and the selected source
  bytes. An ordinary drafting request already authorizes its explicit
  requirements, so prepare does not demand a second technical approval.
- Review checks only listed requirements, in the launch-scoped store,
  and verifies frozen bindings before and after checking.
- Recheck recomputes everything and marks old assurance stale when
  artifact or checker bytes change.
- Repair creates a new task copy under the original requirements. It
  never edits the original task, artifact, or receipt.
- Reviews never overwrite prior outputs. Each review writes a new
  timestamped output directory inside the task.

## What is checked

Deterministic checks only:

- Text and Markdown: required exact text, forbidden exact text, word limit.
- JSON: exact selected fields.
- CSV: declared columns, exact source rows, totals and caps.
- XLSX and DOCX: the existing native adapters, reused unchanged.

Unsupported semantic, web, privacy, sent or delivered, and provider-state
claims stay explicitly unverified. A created draft cannot prove a
message was sent. No arbitrary shell or URL evaluation checker is
provided. Source or contract tampering and missing required inputs
block passing.

## Product reply format for everyday tasks

Task and result first, then a short checklist of what was checked, what
needs attention, and what remains unverified, then a next action if
needed, then a short completion receipt reference and links to the
result and the readable receipt. Raw execution data is kept with the
machine receipt, behind an optional details view, not in the main
deliverable. Model-interpreted coverage is never claimed to be
independently complete, and no task is called certified on the basis
of selected checks alone.

## How to run the tests

Use the same pinned Python packages as the original source. From this
package directory, run the native, backend, adapter, and taskflow suites.
The taskflow protocol test starts a real stdio server in a subprocess
and checks that its tools are read-only and that review does not
modify task inputs.

## Corrections in this v2 copy

- Exact kind dispatch only: unknown kinds stay unknown, including
  unsupported JSON, text, and CSV kinds.
- JSON field equality is recursive and typed, so a boolean is not an
  integer, and strict JSON reading rejects duplicate keys.
- CSV totals use bounded finite Decimal comparisons. Duplicate or
  empty headers, malformed rows, and nonfinite numbers are rejected.
- The native document kind is corrected, and native checks go through
  the existing kernel once, preserving archive guards, extraction
  coverage, and source and native preconditions.
- Reviews refuse symlinks in artifacts, sources, frozen records, and
  parent input paths, and enforce file-size limits at read time.
- Checker identity reuses the existing full project identity, covering
  all project Python, dependency declarations, and runtime package
  versions. Code changed after process start blocks review.
- Frozen-hash record availability and content are part of current
  bindings, so withholding that record stales old evidence.
- Each review output now includes a byte snapshot of the reviewed
  artifact, alongside its immutable receipt.
- Recheck compares task identity, title and request, coverage, checks,
  counts, and decision, not only result fields.
- A repair clone now requires an explicitly reviewed repair scope and
  copies only sources that scope explicitly adopts.
- The readable receipt directs restoring the original input or
  starting a newly confirmed task, never fixing the frozen record to
  weaken the contract. It always discloses checklist-coverage limits,
  shows the short title plus short observed and expected values where
  useful, and avoids huge values, local paths, raw hashes, tool and
  protocol names, and raw-evidence packages.
- Daily-use review must use the new client, which actually calls the
  read-only server, retains method and result observations, and then
  writes an immutable readable receipt plus an artifact snapshot
  outside the server. The server itself remains strictly read-only.

## How to try a task by hand

Prepare a task, write the deliverable into the task artifacts folder,
then review it. Repair, if needed, creates a new task copy under the
original requirements; generate a new deliverable there and review it
again. Do not claim automatic consumer integration from a direct CLI run or a
guided chat test. Native connector registration and a fresh ordinary-request
acceptance test remain necessary.
