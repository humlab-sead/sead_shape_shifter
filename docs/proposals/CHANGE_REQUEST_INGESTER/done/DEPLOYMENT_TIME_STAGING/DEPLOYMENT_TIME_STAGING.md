# Change Request: DEPLOYMENT_TIME_STAGING

## Status

- **Implemented** (branch `deployment-time-staging`; merged in [PR #565](https://github.com/humlab-sead/sead_shape_shifter/pull/565)).
- **Scope:** Model-driven deployment-time ID resolution and foreign-key mapping for supported non-SIMS aggregate children using inline staging.
- **Goal:** Let release SQL generate child IDs while preserving local parent-child references from the submitted bundle.
- **Validation:** The inline staging SQL-builder test module passed before the PR was merged.
- **Remaining follow-up:** Copy-CSV staging parity and promotion through the supported Sqitch release path remain separate work.

## Summary

The Change Request Ingester currently needs concrete target IDs before it can render SQL. It reserves PostgreSQL sequence values while creating the bundle, then projects those IDs into child foreign keys. This consumes sequence values before the SEAD Release Cycle applies the bundle.

This proposal replaces generation-time sequence reservation for non-SIMS aggregate children with temporary staging tables. Staging rows retain Shape Shifter `system_id` values and local foreign-key references. The bundle also carries known target IDs for reference-only rows needed by staged FKs. During deployment, SQL obtains sequence IDs for staged rows, maps local IDs to target IDs, resolves target FKs, checks configured `unique_sets`, and inserts the rows into SEAD tables. The generated bundle contains no numeric target IDs for newly inserted children. Generation-time target collision checks remain for known IDs and fully resolved derived-bridge unique sets.

The target model determines which entities are aggregate children; deployment checks whether each target table supports the required ID generation. The bundle does not use a fixed entity-name allowlist.

## Problem

Aggregate-child IDs do not need SIMS identity management when they only identify rows inside the submitted aggregate. The target tables still need primary keys, and a child row may need its parent's generated target ID.

The current bundle is rendered only after every inserted row has a resolved target ID. This works by reserving sequence IDs during bundle generation, but it requires target-database access at that point. Simply omitting a parent ID from an `INSERT` is not enough when submitted child rows refer to that parent: the generated ID must be captured and mapped back to the child's local FK.

The target-model review identifies `sample_dimension` and `geochronology` as leaf examples, and `analysis_value` and `abundance` as intermediate parents whose IDs are referenced by submitted child rows. See [the aggregate-child review](../../../../../resources/target_models/TARGET_MODEL_REVIEW_20261013.md) and [the SEAD target model](../../../../../resources/target_models/sead_standard_model.yml).

## Scope

- Use database-generated target IDs for model-defined non-SIMS aggregate children when the deployed target table provides a supported sequence or identity default. A tracked fact root must be newly inserted with a SIMS-assigned ID; a reconciled root may already exist with a known target ID, supplied directly or resolved through reconciliation.
- Preserve local `system_id` values and local FK references in deployment staging data, separately from target IDs and target FK values.
- Resolve target IDs and child FKs while the Release Cycle applies the generated SQL.
- Provide equivalent behavior for the inline-INSERT and copy-CSV deploy strategies.
- Keep SIMS-assigned IDs for tracked aggregates and preserve their required target-sequence synchronization.
- Retain generation-time target collision checks for known target IDs and fully resolved derived-bridge `unique_sets` as quality-of-service diagnostics. Check complete `unique_sets` after deployment-time FK resolution, whether or not the target table has a matching unique constraint.

## Non-Goals

- Changing SIMS identity or allocation rules for tracked aggregates.
- Allocating IDs for new shared lookup values that SIMS does not support.
- Creating new `value_type` roots through MVP submissions or deciding the semantic role of `value_type_item`. A child of an existing, resolved `value_type` is not excluded by its parent's reconciled identity.
- Adding children to or replacing an existing tracked fact aggregate.
- Applying the bundle during generation or connecting to the target database to reserve child IDs.
- Removing the existing read-only target collision checks during generation.
- Handling repeated imports or resubmissions of the same submission. Only one generated bundle for a submission is handed to the Release Cycle. Re-submission and existing-row updates are covered separately by [Ingester Idempotency And Re-submission](../../../CHANGE_REQUEST_INGESTER_POST_MVP/INGESTER_IDEMPOTENCY_AND_RESUBMISSION/INGESTER_IDEMPOTENCY_AND_RESUBMISSION.md) and [Sead Change Request Update Handling For Existing Rows](../../../CHANGE_REQUEST_INGESTER_POST_MVP/UPDATE_HANDLING_FOR_EXISTING_ROWS.md).
- Replacing the closed MVP Delivery baseline or reopening its unrelated identity, confirmation, and collision decisions.
- Implementing a separate revert/rollback artifact, updates, or deletes. Transactional rollback when deployment fails is required.

## Current Behavior

- `orchestrate_identity_assignments` handles `database_sequence` rows by calling the injected target ID allocator. The runtime adapter reserves IDs with PostgreSQL `nextval` during bundle generation.
- Target projection maps each local parent `system_id` to its already-resolved target ID before the deploy artifact is rendered.
- Package assembly currently omits reference-only rows after using their IDs for target projection. The generated artifact therefore does not carry their local-to-target ID mappings.
- Both deploy strategies currently emit projected values. The inline writer emits static `INSERT` statements; the copy-CSV writer copies directly into target tables. They preserve package-table order and do not capture a target-generated parent ID for later child rows.
- The generated SQL can defer constraints declared deferrable, but deferring FK checks does not provide generated ID values or populate child FKs.
- Generation runs read-only target collision checks before rendering the bundle. For rows to insert, these check projected `public_id` values; for derived bridge rows, they check configured `unique_sets`. They do not check for duplicate unique sets among submitted rows. The current checks reject unresolved child IDs, so this proposal must limit target-ID checks to IDs known during generation. They can detect conflicts with rows already in the target, but they do not make repeated imports idempotent and do not replace target constraints at deployment.

The completed MVP follow-up deliberately kept the copy-CSV strategy as direct `\copy` into target tables and left temp-table staging outside that artifact contract. This proposal introduces staging as a separate capability for generated-ID resolution; it does not change the historical baseline in place. See [the completed MVP follow-up record](../CHANGE_REQUEST_INGESTER_MVP/MVP_FOLLOWUP_CR.md).

## Proposed Design

Determine eligible entities from the reviewed target model using its shared effective-identity rules. An entity is an aggregate child when its effective `identity_tracking` is `child` and its `aggregate_parent` chain is valid and acyclic. Do not require the chain to end at a tracked entity: the root may also be a reconciled entity with a known target ID. A separately tracked entity starts its own aggregate. A new child can be inserted only when its root has a resolved target ID. For a tracked fact root, this submission must insert the root; a new child may also refer to an existing reconciled root. The reviewed model makes `analysis_entity` a child of the tracked `dataset`; `value_type_item` remains a child of the reconciled `value_type`. New `value_type` roots are outside MVP submission support. Do not infer aggregate membership from an entity's role, ordinary foreign keys, or generated-column metadata. Use no manually maintained entity-name allowlist.

At deployment, verify from the target schema that each eligible entity's `public_id` column has a supported sequence or identity generator. Resolve each model `target_table` to one target relation and use its schema-qualified name and ID-column metadata to locate the associated sequence; reject missing or ambiguous relations. If the model relationship is invalid or the deployed column has no supported generator, fail before inserting target rows. Effective child identity and the deployed schema determine eligibility; the existing `public_id_generation: database_sequence` field, which currently triggers reservation during bundle generation, is not an opt-in requirement for this change. Phase 1 reviews the relevant aggregate-parent assignments and produces a derived inventory of eligible entities and their target ID-generation mechanisms; that inventory is for validation, not a hard-coded runtime allowlist.

1. Load submitted insert rows into temporary staging tables. Retain each row's local `system_id` and local FK values. Keep separate staging fields for local FK IDs and resolved target FK values; do not overwrite a local reference before it has been resolved.
2. Create a deployment-local ID map keyed by `(entity, system_id)`. The generated artifact must carry `(entity, system_id, target ID)` records for reference-only rows used by staged FKs, even though those rows are not inserted. Seed the map with those records and SIMS assignments. Reject duplicate local keys or conflicting target-ID assignments; different local references may point to the same existing target row.
3. For new, sequence-backed non-SIMS aggregate children, lock affected target tables in a stable order before inspecting their IDs or changing their sequences. Synchronize each sequence above existing target IDs when needed, then obtain IDs from it during deployment, for example with `nextval(pg_get_serial_sequence(...))`. Hold the locks through target insertion. The supported release workflow excludes concurrent inserts or independent sequence allocation on these tables. Verify sequence cache behavior and reject a generator that cannot be synchronized safely. Store allocated IDs in staging and the ID map. The bundle contains the SQL needed to allocate IDs, never preassigned numeric child IDs. Do not calculate IDs from `MAX(public_id)` or infer a mapping from row order or payload values.
4. Resolve each local FK through the ID map. Require exactly one target ID for every required relationship. After FK resolution, check each complete configured `unique_set` among staged insert rows and against existing target rows, for both child facts and derived bridges. A complete set has all columns present and non-null. Reject duplicate sets and missing or ambiguous FK mappings before target-table inserts. Generation-time target checks run only for IDs and unique-set values already known; unresolved child IDs do not block bundle generation.
5. Insert the staged rows into target tables in dependency order, explicitly using the IDs and FKs resolved in staging. For `GENERATED ALWAYS AS IDENTITY` columns, use the PostgreSQL-supported override needed to insert the sequence value explicitly. Reject tables whose ID-generation behavior cannot be supported safely.
6. Allocate sequence IDs only for rows that need a new non-SIMS aggregate-child ID. Do not mix staged and direct target inserts within an ID/FK dependency graph. Require the supported dependency graph to be acyclic and report a clear error for cycles.
7. Run staging loads, sequence allocation, ID mapping, and target inserts in one deployment transaction. Define temporary tables with `ON COMMIT DROP`; require the release runner to use `psql` with `ON_ERROR_STOP=1` or equivalent fail-fast behavior for SQL and `\copy` errors. Validate that no required FK mapping remains unresolved before committing. Preserve the existing sequence-synchronization behavior for explicit SIMS IDs.
8. Treat the generated change request as one normal transactional Sqitch change. Sqitch's deployment registry is authoritative for retries: a retry must check whether the change is already deployed rather than replaying its SQL outside Sqitch. The release runner must report Sqitch failures and must not run post-deploy hooks for a failed change. A failed change rolls back target rows; sequence values consumed before failure may leave gaps. No separate duplicate-application mechanism is required under this deployment contract.

Both deploy strategies must use this same ID-resolution contract. The copy-CSV strategy can load payload files into staging tables before target insertion. The inline strategy can populate staging rows from its generated SQL. The strategy may differ in how it loads staged rows, but not in how it allocates sequence IDs, validates the map, or resolves FKs. During Phase 2, the current direct-to-target renderer remains the default while an inline staging bundle is validated separately. Promotion in Phase 3 replaces that default for supported submissions; direct insertion is not a fallback for unresolved staged child IDs.

The older Clearinghouse transport system's `local_db_id` field is prior art for retaining a local row ID beside target rows. This proposal adopts that data-flow idea without requiring the current bundle to reproduce the legacy script or its surrounding workflow.

## Alternatives Considered

- **Keep reserving `nextval` during bundle generation.** This produces concrete IDs for static SQL, but requires a target connection and advances sequences before deployment.
- **Capture IDs with `INSERT ... RETURNING`.** A row-at-a-time insert could associate each returned ID with its staging `system_id`, but would give up bulk target inserts. It may be reconsidered for a generator that cannot be allocated safely in staging. The recommended sequence allocation still happens when the release SQL runs, not while Shape Shifter creates the bundle.
- **Allocate child IDs in Shape Shifter.** Rejected because a local allocator cannot safely coordinate with target sequences and would create collision and synchronization risks.

## Risks And Tradeoffs

- Staging adds SQL and temporary data to the deploy artifact. Both output strategies need disposable-database coverage.
- PostgreSQL sequence values are not rolled back with a failed transaction. Synchronizing an out-of-date sequence or allocating child IDs may leave gaps after failure; this is acceptable for internal child IDs but must not be mistaken for SIMS identity allocation.
- Table locks block other writers while IDs are synchronized and rows inserted. The release workflow must exclude concurrent writes and independent sequence allocation on affected tables; unsafe sequence cache behavior must fail closed.
- Some identity columns require special handling when an explicit sequence value is inserted. Unsupported defaults, triggers that rewrite IDs, or missing sequences must fail closed.
- Temporary-table definitions and insert behavior must match the deployed target schema, including required columns, sequence defaults, ID types, and constraints.
- Replaying the generated SQL outside Sqitch or deploying without the normal per-change transaction would violate the retry and atomicity assumptions. Such deployment modes are unsupported.
- The Change Control tag-deploy wrapper currently checks Sqitch's result before running post-deploy hooks. Validate that this path, and any other supported release path, stops on SQL or `\copy` errors and does not run post-deploy hooks after a failed change before staging is promoted.
- Generation-time collision checks are read-only diagnostics and can become stale before deployment. Deployment checks enforce complete model `unique_sets` after FK resolution; target primary-key and unique constraints provide additional protection where they exist.

## Testing And Validation

- On a disposable SEAD-compatible PostgreSQL database, deploy a parent and multiple children whose target IDs are generated by sequences. Verify each FK points to the correct generated parent.
- Cover a multi-level chain such as `analysis_value` and its typed child rows, and `abundance` and its child rows.
- Cover leaf children such as `sample_dimension` and `geochronology`, and confirm the target generates their IDs without requiring those IDs in the bundle.
- Cover a mixture of reference-only rows with known target IDs, SIMS-assigned IDs, and new sequence-generated child IDs. Confirm that the bundle carries mappings for referenced rows that it does not insert.
- Cover a new child attached to an existing reconciled `value_type`. Reject a child attached to an existing tracked fact root and a new root whose creation is outside MVP support.
- Start with a child sequence behind the target table's highest ID; verify deployment locks the table before synchronization and advances the sequence without reusing an existing ID. Check the deployed sequence cache behavior.
- Include distinct staging rows with identical non-ID payloads and vary their input order; verify that each local ID maps to the correct target ID.
- Verify duplicate local-ID mappings, conflicting assignments, unresolved required FKs, unsupported ID-generation mechanisms, and dependency cycles fail before target rows are committed. Reject duplicate submitted `(abundance_id, modification_type_id)` and `(abundance_id, identification_level_id)` pairs after FK resolution, including when `abundance_id` is generated during deployment. Reject a complete unique-set match against an existing target row under a reconciled parent.
- Run the same relationship cases through inline-INSERT and copy-CSV artifacts.
- Run deployment through the supported release client with error-stop behavior. Force a staging-load and a target-insert failure; verify no partial target rows persist and temporary tables are dropped. Sequence gaps after failure are allowed.
- Verify that a failed Sqitch change can be retried without partial target rows, and that retrying an already-deployed change through Sqitch does not apply it again.
- Confirm generation-time collision checks still report known target-ID and fully resolved derived-bridge `unique_sets` conflicts. A set containing a new child ID must not block generation; deployment checks it after FK resolution. Do not treat generation-time checks as repeated-import protection.
- Verify bundle generation does not call the target sequence allocator for these child rows.
- Verify explicit SIMS IDs still advance the corresponding target sequence after deployment.
- Review aggregate-parent assignments for the MVP entities, derive the candidate inventory, and verify each candidate's deployed sequence or identity behavior before enabling it.

## Acceptance Criteria

- `P-AC-1` Bundle generation does not reserve PostgreSQL sequence IDs for supported non-SIMS aggregate children.
- `P-AC-2` Deployment staging preserves each insert row's local `system_id` and local FK values separately from target IDs and target FK values; local IDs are not written to target tables.
- `P-AC-3` Deployment SQL locks affected target tables before sequence synchronization and allocation, obtains target `public_id` values for new non-SIMS child rows from a supported generator, and maintains one target ID per `(entity, system_id)` to resolve submitted child FKs, including multi-row and multi-level relationships. Generated child ID values are absent from the bundle. Unsupported sequence cache behavior fails before target inserts.
- `P-AC-4` Both inline-INSERT and copy-CSV artifacts preserve the same parent-child mapping and produce valid target-table inserts.
- `P-AC-5` Staging, sequence allocation, ID mapping, and target inserts run in one normal transactional Sqitch change; deployment errors stop execution before success is reported, target rows roll back, and temporary tables are dropped. Retries consult Sqitch's deployment registry rather than replaying a successfully deployed change.
- `P-AC-6` The bundle carries known local-to-target ID mappings for reference-only rows needed by staged FKs without inserting those rows. Existing and SIMS-assigned target IDs continue to work, and required sequence synchronization for explicit SIMS IDs remains intact.
- `P-AC-7` Duplicate local-ID mappings, conflicting target-ID assignments, unresolved or ambiguous required FKs, and duplicate complete `unique_sets` among staged rows or against existing target rows fail before target inserts. This includes child facts and derived bridges whose parent IDs are generated during deployment.
- `P-AC-8` ID mapping remains correct for distinct local rows with identical non-ID payloads and is independent of staging input order.
- `P-AC-9` Unsupported ID-generation mechanisms and dependency cycles fail with actionable diagnostics before target changes are committed.
- `P-AC-10` Eligible entities are derived from effective target-model identity metadata: each is an effective `child` with a valid, acyclic `aggregate_parent` chain ending at a tracked or reconciled root. For each inserted child row, a tracked fact root must be inserted by the same submission, or a reconciled root must have a resolved target ID. Deployment verifies a supported sequence or identity generator for each new child `public_id` and fails before target inserts when the model relationship, root ID, or deployed generator is unsupported.
- `P-AC-11` Generation-time target collision checks remain available for known `public_id` values and fully resolved derived-bridge `unique_sets`. Sets containing child IDs allocated at deployment are checked after FK resolution and do not block generation. Generation-time checks are quality-of-service diagnostics, not protection against repeated imports.

## Planning Handoff

- Keep the closed MVP Delivery identity behavior for tracked aggregates. This proposal changes only deployment-time ID resolution for non-SIMS aggregate children.
- Use the shared effective-identity resolver and `aggregate_parent` relationships to identify children, without a separate root marker or hard-coded entity allowlist. Insert a tracked fact root with its children in the same submission; allow children of an existing reconciled root with a known target ID. Do not extend or replace an existing tracked fact aggregate. The reviewed model makes `analysis_entity` a child of `dataset`.
- In Phase 1, confirm aggregate-parent assignments for the MVP entities and derive and validate their eligibility against deployed sequence and identity metadata. Unrelated target-model role decisions do not block this work.
- Use the submitted local `system_id` values and local FKs as the stable relationship keys throughout staging. Carry mappings for reference-only rows needed by staged FKs in the artifact even though those rows are not inserted.
- Allocate supported non-SIMS child IDs from target sequences when the Release Cycle applies the bundle, not while Shape Shifter builds it. Exclude concurrent writes to affected tables; lock them in stable order before synchronizing or allocating sequence IDs, and verify sequence cache behavior. Do not use `MAX(public_id) + 1` as an independent allocator.
- Preserve one target `public_id` per `(entity, system_id)`; different local references may point to the same existing target row. Do not infer mappings from returned row order or non-ID payload values.
- Resolve target FKs separately from local FK values and reject missing or ambiguous mappings before target inserts. After resolution, reject complete `unique_sets` duplicated within staged rows or already present in target tables, including child facts and derived bridges.
- Support an acyclic dependency graph initially; reject cycles until a separate design supports them.
- Validate sequence defaults, identity-column behavior, FK constraints, and execution error handling against the deployed target schema before enabling an entity.
- Deploy each generated change through Sqitch's normal transactional, registry-aware workflow. Failed changes may consume sequence values, but must not leave target rows; retries must consult the Sqitch registry.
- Preserve generation-time collision checks for known IDs and fully resolved derived-bridge unique sets as optional read-only quality-of-service diagnostics. Allow new child IDs to remain unresolved until deployment; check their complete unique sets after FK resolution. The staging change moves child sequence allocation and FK resolution to deployment; it does not impose a no-target-database-access rule on the complete generation flow.
- During Phase 2, validate inline staging separately while current artifacts remain the default. After Phase 3 promotion, do not fall back to direct target insertion or generation-time reservation for an unresolved staged child. Never write local `system_id` values to target tables.
- Verify the supported Change Control release paths propagate Sqitch errors. For the tag-deploy path, confirm that failed changes skip post-deploy hooks before accepting transactional deployment behavior.
- Only one generated bundle for a submission is handed to the Release Cycle. Repeated imports, resubmission idempotency, and updates to existing rows remain outside this proposal and follow their separate proposals.

## Final Recommendation

Adopt model-driven deployment-time staging and allocate sequence-backed child IDs when the release SQL runs. This preserves a deterministic mapping from local IDs to target IDs without relying on the order of `RETURNING` rows. Include children of resolved reconciled parents and newly inserted tracked fact roots, verify each deployed ID generator, and use Sqitch's normal transactional, registry-aware deployment path. Validate mapping, unique-set checks, and both deploy strategies on a disposable database before enabling the change.
