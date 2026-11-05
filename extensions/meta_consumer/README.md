# Stardive: voice intake and dedicated Meta review

An isolated integration extension prepared 2–3 November 2026. It leaves the
working native Muse controlled workflow and private Stardive research untouched.
No live Meta call, native installation, deployment, public release, or insurance
product has been validated by this checkpoint. The cloud handoff was attempted
but failed its device check; this checkpoint was built locally.

## What is implemented

- **Muse Voice Transcribe** file adapter (`muse-voice-transcribe-1.0`): multipart
  upload of mono PCM16 WAV at 16/24 kHz, at most 60 seconds. The consumer preview
  can record up to 30 seconds locally and encode WAV. No upload occurs before
  explicit permission. A returned transcript must be reviewed and confirmed.
- **Muse Spark 1.3** dedicated auditor (`muse-spark-1.3`): strict structured-output
  request and local validation of all findings, task/version/bundle identity,
  requirement coverage and supplied evidence IDs. This is advisory interpretation,
  not source authentication, independent truth or release authorization.
- **Muse Wonder** (`muse-wonder-1.0`) routing/escalation: complex work or a higher
  caller review floor selects Wonder. It is the API variant, not Wonder
  Full. A model can raise the review tier but cannot lower the caller's floor.
  If Spark raises the tier, a further review is requested explicitly; it is not
  silently charged or automatically treated as completed.
- Independent local byte/schema/binding checks, with an executable arithmetic
  failure → corrected artifact → fresh check → stale prior-advice refusal sample.
  Correct arithmetic does not complete an arbitrary task or its semantic checks.
- Per-process call, input-byte, output-token-per-call and audio-duration limits;
  no retry loop. A timeout, missing usage, incomplete response or invalid finding
  stays unresolved. Actual usage is retained only when returned. These are not
  an account-wide monetary cap or an insurer's pricing/risk model.
- In-memory request/version/advisory history and a consumer preview with record
  export. Export replay verifies bindings only. An operator controlling all local
  code and records can replace them: hashes do not supply third-party custody.

## Run locally, without credentials

Python 3.11+; no third-party installation required.

```sh
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 -m meta_consumer.demo --output .local/offline-demo-01
python3 -m meta_consumer.server --port 8766
```

Open `http://127.0.0.1:8766`. Confirm the request/checklist and prepare the sample:
the wrong total fails. Correct it and prepare again: the arithmetic passes while
the original failed record remains. Increase declared exposure or require a
human review to inspect the stronger routing. Meta buttons stay disabled when
the provider is unconfigured. This is a local preview, not mobile cloud hosting.

The offline demo uses a one-second silent WAV and injected provider responses.
It tests adapter wiring and refusal behavior, **not** transcription accuracy,
Meta-model behavior, token costs, audit efficacy or consumer acceptance.

## Live validation: separate remaining gate

Live testing requires explicit authorization for selected data and a spending
limit, an authorized Meta API key, and confirmation that the selected models are
available to that account. No key was read during development. Supply the key
through the server environment, never the browser, Git or command-line argument.
Then start the preview with `python3 -m meta_consumer.server --live` and explicitly
choose each upload/review in the UI. The default is offline. Use synthetic data
for the first validation. Do not pass private CKG source or consumer documents
merely to show more Meta product usage.

Default limits are three total provider calls per server process, 2,048 output
tokens per inference, 32,000 serialized request bytes per inference and 60 seconds
of audio in total. Restarting a process resets these limits. Configure a real
account/service spending cap before broader use; there is no dollar-cost ceiling
or price calculation here. Missing usage blocks further inference in the process.

The API models use Standard IDs. Contributor mode is not selected. Standard
mode's training policy is not a promise of zero retention, zero disclosure, legal
compliance or independent verification. See the current provider terms.

## Connect to the existing Muse workflow

1. Put this extension in its own sidecar process/package. Do not replace the
   accepted `controller.py`, native card, MCP tools or backend completion gate.
2. Use `intake()`/`MetaProvider.transcribe()`, then show the editable transcript
   and checklist. Call `confirm()` only after the consumer confirms them. Retain
   both the original transcript and approved text; voice is not identity/consent
   authentication. Freeze the exact approved text in the existing task workflow.
