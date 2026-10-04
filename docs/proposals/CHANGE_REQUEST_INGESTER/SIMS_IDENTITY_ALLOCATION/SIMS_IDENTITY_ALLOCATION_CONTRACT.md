# Proposal: Target-Model and SIMS Identity Allocation Contract

## Status

- System ownership is documented: Shape Shifter owns model-driven planning, reconciliation, and artifact checks; the Authority Service owns SIMS identity and allocation behavior. Shape implementation and integration remain pending. The Authority Service's site allocator prototype is verified only against a disposable database.
- Scope: identity work planning and SIMS capability checks in `sead_change_request`
- Goal: use target-model identity rules to plan rows without assuming SIMS supports every entity in the model

## Summary

Use the target model as the source of truth for how each entity is intended to be identified, reconciled, derived, or inherited. Shape Shifter owns reconciliation and decides whether an approved match is reused or a new identity is requested. SIMS owns a configurable, generic identity mechanism for tracked aggregates: it stores each tracked identity and its scoped source identities, mints the aggregate identity values, and guarantees uniqueness within its own store. SIMS does not inspect SEAD tables, map identities to SEAD columns, or enforce SEAD database integrity. SEAD consumes SIMS-issued aggregate identities under a trust contract; every tracked entity represented in SEAD must also have a corresponding SIMS tracked identity.

The target model describes Shape Shifter's identity intent. SIMS configuration determines how the generic identity mechanism handles an entity type. Entity configuration selects behavior; it must not require entity-specific allocator code. Neither system silently substitutes for the other.

## System Ownership

This proposal owns Shape Shifter behavior: interpreting effective target-model identity rules, reconciling source rows, approving matches or misses, checking SIMS capabilities, and blocking artifact generation when required identity values or insertion paths are unavailable.

The Authority Service owns SIMS API semantics, tracked-identity persistence, generic configurable allocation, source-identity associations, and uniqueness within the SIMS identity store. SIMS does not own SEAD table or column mappings, SEAD database constraints, or deployment integrity checks. The [SIMS `target_id` proposal](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/SIMS_TARGET_ID_CONTRACT.md) covers the service response contract. SEAD consumes SIMS-issued aggregate identity values under the agreed trust contract.

The site and sample checks in the candidate verification guide are initial verification examples, not an architectural limit or a requirement for entity-specific code. Production deployment and cutover are outside the current development task; see the [CHANGE_REQUEST_INGESTER cutover and deployment proposal](../CUTOVER_AND_DEPLOYMENT/CHANGE_REQUEST_INGESTER_CUTOVER_AND_DEPLOYMENT_PROPOSAL.md).

## Problem

The target model already defines effective identity behavior through `identity_tracking`, `reconciliation`, and `aggregate_parent`. Target-model validation checks those combinations, and generated SIMS entity-register documentation reports their effective values. The change-request ingester does not use those values to plan identity work. It routes rows by the broader `role` field instead.

This can send an entity to the wrong operation. In the SEAD model, `analysis_entity` has `role: bridge` but explicitly declares `identity_tracking: tracked` and `reconciliation: allocate`; the planner treats every bridge as a derived bridge row. `sample_dimension` has `role: fact` and `aggregate_parent: sample`, so its effective identity mode is `child`; the planner treats it as an allocation candidate. A lookup such as `site` defaults to `reconciled` with `reconcile-exact`, but the planner treats a missing ID as allocation work.

The service currently has entity-specific policy entries and defaults for unlisted names. The resolve endpoint does not expose configured capabilities or distinguish an intentionally configured entity type from an unknown one. The ingester therefore cannot tell whether a requested operation is supported before it calls SIMS. The target architecture is a generic mechanism driven by validated configuration, not allocator branches or bespoke policies coded for individual entity types.

The current Authority Service also has a site allocator prototype and an optional `target_id` response used by Shape Shifter. These are implementation details of the existing integration, not a requirement for SIMS to understand SEAD tables or integer primary-key mappings. The Authority Service proposal owns the generic identity and response contract; this proposal owns how Shape Shifter plans identity work and consumes the response.

