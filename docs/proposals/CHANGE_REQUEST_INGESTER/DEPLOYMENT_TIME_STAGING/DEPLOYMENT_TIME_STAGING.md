# Change Request: DEPLOYMENT_TIME_STAGING

## Status

- Proposed follow-up change request for the Change Request Ingester MVP workstream
- Scope: model-driven deployment-time ID resolution for non-SIMS aggregate children
- Goal: let SEAD generate child primary keys when the release SQL runs while preserving local parent-child references from the submitted bundle

## Summary

The Change Request Ingester currently needs concrete target IDs before it can render SQL. It reserves PostgreSQL sequence values while creating the bundle, then projects those IDs into child foreign keys. This consumes sequence values before the SEAD Release Cycle applies the bundle.

This proposal replaces generation-time sequence reservation for non-SIMS aggregate children with temporary staging tables. Staging rows retain Shape Shifter `system_id` values and local foreign-key references. During deployment, SQL obtains sequence IDs for staged rows, builds a deterministic map from local IDs to target IDs, resolves target FKs, and inserts the rows into SEAD tables. Existing read-only target collision checks may remain during generation as quality-of-service checks; moving child-ID allocation does not require removing them.

The target model determines which entities are aggregate children; deployment checks whether each target table supports the required ID generation. The bundle does not use a fixed entity-name allowlist.

## Problem

Aggregate-child IDs do not need SIMS identity management when they only identify rows inside the submitted aggregate. The target tables still need primary keys, and a child row may need its parent's generated target ID.

The current bundle is rendered only after every inserted row has a resolved target ID. This works by reserving sequence IDs during bundle generation, but it requires target-database access at that point. Simply omitting a parent ID from an `INSERT` is not enough when submitted child rows refer to that parent: the generated ID must be captured and mapped back to the child's local FK.

The target-model review identifies `sample_dimension` and `geochronology` as leaf examples, and `analysis_value` and `abundance` as intermediate parents whose IDs are referenced by submitted child rows. See [the aggregate-child review](../../../../resources/target_models/TARGET_MODEL_REVIEW_20261013.md) and [the SEAD target model](../../../../resources/target_models/sead_superset_model.yml).

## Scope

- Use database-generated target IDs for model-defined non-SIMS aggregate children when the deployed target table provides a supported sequence or identity default.
- Preserve local `system_id` values and local FK references in deployment staging data, separately from target IDs and target FK values.
- Resolve target IDs and child FKs while the Release Cycle applies the generated SQL.
- Provide equivalent behavior for the inline-INSERT and copy-CSV deploy strategies.
- Keep SIMS-assigned IDs for tracked aggregates and preserve their required target-sequence synchronization.
- Retain existing generation-time target collision checks as quality-of-service diagnostics; they are not an idempotency guarantee.

## Non-Goals

- Changing SIMS identity or allocation rules for tracked aggregates.
- Allocating IDs for new shared lookup values that SIMS does not support.
- Applying the bundle during generation or connecting to the target database to reserve child IDs.
- Removing the existing read-only target collision checks during generation.
- Handling repeated imports or resubmissions of the same submission. Only one generated bundle for a submission is handed to the Release Cycle. Re-submission and existing-row updates are covered separately by [Ingester Idempotency And Re-submission](../../CHANGE_REQUEST_INGESTER_POST_MVP/INGESTER_IDEMPOTENCY_AND_RESUBMISSION/INGESTER_IDEMPOTENCY_AND_RESUBMISSION.md) and [Sead Change Request Update Handling For Existing Rows](../../CHANGE_REQUEST_INGESTER_POST_MVP/UPDATE_HANDLING_FOR_EXISTING_ROWS.md).
- Replacing the closed MVP Delivery baseline or reopening its unrelated identity, confirmation, and collision decisions.
- Implementing a separate revert/rollback artifact, updates, or deletes. Transactional rollback when deployment fails is required.

## Current Behavior

