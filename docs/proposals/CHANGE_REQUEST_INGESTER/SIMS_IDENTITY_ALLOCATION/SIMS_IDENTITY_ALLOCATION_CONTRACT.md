# Proposal: Target-Model and SIMS Identity Allocation Contract

## Status

- Proposed change
- Scope: identity work planning and SIMS capability checks in `sead_change_request`
- Goal: use target-model identity rules to plan rows without assuming SIMS supports every entity in the model

## Summary

Use the target model as the source of truth for how each entity is intended to be identified, reconciled, derived, or inherited. Have SIMS publish and enforce the entity operations it currently supports. Before generating artifacts, Shape Shifter must check that the planned operations are supported and that every inserted row has the target-facing integer ID it needs.

The target model and SIMS policy answer different questions. The model defines the target system's conformance rules. SIMS defines which identity operations its current service configuration can perform. Neither system should silently substitute for the other.

## Problem

The target model already defines effective identity behavior through `identity_tracking`, `reconciliation`, and `aggregate_parent`. Target-model validation checks those combinations, and generated SIMS entity-register documentation reports their effective values. The change-request ingester does not use those values to plan identity work. It routes rows by the broader `role` field instead.

This can send an entity to the wrong operation. In the SEAD model, `analysis_entity` has `role: bridge` but explicitly declares `identity_tracking: tracked` and `reconciliation: allocate`; the planner treats every bridge as a derived bridge row. `sample_dimension` has `role: fact` and `aggregate_parent: sample`, so its effective identity mode is `child`; the planner treats it as an allocation candidate. A lookup such as `site` defaults to `reconciled` with `reconcile-exact`, but the planner treats a missing ID as allocation work.

The service policy is a separate, incomplete source of runtime behavior. `sead_authority_service/config/identity_policy.yml` lists a limited set of entity policies. Its loader applies shared-metadata defaults to unlisted names, and the resolve endpoint does not expose the listed capabilities or reject an unlisted entity type. The ingester therefore cannot tell whether a requested operation is supported before it calls SIMS. The policy vocabulary (`provider_owned`, `shared_metadata`, and `relationship`) also has no defined mapping to the target model's four identity modes and reconciliation strategies.

There is a second identity gap: a SIMS tracked UUID is not the target table's integer primary key. SIMS currently mints a tracked UUID without setting `sead_internal_id`; its optional `target_id` response is therefore null for a newly minted identity. The change-request artifact cannot insert that row until the target-ID allocation contract is implemented. The existing Authority Service target-ID proposal addresses this dependency separately.

## Scope

- Define the ownership of target-model identity intent and SIMS runtime capabilities.
- Change ingester planning to use the target model's effective identity rules rather than `role` alone.
- Define a fail-closed compatibility check between planned model operations and SIMS-supported operations.
- Require a target-ID result for each inserted row whose target model declares a `public_id`.
- Identify the Authority Service API and policy changes needed for the ingester to check capabilities.

## Non-Goals

- Implementing the Authority Service capability API or changing its identity database schema in this proposal.
- Replacing the target model's identity modes or changing its entity taxonomy.
- Defining the SEAD submission lifecycle, historical data migration, or change-request deployment order.
- Treating the target model as a list of individual runtime identities already stored in SIMS.

## Current Behavior

- The target model permits `tracked`, `reconciled`, `derived`, and `child` identity modes. When fields are omitted, target-model validation and generated documentation infer effective behavior from the entity role and aggregate parent. See [Target Model Guide](../../../TARGET_MODEL_GUIDE.md), [SEAD superset model](../../../../resources/target_models/sead_superset_model.yml), and [identity rules validator](../../../../src/target_model/spec_validator.py).
- The ingester's [`plan_table()`](../../../../ingesters/sead_change_request/planning.py) selects allocation for most roles, reconciliation for classifiers, and derivation for bridges. It does not resolve or use the effective identity mode or reconciliation strategy.
- The SIMS adapter sends an entity name and serialized row values to `POST /identity/resolve`; it has no capability-discovery call. The `IdentityPolicy` class can list explicitly configured entity types internally, but the API does not publish that list. Unknown entity types receive default policy rather than an unsupported-type error.
- The SIMS API has an optional `target_id` field. New tracked identities are minted with a UUID, while `sead_internal_id` remains unset until materialization. The current allocation path can consequently return a tracked UUID without the integer ID required by generated SQL.
- The active [PostgreSQL contract handoff](../POSTGRESQL_CONTRACT_VALIDATION.md) records that current change-package validation is blocked on this identity contract.