## Scope

- Define how Shape Shifter uses the target model's effective identity rules rather than `role` alone.
- Define how Shape Shifter reconciles and approves existing SEAD matches or misses before requesting SIMS work.
- Define a fail-closed compatibility check between planned model operations and SIMS-published capabilities.
- Require the SIMS-issued aggregate identity value needed by each artifact-producing path whose target model declares a `public_id`. Translating it to a target column is Shape Shifter integration behavior, not SIMS schema knowledge.
- Define when Shape Shifter blocks artifacts because an ID, confirmation, or untracked-row insertion path is missing.

## Non-Goals

- Implementing the Authority Service API, allocator, bootstrap, or identity database schema in this proposal; these belong to Authority Service proposals and plans.
- Replacing the target model's identity modes or changing its entity taxonomy.
- Defining SEAD database integrity enforcement, existing-data migration, production rollout, or cutover. These are outside the current development task and tracked in the [operational cutover and deployment proposal](../CUTOVER_AND_DEPLOYMENT/CHANGE_REQUEST_INGESTER_CUTOVER_AND_DEPLOYMENT_PROPOSAL.md).
- Treating the target model as a list of individual runtime identities already stored in SIMS.

## Current Behavior

- The target model permits `tracked`, `reconciled`, `derived`, and `child` identity modes. When fields are omitted, target-model validation and generated documentation infer effective behavior from the entity role and aggregate parent. See [Target Model Guide](../../../TARGET_MODEL_GUIDE.md), [SEAD superset model](../../../../resources/target_models/sead_superset_model.yml), and [identity rules validator](../../../../src/target_model/spec_validator.py).
- The ingester's [`plan_table()`](../../../../ingesters/sead_change_request/planning.py) selects allocation for most roles, reconciliation for classifiers, and derivation for bridges. It does not resolve or use the effective identity mode or reconciliation strategy.
- The SIMS adapter sends an entity name and serialized row values to `POST /identity/resolve`; it has no capability-discovery call. The `IdentityPolicy` class can list explicitly configured entity types internally, but the API does not publish that list. Unknown entity types receive default policy rather than an unsupported-type error.
- The Authority Service returns an optional `target_id` for approved existing matches and has a disposable-verified site allocator prototype. Other entity types still do not return aggregate identity values for allocation. The prototype is not production-ready. See the [SIMS target-ID proposal](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/SIMS_TARGET_ID_CONTRACT.md).
- The active [PostgreSQL contract handoff](../POSTGRESQL_CONTRACT_VALIDATION.md) records that current change-package validation is blocked on this identity contract.

## Proposed Design

### Ownership

The target model owns the intended identity behavior for each entity in a target schema. Its effective `identity_tracking`, `reconciliation`, and `aggregate_parent` values govern which identity work the ingester plans. The entity's semantic `role` remains useful domain metadata, but it is not a substitute for these identity rules.

Shape Shifter owns reconciliation and approval of uncertain matches. SIMS does not inspect SEAD or approve candidate matches. SIMS owns the identity records for tracked aggregates and uses generic, validated configuration to select identity behavior by entity type. The implementation must not contain separate allocator logic for `site`, `sample`, or other named types. Every tracked entity represented in SEAD must have a corresponding SIMS identity; that is a system contract, not a cutover task in this development scope. `identity_tracking: reconciled` describes how Shape Shifter finds an entity and does not determine whether SIMS tracks its aggregate identity. Actual tracked identities are runtime records and must not be used to decide which target-model entities require identity handling.

### Identity identifier roles

Each tracked aggregate has three distinct identifier roles:

- **Aggregate identity value**: an opaque, entity-scoped value minted and stored by SIMS. SEAD may store this value under the trust contract; SIMS does not know its table or column.
- **Tracked UUID**: the stable UUID stored by SIMS and used to refer to the tracked aggregate across systems.
- **Source identity keys**: business, provider, and authority identifiers scoped to a source. They identify or help reconcile a source's representation of an aggregate; they are not SIMS-minted aggregate identities.

