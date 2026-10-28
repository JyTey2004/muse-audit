# Selected task inputs and stored-byte quota — source-only rollout delta

This is an incremental change from cloud `550df9842273081bd14b21248ffa70b44d6c8d9d`, for the existing native connector service. The coordinator has reported verified Stardive DNS/AWS access and an existing Ubuntu24.04/aarch64/Python3.12/Caddy host with persistent disk. Deployment, DNS, Caddy, credentials and service operations remain entirely with that coordinator. No such operation is performed in this source run; no new compute, volume, tunnel, live key or consumer-acceptance claim is included. The earlier cloud-workspace hosting gap remains a historical observation, not a claim that the coordinator's external host is unavailable.

## Launch policy

Two launch-only configuration fields are added:

```json
{
  "data_policy": "selected_task_inputs",
  "max_stored_bytes_per_owner": 268435456
}
```

The **default** remains `data_policy: synthetic_only`. This preserves existing pilot behavior. The operator must explicitly set `selected_task_inputs` on the existing service to admit selected current-task user inputs. This is not public-data access, unrelated-file/account access, semantic interpretation completeness or a production security certification. Existing owner authentication and scopes (`intake`, `artifact`, `receipt`, `review`) are unchanged. Callers cannot select their principal, store, filesystem root, data policy or quota.

The existing `synthetic` request field stays a required **boolean caller declaration**:

- `true`: declared synthetic; fixtures/examples keep this classification even in selected-input mode.
- `false`: selected current-task inputs. Rejected in default mode; admitted only under the explicitly configured selected-input mode. Never rewritten to true.
- String, numeric, null and missing classifications are refused, not coerced. The declaration is not a personal-data or authenticity detector.

Intake metadata, task description, review/recheck, capabilities, OpenAPI and compact views retain the actual declaration. Old intake metadata with a true synthetic field remains synthetic when the service mode changes. Reverting the launch policy to synthetic-only blocks new selected-input intakes and artifact uploads; retained authorized history can still be inspected/reviewed and fresh receipts can still describe it truthfully. Review remains advisory and read-only. Source authenticity, semantics, checklist completeness and privacy stay unverified.

OpenAPI's `synthetic` schema is boolean, constrained to true only in default mode. Live capabilities/OpenAPI show the launch mode and the byte limit. Both fields are included in configuration binding; a policy/quota change stales old assurance when explicitly rechecked. No continuous observer is implied.

## Stored-byte quota

Default: **268,435,456 bytes (256 MiB) per configured owner**, operator configurable as a positive integer. Counts are based on **actual logical regular-file bytes** (`st_size`), not only the known task/version counters. Historical evidence, legacy indexes, frozen requests/sources, every evaluation copy, outer version bytes, metadata, receipt JSON, compact view and immutable artifact snapshots all count. Symlinked or special owner-store entries are refused. No prior data or completed receipt is removed to recover room. Existing stores already above the limit stay available for read-only review, while growth is refused.

The existing single-process per-owner lock protects accounting and publication. Version and receipt payloads have exact projected totals computed before staging, followed by an exact owner-file recount before atomic publication. Intake uses a conservative bounded preflight reservation for its temporary selected-source preparation and frozen copies, followed by an exact recount of all staged files and metadata before its atomic rename. The intake safety reservation can reject near the limit before the final retained bytes alone would fill it; it is not silently charged as persistent data. New aborted staging is cleaned, never existing task state. These are logical file-byte limits, not filesystem block/inode quotas or a distributed/multi-worker storage transaction. Normal filesystem overhead, operator logs and other apps' storage still need host-level headroom/management.

A quota refusal returns **409** with `Stored-byte quota exceeded` and retained/projected/limit byte counts. It leaves no committed partial intake, version or receipt and never deletes earlier bytes. Idempotent reads/replays that do not grow stored data remain usable. Failure diagnostics log only operation and byte counts to the operator's stderr/journal, **outside committed task state**, without inputs, file bodies, keys or request text. The application creates no unbounded failure-log file bypassing its own quota. Durable journal retention/rotation belongs to the coordinator's existing host logging setup; this source checkpoint does not claim that external log retention is configured. Failed original consumer trials and independent observations are unchanged.

## Validation and handoff

All new “selected input” tests use manufactured fixtures with `synthetic:false` to exercise truthful labeling; there is no actual user content in Git or the package. Existing shipped fixtures remain declared synthetic. Tests cover default refusal, explicit admission, boolean typing, historical classification, mode reversion, truthful receipts/views, live HTTP/MCP capabilities, unchanged persistent bytes during MCP, per-owner isolation, and intake/upload/receipt quota conflicts with earlier bytes preserved. Actual retained extra files count, rather than a cached size estimate. Original validation and independent regressions remain required.

Reproduce with existing pinned Python3.12 dependencies:

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests_connector -v
PYTHONPATH=. .venv/bin/python tests_connector/test_http_protocol.py --selected-task-inputs --output /tmp/stardive-selected-policy-1
```

The second command uses real loopback HTTP/MCP with synthetic credentials and manufactured contents declared as selected inputs. It proves mechanics/classification, not native Muse automatic invocation, live credentials or externally reachable HTTPS. Setup and observed app acceptance remain the coordinator's work.

Mac is reported synced at `63cb32f61109b9990f254a74fc622c3a278f9942`, with both independent 14-check sets and all196 tests passing. Preserve its docs-only differences, staged/unstaged work and excluded raw generated report. Apply only the packaged incremental patch from550df98 after inspecting status and `git apply --check`; no full snapshot overlay or unrelated-history merge. This change does not alter earlier docs-only files, original fixtures, taskflow/native checkers, or existing stdio entrypoints.