- `orchestrate_identity_assignments` handles `database_sequence` rows by calling the injected target ID allocator. The runtime adapter reserves IDs with PostgreSQL `nextval` during bundle generation.
- Target projection maps each local parent `system_id` to its already-resolved target ID before the deploy artifact is rendered.
- Both deploy strategies currently emit projected values. The inline writer emits static `INSERT` statements; the copy-CSV writer copies directly into target tables. They preserve package-table order and do not capture a target-generated parent ID for later child rows.
- The generated SQL can defer constraints declared deferrable, but deferring FK checks does not provide generated ID values or populate child FKs.
- Generation runs read-only target collision checks before rendering the bundle. For rows to insert, these check projected `public_id` values; for derived bridge rows, they check configured `unique_sets`. This proposal leaves those quality-of-service checks in place. They can detect conflicts with rows already in the target, but they do not make repeated imports idempotent and do not replace target constraints at deployment.

The completed MVP follow-up deliberately kept the copy-CSV strategy as direct `\copy` into target tables and left temp-table staging outside that artifact contract. This proposal introduces staging as a separate capability for generated-ID resolution; it does not change the historical baseline in place. See [the completed MVP follow-up record](../done/CHANGE_REQUEST_INGESTER_MVP/MVP_FOLLOWUP_CR.md).

## Proposed Design

Determine eligible entities from the reviewed target model using its shared effective-identity rules. An entity is an aggregate child when its effective `identity_tracking` is `child` and following its `aggregate_parent` relationships reaches exactly one entity with effective `identity_tracking: tracked`. A separately tracked entity starts its own aggregate. Do not infer aggregate membership from an entity's role, ordinary foreign keys, or generated-column metadata. Use no manually maintained entity-name allowlist.

At deployment, verify from the target schema that each eligible entity's `public_id` column has a supported sequence or identity generator. Use the schema-qualified target table and ID-column metadata to locate the associated sequence. If the model relationship is invalid or the deployed column has no supported generator, fail before inserting target rows. The completed model review should produce a derived inventory of eligible entities and their target ID-generation mechanisms; that inventory is for validation, not a hard-coded runtime allowlist.

1. Load submitted rows into temporary staging tables. Retain each row's local `system_id` and local FK values. Keep separate staging fields for local FK IDs and resolved target FK values; do not overwrite a local reference before it has been resolved.
2. Create a deployment-local ID map keyed by `(entity, system_id)`. Seed it with target IDs already known from existing references and SIMS assignments. Reject duplicate local keys or conflicting target-ID assignments.
3. For new, sequence-backed non-SIMS aggregate children, obtain IDs from the target table's associated sequence during deployment, for example with `nextval(pg_get_serial_sequence(...))`, and store them in staging and the ID map. Do not infer an ID from row order or from payload values.
4. Resolve each local FK through the ID map. Require exactly one target ID for every required relationship, and stop before target-table inserts if a mapping is missing or ambiguous.
5. Insert the staged rows into target tables in dependency order, explicitly using the IDs and FKs resolved in staging. For `GENERATED ALWAYS AS IDENTITY` columns, use the PostgreSQL-supported override needed to insert the sequence value explicitly. Reject tables whose ID-generation behavior cannot be supported safely.
6. Stage every supported row through the same mapping flow. Allocate sequence IDs only for rows that need a new non-SIMS aggregate-child ID. Require the supported dependency graph to be acyclic and report a clear error for cycles.
7. Run staging loads, sequence allocation, ID mapping, and target inserts in one deployment transaction. Define temporary tables with `ON COMMIT DROP`; require the release runner to use `psql` with `ON_ERROR_STOP=1` or equivalent fail-fast behavior for SQL and `\copy` errors. Validate that no required FK mapping remains unresolved before committing. Preserve the existing sequence-synchronization behavior for explicit SIMS IDs.
8. Treat the generated change request as one normal transactional Sqitch change. Sqitch's deployment registry is authoritative for retries: a retry must check whether the change is already deployed rather than replaying its SQL outside Sqitch. A failed change rolls back target rows; sequence values consumed before failure may leave gaps. No separate duplicate-application mechanism is required under this deployment contract.