SIMS stores each tracked identity with its entity type, aggregate identity value, tracked UUID, and associated scoped source identities. It guarantees uniqueness within that store. Shape Shifter may expose the aggregate identity value as `target_id` to its artifact-building code, but that adapter name does not make SIMS aware of a SEAD table, column, or database constraint. The `site` and `sample` values in the verification guide remain examples of the current integration.

### Model-driven planning

The ingester uses one shared effective-policy resolution path, consistent with target-model validation and documentation generation. It plans identity work from the resolved mode and reconciliation strategy:

- `tracked` entities use the declared allocation flow.
- `reconciled` entities use their declared reconciliation strategy in Shape Shifter. Shape Shifter passes an approved existing aggregate identity value to SIMS for binding, or requests a new tracked identity after an approved miss only when the strategy and SIMS configuration both permit it; `lookup-only` must not become allocation through a fallback.
- `derived` entities use the declared derivation flow and their related rows.
- `child` entities inherit identity through `aggregate_parent`; they are not independently treated as tracked entities.

SIMS mints opaque aggregate identity values using a generic mechanism and entity-scoped configuration. It does not read SEAD sequences or manage SEAD's relational keys. Child and derived rows, including untracked bridge rows such as `site_location`, do not receive independent SIMS tracked identities unless the domain model defines them as tracked aggregates. Their storage keys and insertion paths belong to the target-system integration. No artifact is emitted while a required aggregate identity value or insertion path is missing.

### Allocation, commit, and rerun

SIMS is the sole minter of tracked aggregate identity values. Its generic allocator uses SIMS-owned state and enforces uniqueness within the SIMS identity store. It does not call SEAD, use SEAD sequences, or know how SEAD stores the returned value. SEAD consumes the value under the trust contract. This does not assign SIMS responsibility for untracked bridge or child keys, target table mappings, or SEAD database integrity.

The target-state contract requires every tracked entity represented in SEAD to have a corresponding SIMS tracked identity. Establishing that condition for existing production data is a separate operational migration and cutover task. It is not part of the current development task. A source identity without a binding does not by itself prove that a new aggregate identity should be minted; Shape Shifter owns reconciliation and approval.

SIMS assigns and persists an aggregate identity value with each new tracked identity before returning success. Keep the value with the tracked identity while it is in the `ALLOCATED` state; a separate reservation state is not needed. Re-resolving the same source identity returns the same tracked UUID and aggregate identity value. An ingester rerun must not mint a second identity or value for that same entity. An approved match binds to the existing tracked identity using its entity type and aggregate identity value without allocating another identity.

For a distinct run, SIMS reuses an existing confirmed binding. If the source identity belongs to a still-proposed Binding Set from an earlier run, SIMS returns a stable pending-identity conflict and does not mint another tracked identity or aggregate identity value. A request that supplies an approved existing value conflicting with a confirmed binding also fails rather than remapping it silently. Runs for the same source identity are serialized in SIMS so concurrent requests cannot both pass the binding check and allocate separate identities. Resolving or abandoning a pending set is an operator action in the initial release; automatic expiry or supersession is deferred.

Do not release or recycle an allocated aggregate identity value. If its package is abandoned, the allocation remains in SIMS. This keeps retries idempotent and prevents an identity value from being reassigned to a different tracked aggregate.

SIMS does not check whether an aggregate identity value conflicts with a value already stored in SEAD. SEAD is responsible for its own persistence integrity. The SIMS–SEAD contract trusts that SEAD consumes identities minted by SIMS and does not create tracked aggregate identities independently. SEAD database constraints, collision handling, and operational cutover are outside the current development task.

Package withdrawal or supersession before deployment, and the gate for regenerated packages, are operational responsibilities covered by the [cutover and deployment proposal](../CUTOVER_AND_DEPLOYMENT/CHANGE_REQUEST_INGESTER_CUTOVER_AND_DEPLOYMENT_PROPOSAL.md). A SIMS Binding Set status is audit state; it does not revoke generated SQL.

