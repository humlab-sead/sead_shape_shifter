# Proposal: Allow Operators To Create Change Request Target Bundles

## Status

- Proposed change
- Scope: Change Request target-bundle creation without a caller-supplied source file
- Goal: let any authenticated operator create a target bundle from an authorized saved project, with no caller-supplied source path, for downstream review by the SEAD Release Cycle
- Depends on the composed in-memory path in [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md)

## Summary

Allow any authenticated operator to create a Change Request target bundle from an authorized saved project, with no caller-supplied source file, without the `application:run_ingesters` permission. The tables for that path come from normalizing the authorized project in memory, as defined in [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md). Shape Shifter writes the bundle to a managed output location. Bundle creation may run read-only verification queries against the target database but must not modify target data or consume sequence values. The SEAD Release Cycle remains responsible for downstream quality assurance.

## Problem

Change Request target-bundle creation produces files for a later release process; it does not update a target database. The operation that needs the relaxed permission also reads no caller-supplied source path: its tables come from normalization of an authorized saved project ([IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md)). Requiring the special ingester permission limits this file-generation operation more than its impact warrants. Fine-grained source, project, and database authorization would add complexity without changing the downstream review process.

## Scope

- Allow any authenticated operator to create a Change Request target bundle from an authorized saved project, with no caller-supplied source path, without `application:run_ingesters`.
- Write the bundle only to an application-managed output location.
- Limit target-database access in this operation to read-only verification queries.
- Leave authorization for all other ingester operations and for bundle creation from an uploaded source file unchanged.

## Non-Goals

- Changing the `application:run_ingesters` requirement for other ingester operations.
- Relaxing the `application:run_ingesters` requirement for bundle creation from a caller-supplied source path. That route keeps its current gate until the read exposure recorded as `R3` in [REVIEW.md](./REVIEW.md) is closed.
- Adding per-project or per-source authorization for Change Request bundle creation.
- Moving the SEAD Release Cycle's review or quality-assurance responsibilities into Shape Shifter.
- Implementing granular Change Request ingester security, which can be reconsidered separately.

## Current Behavior

The ingestion route requires `application:run_ingesters`; its request includes source and output paths. That route-level permission does not distinguish Change Request target-bundle creation from operations with different effects. See the [ingester route](../../../backend/app/api/v1/endpoints/ingesters.py), [request models](../../../backend/app/models/ingester.py), and [ingester service](../../../backend/app/services/ingester_service.py).

## Proposed Design

Allow authenticated operators to create Change Request target bundles from an authorized saved project, with no caller-supplied source path, without the `application:run_ingesters` permission. Limit this exception to that composed path; keep the existing gate for other ingester operations and for bundle creation from an uploaded source file.

Write each generated bundle under an application-managed output location in a run-specific folder whose name includes a UTC timestamp. If the destination already exists, fail without modifying it. Do not let bundle creation overwrite or remove unrelated files.

Bundle creation may connect to the target database for read-only verification queries only. This covers the fixed `data_provider` row confirmation required by the provider-scope cutover ([PROJECT_DATA_PROVIDER_SCOPE](../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md)) and any target-row collision checks the ingester runs. Bundle creation must not insert, update, or delete target rows, and must not call `nextval` or otherwise consume sequence values; reserving target IDs stays out of generation. The SEAD Release Cycle handles review and quality assurance after bundle creation.

## Risks And Tradeoffs

- More operators can create bundles, including bundles that may need correction during the SEAD Release Cycle.
- Managed output paths and the read-only target-database rule keep this operation's side effects limited to the intended files; read-only verification queries add a target-database dependency, so bundle creation fails when the provider-row confirmation cannot run.
- Timestamped folders avoid replacing earlier bundles but accumulate output; [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550) tracks a future review of this naming and retention choice.

## Testing And Validation

- Confirm an authenticated operator without `application:run_ingesters` can create a target bundle from an authorized saved project with no caller-supplied source file, and an unauthenticated caller cannot.
- Confirm bundle creation from a caller-supplied `.xlsx`/`.xls` path still requires `application:run_ingesters`.
- Confirm each run writes to a timestamped folder under the managed output location; a destination collision fails without modifying existing files.
- Confirm bundle creation does not overwrite or remove unrelated files.
- Confirm bundle creation runs only read-only verification queries against the target database: no target-table write and no sequence allocation (`nextval`) occurs.
- Confirm other ingester operations retain their existing authorization requirement.

## Acceptance Criteria

- `P-AC-1` A bundle created from an authorized saved project with no caller-supplied source path — the [in-memory handoff](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) — requires only an authenticated operator and not `application:run_ingesters`; unauthenticated callers are rejected. Bundle creation from a caller-supplied source path keeps its current `application:run_ingesters` requirement until that read path is constrained.
- `P-AC-2` Each run writes to a timestamped folder under the managed output location. A destination collision fails without modifying existing files, and bundle creation cannot overwrite or remove unrelated files.
- `P-AC-3` Bundle creation limits target-database access to read-only verification queries. It does not insert, update, or delete target rows and does not consume sequence values.
- `P-AC-4` Authorization for other ingester operations is unchanged.
- `P-AC-5` Repeated bundle generation for the same stable SIMS source identity reuses its assigned target ID; retrying an allocation batch uses the same run ID and payload.

## Planning Handoff

- Apply the permission exception only to the composed path defined by [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md); keep the gate on the caller-path route. This work depends on that proposal's `P-AC-1` and `P-AC-8`.
- Keep each run's output in its own UTC-timestamped folder under an application-managed location; fail if that destination already exists. Do not add project/source authorization or target-database selection for this operation.
- Leave downstream review and quality assurance to the SEAD Release Cycle.
- Reconsider timestamped folder naming and retention under [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550).
- Keep SIMS identity resolution idempotent by using the entity's configured business `keys` as source identity, and preserve the same run ID and payload when retrying an allocation batch. Preserve deployment-time sequence synchronization in generated SQL.
- Do not allocate database-sequence IDs during bundle generation. Non-SIMS-tracked entities that require such IDs must have them pre-resolved before generation or be rejected as unsupported. Bundle generation may run read-only verification queries against the target database but must not modify target data or call `nextval`.
- Align Phase 4 of the [Security Hardening Follow-up phase plan](../SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP_PHASE_PLAN.md) with these decisions.

## Final Recommendation

Approve the narrow permission exception for Change Request target-bundle creation. Defer more granular security controls for this operation unless a later review identifies a need for them.