Both deploy strategies must use this same ID-resolution contract. The copy-CSV strategy can load payload files into staging tables before target insertion. The inline strategy can populate staging rows from its generated SQL. The strategy may differ in how it loads staged rows, but not in how it allocates sequence IDs, validates the map, or resolves FKs.

The older Clearinghouse transport system's `local_db_id` field is prior art for retaining a local row ID beside target rows. This proposal adopts that data-flow idea without requiring the current bundle to reproduce the legacy script or its surrounding workflow.

## Alternatives Considered

- **Keep reserving `nextval` during bundle generation.** This produces concrete IDs for static SQL, but requires a target connection and advances sequences before deployment.
- **Capture IDs with `INSERT ... RETURNING`.** This is not the initial approach because a bulk insert does not by itself associate returned rows with staging `system_id` values. It may be reconsidered for a generation mechanism that cannot be allocated safely in staging.
- **Allocate child IDs in Shape Shifter.** Rejected because a local allocator cannot safely coordinate with target sequences and would create collision and synchronization risks.

## Risks And Tradeoffs

- Staging adds SQL and temporary data to the deploy artifact. Both output strategies need disposable-database coverage.
- PostgreSQL sequence values are not rolled back with a failed transaction. Failed deploys may leave gaps; this is acceptable for internal child IDs but must not be mistaken for SIMS identity allocation.
- Some identity columns require special handling when an explicit sequence value is inserted. Unsupported defaults, triggers that rewrite IDs, or missing sequences must fail closed.
- Temporary-table definitions and insert behavior must match the deployed target schema, including required columns, sequence defaults, ID types, and constraints.
- Replaying the generated SQL outside Sqitch or deploying without the normal per-change transaction would violate the retry and atomicity assumptions. Such deployment modes are unsupported.
- Generation-time collision checks are read-only diagnostics and can become stale before deployment. Target primary-key and unique constraints remain the final protection against conflicting rows.

## Testing And Validation

- On a disposable SEAD-compatible PostgreSQL database, deploy a parent and multiple children whose target IDs are generated by sequences. Verify each FK points to the correct generated parent.
- Cover a multi-level chain such as `analysis_value` and its typed child rows, and `abundance` and its child rows.
- Cover leaf children such as `sample_dimension` and `geochronology`, and confirm the target generates their IDs without requiring those IDs in the bundle.
- Cover a mixture of existing references, SIMS-assigned IDs, and new sequence-generated child IDs.
- Include distinct staging rows with identical non-ID payloads and vary their input order; verify that each local ID maps to the correct target ID.
- Verify duplicate local-ID mappings, conflicting assignments, unresolved required FKs, unsupported ID-generation mechanisms, and dependency cycles fail before target rows are committed.
- Run the same relationship cases through inline-INSERT and copy-CSV artifacts.
- Run deployment through the supported release client with error-stop behavior. Force a staging-load and a target-insert failure; verify no partial target rows persist and temporary tables are dropped. Sequence gaps after failure are allowed.
- Verify that a failed Sqitch change can be retried without partial target rows, and that retrying an already-deployed change through Sqitch does not apply it again.
- Confirm the existing generation-time collision checks still report projected target-ID and derived-bridge `unique_sets` conflicts; do not treat these checks as repeated-import protection.
- Verify bundle generation does not call the target sequence allocator for these child rows.
- Verify explicit SIMS IDs still advance the corresponding target sequence after deployment.
- Derive the candidate entity inventory from the completed target model review and verify each candidate's deployed sequence or identity behavior before enabling it.

## Acceptance Criteria