### One SIMS batch per ingester run

For one artifact-producing ingester run, Shape Shifter collects all rows that require SIMS identity work and sends them in one `POST /identity/resolve` request. The endpoint already accepts a list of resolution requests and creates one Submission and one Binding Set per call. If no rows require SIMS work, Shape Shifter skips the request.

SIMS returns outcomes in the same order as the requests. The ingester does not call the confirmation endpoint automatically. SIMS may auto-confirm a set only when policy allows auto-confirmation for every entity in the batch. A proposed set blocks artifact generation; the initial release supports only auto-confirmable entities. Supporting manual-review entities requires an explicit review and confirmation step before artifact generation.

Each ingester run has a stable run ID used as its idempotency key, scoped to the SIMS source scope. The ingester persists and reuses that ID for retries; a later intentional run gets a new ID even if its payload is identical. SIMS stores the key, a canonical fingerprint of the request body, and the completed result. It serializes requests with the same key using a database lock and enforces a unique key constraint. The same key and fingerprint return the original Submission, Binding Set, and outcomes; the same key with a different fingerprint returns a conflict. The key, Submission, source-identity resolution, tracked-identity allocations, bindings, Binding Set, and target IDs are committed in one database transaction, so a failed request leaves no partial batch to replay.

Do not add request chunking or multi-set aggregation initially. If a batch-size limit becomes necessary, define that as a separate contract change.

### SIMS capability contract

Add a versioned `GET /identity/capabilities` response for entity types that SIMS supports. For each type, it must state supported binding of an approved existing SIMS aggregate identity, new tracked-identity allocation where permitted, relevant key semantics, confirmation behavior, and whether each operation returns an aggregate identity value. Shape Shifter's reconciliation strategy is not a SIMS operation. The current adapter may carry that value in `target_id`; the exact capability schema belongs in the companion Authority Service proposal.

SIMS must also reject unsupported entity types or operations at the resolve endpoint with a stable, actionable client error. Applying the default policy to an unrecognized type must not make the request appear supported.

SIMS capabilities reflect validated entity configuration rather than a hard-coded entity allowlist. Independently validate insertion paths for all required rows, including child or derived rows that SIMS does not track. If such a row requires an identity value but has no defined insertion path, preflight rejects the package before identity resolution or artifact generation. Do not assign the parent's identity to the child. Rows without a `public_id` are supported only when their explicit composite-key or database-generated-key insertion contract is defined and validated.

Before identity orchestration, Shape Shifter compares each entity's normalized, identity-relevant target-model requirements with the SIMS capability response. The check uses the versioned capability contract, not an exact target-model version match. Its result records the target-model name and version for diagnostics and audit; a different model version is not itself a failure, and a matching version is not proof of compatibility. A missing capability, incompatible policy, or unavailable required target ID blocks artifact generation and identifies the entity and requirement. Shape Shifter must not silently downgrade an operation or infer SIMS support from the entity's presence in the model.

## Alternatives Considered

- **SIMS configuration is authoritative for Shape Shifter's target-model intent.** Rejected because the target model defines the consumer's intended identity behavior; SIMS configuration defines how its generic mechanism supports that intent.
- **Shape Shifter assumes SIMS supports every configured entity type.** Rejected because capability checks must confirm valid SIMS configuration and operation support rather than infer support from target-model declarations.
- **Keep routing by `role`.** Rejected because explicit identity metadata can override role defaults, and aggregate children can share a role with independently tracked entities.

## Risks And Tradeoffs

