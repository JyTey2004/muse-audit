# Dedicated Muse controlled task workflow

This entry point accepts one normal request in `args.request`. It supports text,
Markdown, JSON and CSV artifacts through the existing private HTTPS backend.
It creates no new credential, permission, endpoint, scheduled job or cloud service.
The three native MCP tools stay read-only.

`workflow.js` awaits each native Promise-returning agent stage. The actual native
runtime probe confirmed that top-level await returns the schema-validated object.
Runtime suspension/provider errors are left to the native runtime rather than
being swallowed by a generic catch. It runs bounded stages: plan/freeze, private draft/upload,
verification, then delivery. The guarded `controller.py` performs backend writes
through the existing host-scoped Muse SCS broker. The request is frozen before
artifact generation; no stage can pass a caller verdict to the service. The
verifier saves the actual server-recomputed audit and attempts completion.
A failed/unknown/stale/missing receipt ends the workflow with the native blocked
control result, with check values/reasons and an audit reference when available.

Delivery is a separate code path, never a copy of the worker's local draft. It
requires this run's persisted receipt, checks its request/version/artifact bindings,
revalidates current server completion, downloads through the existing gated result
URL and checks the exact bytes before exclusive creation of the final output.
No implicit verification, repair, cap change or draft fallback happens at delivery.
A new upload or changed evidence blocks later retrieval. Earlier files/history
are preserved, and changed final files are never overwritten.

In Muse install controller.py beside the existing connector helpers, then create
the saved workflow from workflow.js. Use a dedicated chat to route a plain user
request to `workflow.launch(name='stardive-controlled-task',args={request:exact})`.
Render only the curated final return: useful file, observed/required check table,
receipt/date and one scope sentence. Do not attach scratch/plan/receipt JSON.

The saved workflow and publisher source plus private run context are trusted.
Native child agents retain normal workspace access: this is not an OS sandbox
against a malicious process rewriting that trusted source/context. JavaScript
stage schema validation does not authenticate model prose; authoritative checks
and file release remain in the backend, and the publisher independently retrieves
them. The controlled entry point does not add a global Muse final-response veto.
Dedicated-chat routing itself is a scoped agent instruction; other chats remain
outside this workflow.

Production accepts no skip/override flags. The separately named negative-test
snapshot changes only SKIP_VERIFICATION_TEST to true, deliberately omits verify,
and calls the same guarded publisher to prove actual missing-receipt refusal.
It always returns blocked and exposes no final file. It is not the user entry point.

Validation: `python -m unittest discover -s tests_controlled -v` exercises the
controller against the actual local ASGI backend with synthetic credentials.
`node tests_controlled/test_workflow.mjs` executes the exact workflow JavaScript
with manufactured stage outputs. Actual native runs are separate acceptance.