## Proposed Design

### Ownership

The target model owns the intended identity behavior for each entity in a target schema. Its effective `identity_tracking`, `reconciliation`, and `aggregate_parent` values govern which identity work the ingester plans. The entity's semantic `role` remains useful domain metadata, but it is not a substitute for these identity rules.

SIMS owns the operations its deployed policy can perform, the tracked identities it creates, and allocation of new target IDs for those identities. It should publish supported entity operations as capabilities, not as a replacement for the target model's conformance rules. Actual tracked identities are runtime records and must not be used to decide which target-model entities require identity handling.

### Model-driven planning

The ingester uses one shared effective-policy resolution path, consistent with target-model validation and documentation generation. It plans identity work from the resolved mode and reconciliation strategy:

- `tracked` entities use the declared allocation flow.
- `reconciled` entities use their declared reconciliation strategy. A miss may allocate or block only when that strategy and SIMS capability both permit it; `lookup-only` must not become allocation through a fallback.
- `derived` entities use the declared derivation flow and their related rows.
- `child` entities inherit identity through `aggregate_parent`; they are not independently treated as tracked entities.

The target-facing integer primary key is a separate requirement from a SIMS tracked UUID. SIMS is the sole allocator of new target IDs for this workflow. The implementation must specify how each row with a declared `public_id` obtains its target ID, including child or derived rows that do not receive an independent tracked UUID. Rows without a `public_id` must follow an explicit composite-key or database-generated-key insertion contract. No artifact is emitted while a required target ID is missing.

### Allocation, commit, and rerun

SEAD hands target-ID allocation for these entities to SIMS. After cutover, Shape Shifter and the SEAD database must not independently allocate those IDs. The SEAD Change Control system is the only system expected to write these submissions to SEAD.

SIMS assigns and persists one target ID for each tracked identity before artifact generation. Keep the target ID with the tracked identity while it is in the `ALLOCATED` state; a separate reservation state is not needed. Re-resolving the same source identity returns the same tracked UUID and target ID. An ingester rerun must not mint a second identity or target ID for that same entity.

For a distinct run, SIMS reuses an existing confirmed binding. If the source identity belongs to a still-proposed Binding Set from an earlier run, SIMS returns a stable pending-identity conflict and does not mint another tracked identity or target ID. Runs for the same source identity are serialized in SIMS so concurrent requests cannot both pass the binding check and allocate separate identities. Resolving or abandoning a pending set is an operator action in the initial release; automatic expiry or supersession is deferred.

Do not release or recycle an allocated target ID. If its package is abandoned, the allocation remains in SIMS and may leave an unused ID gap. This avoids changing the ID underneath another generated package and keeps retries idempotent. Allocate a different ID only for a genuinely different tracked identity.

Use optimistic collision detection at insertion time. Change Control inserts the submission in a database transaction and relies on primary-key and other uniqueness constraints to reject an ID that is already in use. A collision must fail the transaction; the ingester must not silently replace the ID or emit a different package. Treat a collision as an invariant violation to investigate. Given the agreed single-writer rule, no distributed lock is needed for the normal path.

Before a regenerated package becomes eligible for deployment, Change Control must withdraw or supersede the earlier change request for the same logical submission. A SIMS Binding Set status can record that supersession for audit, but it does not revoke SQL that has already been generated. If two packages are nevertheless applied, the first successful insert wins and the other must fail on database uniqueness constraints.

### One SIMS batch per ingester run

For one artifact-producing ingester run, Shape Shifter collects all rows that require SIMS identity work and sends them in one `POST /identity/resolve` request. The endpoint already accepts a list of resolution requests and creates one Submission and one Binding Set per call. If no rows require SIMS work, Shape Shifter skips the request.

SIMS returns outcomes in the same order as the requests. The ingester does not call the confirmation endpoint automatically. SIMS may auto-confirm a set only when policy allows auto-confirmation for every entity in the batch. A proposed set blocks artifact generation; the initial release supports only auto-confirmable entities. Supporting manual-review entities requires an explicit review and confirmation step before artifact generation.