- Correct model-driven routing can change generated identity work for entities that were previously routed by role. Existing artifact behavior must be compared before rollout.
- The target model and SIMS entity configuration remain separately maintained. A versioned capability check and strict request validation reduce drift but do not require entity-specific SIMS code.
- The system contract requires every tracked entity represented in SEAD to have a corresponding SIMS identity. Establishing that condition for existing production data, and any cutover work, are outside the current development task. SIMS does not validate SEAD data or enforce its database constraints.
- Child and derived entities may need relational primary keys even when they do not have independent tracked UUIDs. Their target-ID source must be decided explicitly.
- A single SIMS batch makes its Binding Set the confirmation unit for all SIMS work in one ingester run. Any manual-review requirement leaves that set proposed and blocks artifact generation until it is confirmed.
- A batch may eventually need a size limit. Defer chunking until real limits require it; chunking would need a parent run and a defined multi-set confirmation contract.
- The initial release is limited to configured auto-confirmable operations with a defined aggregate identity value and insertion path. Unsupported child/derived identity paths and manual-review operations fail closed; this limits the supported entity set but does not block a pilot using operations reported by SIMS capabilities.
- A proposed Binding Set from an earlier, distinct run blocks another run for the same source identity until an operator resolves it. Automatic expiry and supersession are deferred, so abandoned proposals may require operator cleanup.
- SIMS batch idempotency and database serialization are required before automatic retries are enabled. Without them, an ambiguous timeout must stop the run for operator investigation; the client must not retry with a new run ID.
- An abandoned allocation remains assigned and can leave an unused ID gap. This is intentional; recycling IDs would add coordination and could make an older package valid again.
- A superseded SQL package is not revoked by changing SIMS Binding Set state. Change Control must prevent superseded packages from being deployed; the database constraint only prevents a second insert after one package has succeeded.

## Testing And Validation

- Target-model tests cover effective identity-mode resolution and invalid combinations; planner tests use conflicting role/mode examples such as `analysis_entity` and `sample_dimension` to prove the model rules control routing.
- Contract tests compare the normalized identity requirements of the SEAD target model with the versioned SIMS capability response and report semantic incompatibilities before artifact generation, regardless of whether the target-model version matches.
- SIMS API tests prove capability reporting follows validated configuration and missing or invalid entity configuration fails explicitly instead of receiving default behavior.
- Identity integration tests prove Shape Shifter supplies approved existing identities without reminting and that SIMS allocates configured aggregate identity values and UUIDs through the same generic mechanism. Child and derived rows follow their own insertion contracts or block artifact generation.
- SIMS store tests prove aggregate identity values are unique within SIMS and reject conflicting mappings there. They do not test or claim SEAD database uniqueness or integrity.
- SIMS batch tests prove one request creates one Submission and one Binding Set, outcomes preserve request order, and a same-key/same-payload retry returns the original result without creating another set. Reuse of a key with a different payload is rejected.
- SIMS retry tests prove the same source identity returns the same tracked UUID and aggregate identity value, and abandoned values are never reassigned to another identity.
- SIMS concurrency tests prove simultaneous runs for the same source identity cannot create duplicate tracked identities, and a distinct run receives a pending-identity conflict while an earlier set remains proposed.
- Confirmation tests prove the ingester never confirms a proposed set automatically, and artifact generation remains blocked until SIMS reports the set as confirmed.
- Package withdrawal, supersession, and deployment eligibility are validated in the separate [operational cutover and deployment work](../CUTOVER_AND_DEPLOYMENT/CHANGE_REQUEST_INGESTER_CUTOVER_AND_DEPLOYMENT_PROPOSAL.md), not in this development task.
- Inline INSERT and copy-CSV artifact tests prove both strategies emit equivalent identities and no package is written when a required capability or target ID is missing.
- Disposable PostgreSQL validation must pass the submission artifact assertions in the linked contract handoff after the identity behavior is implemented.

## Acceptance Criteria