- `P-AC-1` Bundle generation does not reserve PostgreSQL sequence IDs for supported non-SIMS aggregate children.
- `P-AC-2` Deployment staging preserves each submitted row's local `system_id` and local FK values separately from target IDs and target FK values; local IDs are not written to target tables.
- `P-AC-3` Deployment SQL obtains a target `public_id` for each inserted staging row using the target's supported ID-generation mechanism, maintains a unique `(entity, system_id)` mapping, and uses it to resolve submitted child FKs, including multi-row and multi-level relationships.
- `P-AC-4` Both inline-INSERT and copy-CSV artifacts preserve the same parent-child mapping and produce valid target-table inserts.
- `P-AC-5` Staging, sequence allocation, ID mapping, and target inserts run in one normal transactional Sqitch change; deployment errors stop execution before success is reported, target rows roll back, and temporary tables are dropped. Retries consult Sqitch's deployment registry rather than replaying a successfully deployed change.
- `P-AC-6` Existing and SIMS-assigned target IDs continue to work, and required sequence synchronization for explicit SIMS IDs remains intact.
- `P-AC-7` Duplicate local-ID mappings, conflicting target-ID assignments, and unresolved or ambiguous required FKs fail before commit.
- `P-AC-8` ID mapping remains correct for distinct local rows with identical non-ID payloads and is independent of staging input order.
- `P-AC-9` Unsupported ID-generation mechanisms and dependency cycles fail with actionable diagnostics before target changes are committed.
- `P-AC-10` Eligible entities are derived from effective target-model identity metadata: each is an effective `child` whose `aggregate_parent` chain reaches exactly one effective `tracked` root. Deployment verifies a supported sequence or identity generator for each target `public_id` and fails before target inserts when the model relationship or deployed generator is unsupported.
- `P-AC-11` Existing generation-time target collision checks remain available for projected `public_id` values and derived-bridge `unique_sets`. They are documented as quality-of-service diagnostics, not as protection against repeated imports.

## Planning Handoff

- Keep the closed MVP Delivery identity behavior for tracked aggregates. This proposal changes only deployment-time ID resolution for non-SIMS aggregate children.
- Use the shared effective-identity resolver and `aggregate_parent` relationships to identify aggregate roots and children; do not add a separate root marker or hard-coded entity allowlist.
- After the target-model review is complete, derive and validate the eligible-entity inventory against deployed sequence and identity metadata.
- Use the submitted local `system_id` values and local FKs as the stable relationship keys throughout staging.
- Allocate supported non-SIMS child IDs from target sequences when the Release Cycle applies the bundle, not while Shape Shifter builds it.
- Preserve a unique one-to-one mapping from each local row ID to its target `public_id`; do not infer the mapping from returned row order or non-ID payload values.
- Resolve target FKs separately from local FK values and reject missing or ambiguous mappings before commit.
- Support an acyclic dependency graph initially; reject cycles until a separate design supports them.
- Validate sequence defaults, identity-column behavior, FK constraints, and execution error handling against the deployed target schema before enabling an entity.
- Deploy each generated change through Sqitch's normal transactional, registry-aware workflow. Failed changes may consume sequence values, but must not leave target rows; retries must consult the Sqitch registry.
- Preserve generation-time collision checks as optional read-only quality-of-service diagnostics. The staging change moves child sequence allocation and FK resolution to deployment; it does not impose a no-target-database-access rule on the complete generation flow.
- Only one generated bundle for a submission is handed to the Release Cycle. Repeated imports, resubmission idempotency, and updates to existing rows remain outside this proposal and follow their separate proposals.

## Final Recommendation

Adopt model-driven deployment-time staging and allocate sequence-backed child IDs before target inserts. This preserves a deterministic mapping from local IDs to target IDs without relying on the order of `RETURNING` rows. Derive eligible entities from the reviewed aggregate model, verify each deployed ID generator, and use Sqitch's normal transactional, registry-aware deployment path. Validate mapping behavior and both deploy strategies on a disposable database before enabling the change.