Each ingester run has a stable run ID used as its idempotency key, scoped to the SIMS source scope. The ingester persists and reuses that ID for retries; a later intentional run gets a new ID even if its payload is identical. SIMS stores the key, a canonical fingerprint of the request body, and the completed result. It serializes requests with the same key using a database lock and enforces a unique key constraint. The same key and fingerprint return the original Submission, Binding Set, and outcomes; the same key with a different fingerprint returns a conflict. The key, Submission, source-identity resolution, tracked-identity allocations, bindings, Binding Set, and target IDs are committed in one database transaction, so a failed request leaves no partial batch to replay.

Do not add request chunking or multi-set aggregation initially. If a batch-size limit becomes necessary, define that as a separate contract change.

### SIMS capability contract

Add a versioned `GET /identity/capabilities` response for entity types that SIMS supports. For each type, it must state the supported identity modes and reconciliation behavior, relevant key semantics, allocation and confirmation behavior, and whether each operation can return a target-facing integer ID allocated by SIMS. The exact response schema belongs in the companion Authority Service proposal.

SIMS must also reject unsupported entity types or operations at the resolve endpoint with a stable, actionable client error. Applying the default policy to an unrecognized type must not make the request appear supported.

The initial capability allowlist includes only operations whose identity and target-ID paths are defined. If a child or derived row requires a new target integer ID but has no supported SIMS allocation path, capability preflight rejects that entity before identity resolution or artifact generation. Do not assign the parent's ID to the child. Rows without a `public_id` are supported only when their explicit composite-key or database-generated-key insertion contract is defined and validated.

Before identity orchestration, Shape Shifter compares each entity's normalized, identity-relevant target-model requirements with the SIMS capability response. The check uses the versioned capability contract, not an exact target-model version match. Its result records the target-model name and version for diagnostics and audit; a different model version is not itself a failure, and a matching version is not proof of compatibility. A missing capability, incompatible policy, or unavailable required target ID blocks artifact generation and identifies the entity and requirement. Shape Shifter must not silently downgrade an operation or infer SIMS support from the entity's presence in the model.

## Alternatives Considered

- **SIMS is authoritative for which target entities are tracked.** Rejected because SIMS policy does not define target-schema conformance and can differ from one target model version to another. Making it authoritative would duplicate or override model information.
- **Shape Shifter uses the model and assumes SIMS supports every declared mode.** Rejected because the service has a separate, partial policy list, unknown types currently fall back to defaults, and new UUID allocation does not currently guarantee a target integer ID.
- **Keep routing by `role`.** Rejected because explicit identity metadata can override role defaults, and aggregate children can share a role with independently tracked entities.

## Risks And Tradeoffs

- Correct model-driven routing can change generated identity work for entities that were previously routed by role. Existing artifact behavior must be compared before rollout.
- The target model and SIMS policy remain separately maintained. A versioned capability check and strict request validation reduce drift but do not remove the need for a companion Authority Service change.
- The handoff to SIMS requires a coordinated cutover: existing IDs must be accounted for, and other allocation paths for SIMS-managed entities must stop. The single-writer assumption reduces collision risk but does not replace database uniqueness constraints.
- Child and derived entities may need relational primary keys even when they do not have independent tracked UUIDs. Their target-ID source must be decided explicitly.
- A single SIMS batch makes its Binding Set the confirmation unit for all SIMS work in one ingester run. Any manual-review requirement leaves that set proposed and blocks artifact generation until it is confirmed.
- A batch may eventually need a size limit. Defer chunking until real limits require it; chunking would need a parent run and a defined multi-set confirmation contract.
- The initial release is limited to auto-confirmable entity operations with a defined target-ID and insertion path. Unsupported child/derived ID paths and manual-review entities fail closed; this limits the supported entity set but does not block a pilot using the allowlisted operations.
- A proposed Binding Set from an earlier, distinct run blocks another run for the same source identity until an operator resolves it. Automatic expiry and supersession are deferred, so abandoned proposals may require operator cleanup.
- SIMS batch idempotency and database serialization are required before automatic retries are enabled. Without them, an ambiguous timeout must stop the run for operator investigation; the client must not retry with a new run ID.
- An abandoned allocation remains assigned and can leave an unused ID gap. This is intentional; recycling IDs would add coordination and could make an older package valid again.
- A superseded SQL package is not revoked by changing SIMS Binding Set state. Change Control must prevent superseded packages from being deployed; the database constraint only prevents a second insert after one package has succeeded.