- `P-AC-1`: The ingester derives each row's identity work from the target model's effective `identity_tracking`, `reconciliation`, and `aggregate_parent` values, not from `role` alone.
- `P-AC-2`: Target-model validation and ingester planning use the same effective identity rules, including documented defaults for omitted fields.
- `P-AC-3`: Before orchestration, Shape Shifter compares normalized identity requirements with a versioned SIMS capability response, records the target-model name and version, and does not require exact target-model version equality.
- `P-AC-4`: SIMS rejects unsupported entity types or operations explicitly; unlisted entities do not silently inherit a default policy.
- `P-AC-5`: SIMS provides a generic, configuration-driven mechanism for minting tracked aggregate identity values. Shape Shifter blocks artifact generation when a required identity value or insertion path is unavailable. Child and derived rows use insertion paths outside SIMS unless the domain model identifies them as tracked aggregates.
- `P-AC-6`: SIMS guarantees uniqueness of aggregate identity values within its own identity store. It does not guarantee SEAD database uniqueness, map values to SEAD tables or columns, or enforce SEAD integrity.
- `P-AC-7`: Re-resolving a confirmed source identity returns its same tracked UUID and aggregate identity value; a distinct run encountering a proposed Binding Set receives a pending-identity conflict and does not allocate another identity. Allocated values are never released or reused, including when a package is abandoned.
- `P-AC-8`: The development work does not control deployment eligibility; package withdrawal or supersession before a regenerated package is deployed is defined in the [operational cutover and deployment proposal](../CUTOVER_AND_DEPLOYMENT/CHANGE_REQUEST_INGESTER_CUTOVER_AND_DEPLOYMENT_PROPOSAL.md).
- `P-AC-9`: One artifact-producing ingester run sends all SIMS identity work in one resolve request and receives one Submission and one Binding Set; an empty SIMS work set makes no request.
- `P-AC-10`: SIMS returns outcomes in request order. The ingester never confirms a proposed Binding Set automatically and blocks artifact generation until the set is confirmed; it associates a confirmed set once with the generated change request.
- `P-AC-11`: SIMS serializes requests by scoped run-level idempotency key and commits the key, batch result, and identity changes in one transaction. A same-key/same-payload retry returns the original result; a different payload with that key conflicts; a failed batch leaves no partial result.
- `P-AC-12`: Inline INSERT and copy-CSV output pass the disposable PostgreSQL submission-artifact contract checks.
- `P-AC-13`: The SIMS–SEAD trust contract requires every tracked entity represented in SEAD to have a corresponding SIMS tracked identity. Establishing this invariant for existing production data is separate operational work described in the [cutover and deployment proposal](../CUTOVER_AND_DEPLOYMENT/CHANGE_REQUEST_INGESTER_CUTOVER_AND_DEPLOYMENT_PROPOSAL.md), not part of the current development scope.
- `P-AC-14`: Shape Shifter performs reconciliation and approval before SIMS resolution. SIMS binds an approved existing aggregate identity without minting another identity; an approved miss requests a new identity through the configured generic mechanism. A conflicting binding fails without remapping.
- `P-AC-15`: For every tracked aggregate, SIMS stores an entity-scoped aggregate identity value, tracked UUID, and associated scoped source identities as distinct roles.
- `P-AC-16`: SIMS's generic allocator is configured by entity type, mints aggregate identity values, and enforces uniqueness within SIMS without SEAD table, column, sequence, or database-constraint knowledge.

## Planning Handoff

Use the [cross-system phase plan](./SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md) for delivery order. The plan assigns SIMS implementation to the Authority Service, model-driven planning and artifact work to Shape Shifter, and insertion/deployment checks to SEAD Change Control. The cross-system plan remains in Shape Shifter because it sequences the consuming workflow; it is not the design authority for SIMS internals.