3. Obtain the selected current request, requirements, artifact and permitted
   evidence from the existing task's approved export. Use `bundle()` with that
   task ID and version. The sample HTTP preview constructs its own local example;
   it does not read or verify the native backend automatically.
4. Call `audit()` after per-request upload authorization and budget reservation.
   Store the returned advisory in a separate task/version-bound sidecar record.
   It may request more evidence or human review; it cannot grant canonical PASS,
   alter requirements, remove UNKNOWN, call `/complete`, or release a file.
5. Leave the existing deterministic MCP checks, independent receipt recomputation,
   current-version completion checks and guarded delivery in charge. An unresolved
   semantic requirement needs an accountable human decision and a documented scope.

That native orchestration and its actual app acceptance are still to be wired and
tested. The existing prototype's unsupported semantic/privacy/provider claims stay
unsupported. A second model from the same provider can share errors with the task
agent. Increasing compute does not by itself establish independence.

## Consumer and insurance direction

Proposed product: users state a goal; Stardive makes the applicable requirements,
evidence, unresolved conditions and extra review understandable. Declared exposure,
irreversibility and missing external read-back increase scrutiny. In the preview,
SGD100 routes to extended review and SGD1,000, irreversibility or an unobserved
external effect requires a human. These thresholds are illustrative defaults,
not calibrated underwriting or evidence of a low-risk action. Caller declarations
can be wrong. This package executes no transaction or external action.

An insurance path needs independently verified authorization and provider outcomes,
defined covered failures, real incident/loss data, human adjudication and an insurer
and appropriate permissions. This extension offers no coverage, premium, payout,
eligibility decision or partnership. A verification record is an input to that
future work, not an insurance policy.

## Current official references (checked 2–3 November 2026)

- [Meta models and availability](https://dev.meta.ai/docs/models)
- [Chat Completions parameters](https://dev.meta.ai/docs/protocols/chat-completions)
- [Structured output](https://dev.meta.ai/docs/structured-output)
- [Voice file format and multipart fields](https://dev.meta.ai/docs/speech-to-text)
- [Current provider pricing](https://dev.meta.ai/docs/pricing-rate-limits)

## Verification checkpoint

The original private checkpoint records the initial tested source hashes and limits.
The initial nineteen automated tests, injected-provider offline flow and a 390-pixel
browser walkthrough passed. The browser walkthrough checked failed arithmetic,
visible stale findings after an edit, corrected arithmetic and human/Wonder
routing. It did not exercise microphone capture, live transcription, real-model
advice, native Muse orchestration or deployment. Those remain unverified.

## Bounded synthetic live-test runner

`python3 -m meta_consumer.live_test --audio PATH.wav --output NEW_DIRECTORY`
validates the audio and shows the plan without reading a key or making a call.
The execution path additionally needs `--execute`, an explicitly authorized
spending budget and `MODEL_API_KEY` in the environment (or `--key-file` pointing
to a private file). The file may contain a bare key or a `MODEL_API_KEY=...` line.
It is parsed as data; it is never sourced as shell code. Never paste keys into chat.

This runner permits one attempt each for Voice Transcribe, Spark and Wonder,
at most twenty audio seconds, 16,000 request bytes per inference and 2,048
completion tokens per inference. It pauses after transcription for an operator
to compare the synthetic transcript before proceeding with the predefined request.
That test review does not establish a real consumer's identity or consent.

Pricing checked 3 November 2026 gives a conservative planning allowance of
US$0.538656, including a fourfold margin on a byte-based token estimate. It is not
a provider tokenizer, billing guarantee or account-wide spend limit. Returned
usage is converted at uncached Standard rates and retained separately from any
provider invoice. Missing usage, provider errors or invalid advice stop the run;
the runner does not retry or overwrite/resume an existing run directory.

`tests/test_live_runner.py` adds five offline checks: decline stops after voice,
exactly one attempt per model, preserved failures without secret error bodies,
missing usage stops further inference, and non-executing credential-file parsing.
The combined suite now has 24 passing tests. No live result is implied by these
offline runner checks; see the dated preflight record for the current live state.

No public license has been selected. Review source, dependencies, disclosure and
license before publishing this submission slice. No private research was copied.