## Testing And Validation

- Target-model tests cover effective identity-mode resolution and invalid combinations; planner tests use conflicting role/mode examples such as `analysis_entity` and `sample_dimension` to prove the model rules control routing.
- Contract tests compare the normalized identity requirements of the SEAD target model with the versioned SIMS capability response and report semantic incompatibilities before artifact generation, regardless of whether the target-model version matches.
- SIMS API tests prove unsupported entity types and operations fail explicitly instead of receiving default behavior.
- Identity integration tests prove SIMS allocates each new target integer ID for rows with a declared `public_id`, including rows without an independently tracked UUID, or the ingester blocks with a diagnostic. Rows without a `public_id` follow their declared insertion contract.
- Disposable database tests prove a target-ID collision rolls back the Change Control insertion transaction and does not silently remap the identity.
- SIMS batch tests prove one request creates one Submission and one Binding Set, outcomes preserve request order, and a same-key/same-payload retry returns the original result without creating another set. Reuse of a key with a different payload is rejected.
- SIMS retry tests prove the same source identity returns the same tracked UUID and target ID, and abandoned target IDs are never reassigned to another identity.
- SIMS concurrency tests prove simultaneous runs for the same source identity cannot create duplicate tracked identities, and a distinct run receives a pending-identity conflict while an earlier set remains proposed.
- Confirmation tests prove the ingester never confirms a proposed set automatically, and artifact generation remains blocked until SIMS reports the set as confirmed.
- Change Control workflow validation proves an earlier package for the same logical submission is withdrawn or superseded before a regenerated package can be deployed.
- Inline INSERT and copy-CSV artifact tests prove both strategies emit equivalent identities and no package is written when a required capability or target ID is missing.
- Disposable PostgreSQL validation must pass the submission artifact assertions in the linked contract handoff after the identity behavior is implemented.

## Acceptance Criteria

- `P-AC-1`: The ingester derives each row's identity work from the target model's effective `identity_tracking`, `reconciliation`, and `aggregate_parent` values, not from `role` alone.
- `P-AC-2`: Target-model validation and ingester planning use the same effective identity rules, including documented defaults for omitted fields.
- `P-AC-3`: Before orchestration, Shape Shifter compares normalized identity requirements with a versioned SIMS capability response, records the target-model name and version, and does not require exact target-model version equality.
- `P-AC-4`: SIMS rejects unsupported entity types or operations explicitly; unlisted entities do not silently inherit a default policy.
- `P-AC-5`: SIMS is the sole allocator of new target IDs for this workflow after cutover; every inserted row in the enabled capability allowlist whose target model declares a `public_id` has a valid target ID or artifact generation is blocked. Unsupported child/derived ID paths fail preflight. Rows without a `public_id` are enabled only with a validated insertion contract.
- `P-AC-6`: A target-ID collision fails and rolls back the Change Control insertion transaction; the ingester does not silently remap the ID.
- `P-AC-7`: Re-resolving a confirmed source identity returns its same tracked UUID and target ID; a distinct run encountering a proposed Binding Set receives a pending-identity conflict and does not allocate another identity. Allocated target IDs are never released or reused, including when a package is abandoned.
- `P-AC-8`: Change Control withdraws or supersedes an earlier package for the same logical submission before a regenerated package is eligible for deployment.
- `P-AC-9`: One artifact-producing ingester run sends all SIMS identity work in one resolve request and receives one Submission and one Binding Set; an empty SIMS work set makes no request.
- `P-AC-10`: SIMS returns outcomes in request order. The ingester never confirms a proposed Binding Set automatically and blocks artifact generation until the set is confirmed; it associates a confirmed set once with the generated change request.
- `P-AC-11`: SIMS serializes requests by scoped run-level idempotency key and commits the key, batch result, and identity changes in one transaction. A same-key/same-payload retry returns the original result; a different payload with that key conflicts; a failed batch leaves no partial result.
- `P-AC-12`: Inline INSERT and copy-CSV output pass the disposable PostgreSQL submission-artifact contract checks.