- Preserve the target model as the authority for Shape Shifter's intended identity behavior, Shape Shifter as the owner of reconciliation and approval, and SIMS as the owner of tracked aggregate identities and generic identity minting.
- Preserve the identity ownership decision: SIMS owns tracked aggregate identities and scoped source-identity associations, and mints aggregate identity values through generic configuration. SEAD consumes those values under a trust contract; SIMS does not know SEAD table or column mappings and does not enforce SEAD database integrity.
- Do not equate the four target-model identity modes directly with SIMS's `entity_subtype`; define and validate an explicit mapping between target operations and service capabilities.
- Keep existing-data migration, operational adoption, and cutover out of the current development task. The target-state trust contract requires every tracked SEAD entity to have a SIMS identity; establishing that for historical data is a separate operational decision.
- Define an explicit request to bind an approved existing aggregate identity by entity type and identity value; SIMS must not search SEAD or infer a miss from a missing source binding. Keep Shape Shifter's manual approval of uncertain matches distinct from SIMS Binding Set confirmation.
- Specify insertion-time keys for child and derived rows outside SIMS, including `site_location_id`, when those rows do not receive independent tracked UUIDs.
- Persist the aggregate identity value with the tracked identity from first allocation so retries return the same UUID and value; do not release or recycle allocated values. Serialize identity resolution so a concurrent run cannot allocate a second identity for the same source identity.
- For a distinct run, reuse confirmed bindings and reject source identities with a still-proposed Binding Set. Treat resolution or abandonment of that set as an operator action; defer automatic expiry and supersession.
- Keep package withdrawal, supersession, and deployment eligibility in the linked operational proposal; they are not development acceptance criteria. Treat SIMS Binding Set status as audit state, not SQL revocation.
- Send all SIMS work for one artifact-producing ingester run in one resolve request. Retain a scoped run ID across retries, serialize duplicate requests, and commit the idempotency record and batch result atomically. Give each intentional run a new ID.
- Do not confirm proposed Binding Sets from the ingester. Initially allow only auto-confirmable operations; require a confirmed set before artifact generation and defer a manual-review workflow.
- Preserve request order in SIMS outcomes or introduce an explicit row correlation value if the API cannot guarantee ordering. Do not add chunking or multi-set orchestration until a real batch limit requires it.
- Implement a companion Authority Service proposal for generic entity configuration, capability publication, and strict missing/invalid-configuration responses before integrating capability checks in Shape Shifter.
- Treat the verified `site` and `sample` operations as initial test/configuration examples, not a limit on the generic mechanism. Fail preflight for required child/derived rows without a validated insertion path; define those paths before generating packages that include them.
- Expected validation outcome: unsupported or incomplete identity behavior is detected before an artifact is written; both deploy strategies produce packages that pass the isolated PostgreSQL assertions.
- Define the normalized compatibility fields and capability response schema before coding. The initial rollout is blocked if any enabled operation lacks its required aggregate identity value, confirmation, or insertion contract; unsupported operations remain known limitations until configured and implemented.

## Blockers And Known Limitations

- **Blocks the affected package:** A child or derived row that needs a new target ID without a defined insertion path is rejected at preflight. It can be enabled after a follow-up defines and validates its key contract outside SIMS.
- **Limits the initial rollout:** Types requiring manual SIMS Binding Set confirmation are unsupported until that workflow exists. This does not bypass Shape Shifter's approval of uncertain SEAD matches before submitting them to SIMS. A proposed Binding Set blocks artifact generation; the ingester does not confirm it automatically.
- **Requires operator handling:** A different run that encounters an earlier proposed Binding Set for the same source identity is rejected until the set is resolved. Automatic expiry and supersession are deferred.
- **Blocks automatic retries until implemented:** SIMS must persist idempotency results, serialize duplicate keys and source-identity allocation, and commit a batch atomically. Until then, ambiguous timeouts require operator investigation rather than retrying with a new run ID.
- These limits do not block a pilot restricted to auto-confirmable, configured operations with defined identity-value and insertion contracts. They do block enabling unconfigured operations or claiming full rollout coverage.

## Final Recommendation

Keep target-model identity metadata authoritative for Shape Shifter's intended behavior and SIMS's validated configuration authoritative for the generic identity operations it can perform. SIMS owns and uniquely stores each tracked aggregate identity and mints its opaque entity-scoped identity value; it does not know SEAD table or column mappings and does not enforce SEAD database integrity. Shape Shifter uses the SIMS response for artifact generation and fails closed when a required value or insertion path is missing. Send one atomically idempotent resolve batch per artifact-producing run, reject distinct runs that encounter unresolved proposed bindings, and require confirmation before artifact generation without auto-confirming from the ingester. Use configuration, not entity-specific allocator code, to support entity types. The long-term trust contract requires every tracked entity represented in SEAD to have a SIMS identity. Existing-data migration, production validation, and cutover are separate operational work and outside this development task.