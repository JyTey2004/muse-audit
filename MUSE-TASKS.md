# Stardive Task Receipts

This skill describes a workflow for a supported file task the user
asks for in this chat: creating, drafting, transforming, or checking
a text, Markdown, JSON, CSV, spreadsheet, or document file, with a
read-only verification step and a readable receipt. It applies only
to that current task. It does not change permissions, credentials,
approvals, or other tasks, and it does not ask for a bypass of any
safety or policy control.

## Workflow

When you use this workflow for the current task, the steps are, in
order:

1. Read references/installed-paths.md in this skill for the
   installed paths and command templates. Those paths are private
   to the agent and do not belong in user replies.
2. Turn the request into a short checklist of its explicit
   obligations: supplied values, totals, caps, protected items, and
   any claims that have no supported check. If an essential
   requirement is unclear, ask one plain question.
3. Prepare a fresh task before generating the deliverable. The
   prepare command freezes the request, the interpreted checklist,
   and the selected sources. Prepare needs 1 to 20 selected sources.
   For a request with no supplied file, save the exact request
   verbatim as a selected source and pass it as the request source.
   For a CSV rows check, also freeze a separate source CSV
   transcribed from the supplied rows before prepare. That
   transcription is model-controlled, and in the final answer it
   is described as a model transcription, not as an independently
   authenticated source. The transcribed CSV contains exactly the
   data rows the artifact should match, with the same header, and
   no total row, because rows are compared exactly and the total
   is computed from the artifact rows.
4. Generate the deliverable inside that fresh task's artifacts/
   directory, using the frozen requirements. If a requirement
   cannot be met, report it rather than changing the requirement,
   cap, or protected item to fit the output.
5. Run the client review command for that task, using the installed
   interpreter and task store. The client starts a read-only
   review server, calls its review tool, keeps the observations,
   and writes a readable receipt plus a snapshot of the delivered
   file outside the server. A direct Python review, reading the
   file yourself, a model opinion, or an old receipt is a different
   kind of check, and is not presented as this client review.
6. Read the fresh readable receipt before presenting the result
   as checked.

## If verification cannot run

If a step cannot run for any reason, including a safety, policy,
or tool reason, stop that step and tell the user plainly that
verification is unavailable for that step. Present the file, if
any, as unverified for that step, and do not present it as
checked. Respect the user's instructions and the applicable tool
policy in that chat. This skill does not provide a way around a
safety or policy limit.

## Presentation when execution succeeds

When the workflow runs and a fresh receipt is available, present
in chat:

- A short result in one sentence, such as the total and remaining
  budget, or the purpose of the saved document.
- A small table, with one row per part of the request, showing the
  specific observed result for each part.
- Every failure, missing input, stale result, and material
  unsupported claim, shown plainly in that table.
- One scope line: Checked against the interpreted checklist;
  meaning and real-world accuracy may still need your review.
- Links to the result and to the readable receipt.

Keep machine details, logs, and protocol details in the task
store, not in the main chat answer, unless the user asks for
raw diagnostics.

## Supported checks and limits

- Text and Markdown: exact required or forbidden text, word limits.
- JSON: strict parsing and typed equality of selected fields.
- CSV: declared columns, exact selected rows, finite decimal
  totals and caps, in the same unit for the column and the cap.
- Spreadsheet and document files: the existing bounded native
  adapters and their coverage gates.

Unsupported formats, semantics, live web truth, privacy, sending,
delivery, and provider state remain explicitly unverified. A draft
does not prove a message was sent or delivered. The checklist is
interpreted, not independently complete, and results establish
only the specific comparisons that were run against retained
local bytes.

For a recheck, resolve the intended task from the conversation
and run a fresh client review, preserving older receipts and
snapshots. If the intended task is unclear, ask which task by
title. For a repair, use a reviewed scope and a new task copy
under the original requirements, leaving the original unchanged.

## Installation and developer commands

The private Muse installation retains **Stardive Task Receipts** for explicitly
requested pilot checks. Automatic prompt inclusion is off after failed ordinary
fresh-chat acceptance. Its private `references/installed-paths.md` records the
reviewed source directory, pinned interpreter and task store. These are setup
values, not user inputs. Keep the exact historical budget recheck skill available
with automatic inclusion off and a narrow historical discovery description.
No credentials, hosted endpoint or permission-policy change is needed for the
current task-local cloud route.

From the installed source directory, prepare with the pinned interpreter:

```sh
"$TASK_PYTHON" -m muse_audit.taskflow.cli prepare \
  --store "$TASK_STORE" --request-file "$REQUEST_FILE" \
  --requirements-json "$REQUIREMENTS_FILE" --source "request=$REQUEST_FILE" \
  --artifact-name "$ARTIFACT_NAME" --artifact-kind "$ARTIFACT_KIND" \
  --title "$TASK_TITLE"
```

Set the variables from the installed reference and actual task. Additional
selected sources use additional `--source ID=PATH` arguments. Read the returned
`task_id` and `task_dir`, create the result inside that task's `artifacts/`, then
run the actual MCP client:

```sh
"$TASK_PYTHON" -m muse_audit.taskflow.client_cli \
  --store "$TASK_STORE" --task-id "$TASK_ID"
```

The new output directory contains `receipt.md` and a delivered-file snapshot.
Machine receipts and protocol observations remain internal diagnostics. A
successful process exit alone is not a passing result: read the receipt decision
and all checks. The model's task interpretation and source transcription remain
outside the deterministic checker's independent coverage. Skill instructions
are a workflow aid, not an enforced Muse host hook; verify actual execution and
receipt delivery when validating a fresh chat.