## Planning Handoff

- Preserve the target model as the authority for intended entity identity modes and preserve SIMS as the owner of tracked identities, supported operations, and new target-ID allocation.
- Do not equate the four target-model identity modes directly with SIMS's `entity_subtype`; define and validate an explicit mapping between target operations and service capabilities.
- Define the cutover that accounts for existing target IDs and stops other allocation paths for SIMS-managed entities. Change Control's database transaction and uniqueness constraints provide the optimistic collision check.
- Specify how child and derived rows obtain target IDs even when they do not receive independent tracked UUIDs.
- Persist the target ID with the tracked identity from first allocation so retries return the same UUID and target ID; do not release or recycle IDs when a package is abandoned. Serialize identity resolution so a concurrent run cannot allocate a second identity for the same source identity.
- For a distinct run, reuse confirmed bindings and reject source identities with a still-proposed Binding Set. Treat resolution or abandonment of that set as an operator action; defer automatic expiry and supersession.
- Ensure Change Control withdraws or supersedes an earlier package before a regenerated package for the same logical submission is eligible for deployment. Treat SIMS Binding Set supersession as audit state, not as SQL revocation.
- Send all SIMS work for one artifact-producing ingester run in one resolve request. Retain a scoped run ID across retries, serialize duplicate requests, and commit the idempotency record and batch result atomically. Give each intentional run a new ID.
- Do not confirm proposed Binding Sets from the ingester. Initially allow only auto-confirmable operations; require a confirmed set before artifact generation and defer a manual-review workflow.
- Preserve request order in SIMS outcomes or introduce an explicit row correlation value if the API cannot guarantee ordering. Do not add chunking or multi-set orchestration until a real batch limit requires it.
- Implement a companion Authority Service proposal for capability publication and strict unsupported-type responses before integrating capability checks in Shape Shifter.
- Limit the initial capability allowlist to entity operations with defined target-ID and insertion behavior. Fail preflight for child/derived rows without a supported ID path; define those paths in a follow-up before expanding the allowlist.
- Expected validation outcome: unsupported or incomplete identity behavior is detected before an artifact is written; both deploy strategies produce packages that pass the isolated PostgreSQL assertions.
- Define the normalized compatibility fields and capability response schema before coding. The initial rollout is blocked if any enabled operation lacks its required ID, confirmation, or insertion contract; unsupported operations remain known limitations outside the allowlist.

## Blockers And Known Limitations

- **Blocks the affected operation:** A child or derived row that needs a new target ID without a defined allocation path is rejected at preflight. It can be enabled after a follow-up defines and validates its ID contract.
- **Limits the initial rollout:** Manual-review entities are unsupported until an explicit review workflow exists. A proposed Binding Set blocks artifact generation; the ingester does not confirm it automatically.
- **Requires operator handling:** A different run that encounters an earlier proposed Binding Set for the same source identity is rejected until the set is resolved. Automatic expiry and supersession are deferred.
- **Blocks automatic retries until implemented:** SIMS must persist idempotency results, serialize duplicate keys and source-identity allocation, and commit a batch atomically. Until then, ambiguous timeouts require operator investigation rather than retrying with a new run ID.
- These limits do not block a pilot restricted to auto-confirmable entities with defined target-ID and insertion contracts. They do block enabling unsupported entity groups or claiming full rollout coverage.

## Final Recommendation

Keep target-model identity metadata authoritative for the ingester's intended behavior, and make SIMS the owner and sole allocator of new identities and target IDs after cutover. Persist one target ID per tracked identity and return the same UUID and ID on reruns; never release or recycle allocated IDs. Add a SIMS capability contract and strict request validation. Send one atomically idempotent resolve batch per artifact-producing run, reject distinct runs that encounter unresolved proposed bindings, and require confirmation before artifact generation without auto-confirming from the ingester. Start with auto-confirmable entities whose target-ID and insertion behavior is defined; fail closed for all others until follow-up contracts are implemented. Let Change Control rely on database uniqueness constraints as an optimistic collision check under the single-writer assumption; a collision aborts the transaction and is investigated, never silently remapped. Change Control must withdraw or supersede an older package before a regenerated one is eligible for deployment.