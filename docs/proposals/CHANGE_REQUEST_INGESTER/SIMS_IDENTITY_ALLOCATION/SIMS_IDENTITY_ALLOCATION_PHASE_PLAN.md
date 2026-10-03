# Cross-System Phase Plan: Target-Model And SIMS Identity Allocation

Source proposal: [Target-Model and SIMS Identity Allocation Contract](./SIMS_IDENTITY_ALLOCATION_CONTRACT.md)
SIMS identity contract: [SIMS `target_id` response proposal](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/SIMS_TARGET_ID_CONTRACT.md)

## Summary

This plan sequences cross-system development for `sead_change_request`. The current development task is to deliver a configurable, generic SIMS identity mechanism and the Shape Shifter integration contract. SIMS-owned API, identity-store, and allocation decisions belong in Authority Service proposals; target-model planning, reconciliation, and artifact behavior belong in Shape Shifter proposals.

Cutover, production rollout, existing-data migration, and SEAD database-integrity checks are separate operational work and are explicitly outside the current development task. Shape Shifter approves uncertain reconciliation matches before requesting SIMS identity work.

## Problem

The ingester currently plans identity work by entity role and calls SIMS per row. SIMS does not publish its supported operations or provide run-level idempotency. A SIMS-owned site allocator prototype now returns a target ID in disposable tests, but it is not an approved operation or a validated Shape Shifter-to-artifact path. These gaps prevent a safe, model-driven batch workflow.

## Scope

This plan covers the development changes needed to plan from effective target-model identity rules, check SIMS's configured capabilities, resolve one batch per run, and generate artifacts only with valid SIMS identity values and a confirmed Binding Set. It also records a separate future operational phase for establishing the SIMS–SEAD trust contract for existing data.

The current development task does not include cutover, production or intended-deployment validation, existing-data bootstrap, stopping other writers, SEAD collision enforcement, or rollout. It also does not include a manual SIMS Binding Set confirmation workflow, automatic expiry or supersession of pending Binding Sets, insertion paths for unsupported child or derived rows, or request chunking.

## Current Position

- The target model defines effective identity modes and reconciliation behavior; the ingester planner still routes by role. See the source proposal's Current Behavior section.
- The SIMS endpoint accepts a list of requests, but the current Shape Shifter adapter calls it once per row. Each resolve call creates a Submission and Binding Set.
- The site and sample identity paths have disposable verification as initial configuration examples. The generic configurable allocation mechanism, capability publication, strict rejection of unconfigured operations, and request-level idempotency remain development work. Cutover is separate operational work.
- The candidate verification guide is complete for the agreed disposable scope: the site binding and allocation paths, sample allocation, and required site/sample insertion paths have been checked, and submission IDs are reserved through the target database sequence. The sample-child comparison found no additional required path for this candidate.
- The 2026-10-02 approval records initial `site` and `sample` verification examples for Phase 1 planning. It does not constrain the generic allocator to these entity types or authorize production use or cutover.

## System Ownership

| System | Owns | Plan coverage |
| --- | --- | --- |
| SEAD Authority Service (SIMS) | Tracked aggregate identities, scoped source-identity associations, generic configured allocation, and uniqueness within its own identity store. SIMS does not map identities to SEAD tables or enforce SEAD database integrity. | Phase 1 development; see the [SIMS identity response proposal](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/SIMS_TARGET_ID_CONTRACT.md). |
| Shape Shifter | Target-model identity intent, SEAD reconciliation and approval, capability preflight, run orchestration, and artifact generation. | Phases 2–3 and Shape Shifter portions of Phase 4. |
| SEAD integration and operations | Consume SIMS-issued aggregate identity values under the trust contract; establish that existing tracked entities are represented in SIMS before operational adoption. SEAD database integrity remains SEAD's responsibility. | Separate operational follow-up, not the current development task. |

Keep this plan in Shape Shifter because it sequences the consumer workflow and cross-system validation. Do not move the whole plan into the Authority Service repository; keep SIMS-specific contracts and implementation plans in that repository and link them here.

## Phase Plan

### Phase 1: SIMS Capability And Batch Guarantees

**System Owner**

SEAD Authority Service (SIMS); Shape Shifter supplies approved match/miss decisions and consumes the published contract.

**Goal**

Provide a versioned SIMS capability contract and reliable batch binding and allocation through a generic mechanism configured by entity type. No entity type may require bespoke allocator code.

**Focus**

- Implement generic, configurable entity-scoped identity allocation and binding. Use `site` and `sample` as verified configuration examples, not as a fixed supported-type limit or separate code paths.
- Publish configured capabilities and reject unconfigured or invalid operations instead of applying implicit defaults. SIMS does not perform reconciliation or inspect SEAD.
- Bind an approved existing SIMS aggregate identity without minting another one; mint and persist the configured aggregate identity value and tracked UUID for a new tracked identity.
- Use a scoped run ID, payload fingerprint, database locking, and a unique key constraint to replay identical runs and reject key reuse with different payloads.
- Commit the idempotency record, Submission, identity changes, Binding Set, and target IDs in one transaction.
- Reuse confirmed bindings on later runs; return a pending-identity conflict when a distinct run encounters an unresolved proposed Binding Set. Serialize resolution for the same source identity.

**Initial Verified Configuration Examples (Approved for Phase 1 Planning; Not a Design Limit)**

Approved by the user on 2026-10-02. Disposable verification evidence and limits are recorded in the [candidate verification guide](./SIMS_IDENTITY_ALLOCATION_CANDIDATE_VERIFICATION.md).

| Entity | Approved operation | Scope and verification |
| --- | --- | --- |
| `site` | Bind a Shape Shifter-approved existing SEAD match. | Approved match ID must be supplied by Shape Shifter. Binding behavior and the required site insertion path passed disposable checks; this does not establish source-target correctness for a real match. |
| `site` | Allocate a new tracked identity after a Shape Shifter-approved miss. | Allocation and the required site plus `site_location` insertion path passed disposable checks using a mocked miss. Each real miss still requires Shape Shifter approval. |
| `sample` | Allocate a new tracked identity. | Sample allocation and the required sample references and insertion path passed disposable checks. Optional sample children are excluded as recorded in the verification guide. |

This approval records which paths were verified in the disposable candidate exercise. It is not a requirement for entity-specific allocator code and does not limit the generic mechanism to these entity types. A real reconciliation match or miss remains Shape Shifter's decision. The examples do not approve production use or cutover.

**Depends On**

- The generic SIMS identity contract, including entity-scoped configuration, SIMS-store uniqueness, and batch behavior. The disposable `site` and `sample` evidence supplies examples, not a cutover inventory.

Candidate verification evidence is complete for the recorded examples. The remaining Phase 1 dependency is to specify and implement the generic configuration contract. No bootstrap or cutover gate is part of this development phase.

**Outputs**

- A versioned SIMS capability contract and generic entity-scoped configuration for approved binding and new tracked-identity allocation.
- Atomic, idempotent batch resolution with defined conflict behavior for unsupported operations, changed retry payloads, and pending bindings.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-3`, `P-AC-4`) The capability response describes configured generic operations, and unconfigured types or invalid operations receive a stable error rather than default behavior.
- `PH1-AC-2` (from `P-AC-5`) The generic configured allocator returns the same entity-scoped aggregate identity value and tracked UUID on retry; artifact generation fails when a required identity value is absent.
- `PH1-AC-3` (from `P-AC-7`) A later run reuses a confirmed identity, while a distinct run encountering a proposed Binding Set receives a conflict and does not allocate a second identity or target ID.
- `PH1-AC-4` (from `P-AC-9`, `P-AC-11`) A run creates one Submission and one Binding Set; identical retries return the stored result, changed payloads conflict, and failed batches leave no partial result.
- `PH1-AC-5` (from `P-AC-14`) An approved existing aggregate identity binds without minting another identity; a conflicting binding fails, and a configured new-identity request receives its SIMS-issued identity values.
- `PH1-AC-6` (from `P-AC-15`, `P-AC-16`) SIMS stores distinct entity-scoped aggregate identity, tracked UUID, and source-key roles, and enforces uniqueness within its own identity store without requiring SEAD table or sequence knowledge.

**Validation Milestones**

- `VM-1` Capability and API tests prove approved-match binding, SIMS-owned ID allocation, and unsupported-operation rejection, covering `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-5`, and `PH1-AC-6`.
- `VM-2` Database-backed tests prove concurrent duplicate requests do not create duplicate identities, pending bindings block distinct runs, and failed batches roll back, covering `PH1-AC-3` and `PH1-AC-4`.

**Task-Plan Handoff**

- Keep the agreed database-locking and atomic-transaction requirements; leave the specific lock implementation to the task plan.
- Preserve the ownership decision: SIMS mints aggregate identity values and guarantees uniqueness only within its own store. It does not inspect SEAD sequences, tables, columns, or database constraints. Treat the site state-row implementation as a prototype, not as the generic allocator contract.
- Keep disposable `site` and `sample` checks as examples. Configuration, not entity-specific code, determines the behavior for any supported entity type.
- Cutover, bootstrap of existing data, competing-writer retirement, and deployment checks are separate operational work. Do not implement or validate them in Phase 1.
- Map normalized target-model requirements to SIMS capabilities without equating target-model modes directly to SIMS entity subtypes.

**Readiness**

Ready for a task plan after the generic configuration fields and response semantics are specified in the SIMS contract. The existing candidate evidence remains verification context; cutover and deployment are outside this development task.

### Phase 2: Model-Driven Planning And Capability Preflight

**System Owner**

Shape Shifter.

**Goal**

Make Shape Shifter plan identity work from the target model and reject unsupported work before SIMS resolution or artifact generation.

**Focus**

- Use the same effective identity-policy resolution as target-model validation and documentation.
- Route tracked, reconciled, derived, and child rows from their effective metadata, not role alone. Reconciliation is Shape Shifter's matching decision; a reconciled SEAD row can still have a SIMS tracked identity.
- Normalize approved-existing-ID binding and permitted new tracked-identity requests and compare them with the Phase 1 capability contract.
- Record target-model name and version for diagnostics without requiring an exact version match.
- Block unsupported operations and missing target-ID or untracked-row insertion paths before writing artifacts.

**Depends On**

- Phase 1 capability contract and validated entity configuration.

**Outputs**

- Model-driven identity plans and fail-closed SIMS capability preflight for the enabled operations.
- Diagnostics identifying the entity and unsupported requirement.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`, `P-AC-2`) Planning uses effective `identity_tracking`, `reconciliation`, and `aggregate_parent` values, including defaults, and matches target-model validation behavior.
- `PH2-AC-2` (from `P-AC-3`, `P-AC-4`, `P-AC-5`) Preflight checks normalized requirements against SIMS capabilities, records model name and version, and blocks unsupported or incomplete operations before artifact generation.

**Validation Milestones**

- `VM-3` Target-model and planner tests prove explicit mode settings override conflicting roles and omitted settings use documented defaults, covering `PH2-AC-1`.
- `VM-4` Contract tests prove semantic compatibility is independent of exact model-version equality and unsupported requirements block before artifacts are written, covering `PH2-AC-2`.
- `VM-5` Comparisons against existing artifact behavior document every changed identity route for the enabled operations reported by SIMS configuration before promotion, covering `PH2-AC-1`.

**Task-Plan Handoff**

- Use configured entity types for parity comparisons; do not limit generic allocator implementation to the initial `site` and `sample` examples.
- Preserve fail-closed behavior; do not silently fall back from lookup-only reconciliation to allocation or from unsupported child/derived handling to parent IDs. Shape Shifter approves uncertain SEAD matches before the SIMS request; this is separate from SIMS Binding Set confirmation.

**Readiness**

Ready for a task plan after Phase 1 publishes the capability contract and validated configuration model.

### Phase 3: Single-Batch Orchestration And Artifact Generation

**System Owner**

Shape Shifter, with SIMS-owned batch and idempotency guarantees as prerequisites.

**Goal**

Use one idempotent SIMS request per artifact-producing run and produce artifacts only from supported identities and confirmed Binding Sets.

**Focus**

- Collect Shape Shifter-approved existing matches and permitted new tracked-identity requests for the run and submit them in one SIMS request; skip the call when there is no SIMS work.
- Persist the run ID across transport retries and preserve request-to-row correlation using response order or an explicit correlation value.
- Do not confirm proposed Binding Sets from the ingester. Block artifact generation until SIMS reports the set as confirmed.
- Associate the confirmed Binding Set once with the generated change request.
- Keep Inline INSERT and copy-CSV output consistent for configured supported operations.

**Depends On**

- Phase 1 idempotent batch API and Phase 2 model-driven plan and preflight.

**Outputs**

- One Binding Set per artifact-producing run, with deterministic row assignments and no artifact output for unsupported or unconfirmed work.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-9`, `P-AC-11`) Each run sends all SIMS work in one request, skips empty batches, and reuses its run ID only for identical retries.
- `PH3-AC-2` (from `P-AC-10`) Outcomes map deterministically to planned rows; the ingester does not confirm proposed sets and writes artifacts only when the set is confirmed.
- `PH3-AC-3` (from `P-AC-5`, `P-AC-12`) Both artifact strategies emit the required SIMS-issued identity values consistently and emit no package when capability, identity-value, insertion, or confirmation requirements are unmet.

**Validation Milestones**

- `VM-6` Runtime tests prove one request and one Binding Set per run, stable row mapping, empty-batch skipping, and same-run retry behavior, covering `PH3-AC-1` and `PH3-AC-2`.
- `VM-7` Artifact tests prove both strategies produce equivalent IDs for supported work and neither writes a package for unsupported or unconfirmed work, covering `PH3-AC-3`.

**Task-Plan Handoff**

- Treat each intentional execution as a new run ID; persist that ID for retries and never retry an ambiguous failure under a new ID.
- Leave manual SIMS Binding Set confirmation workflows and request chunking out of this phase; Shape Shifter's approval of uncertain SEAD matches still precedes the batch.

**Readiness**

Ready for a task plan after Phases 1 and 2 are complete.

### Phase 4: Separate Follow-On — Trust-Contract Adoption

**System Owner**

SEAD and SIMS operational owners, with Shape Shifter and Change Control participating in their respective integration responsibilities.

**Goal**

Establish the SIMS–SEAD trust contract for existing tracked entities and coordinate operational adoption. This is a separate follow-on phase, outside the current development task.

**Focus**

- Establish that each tracked entity already represented by SEAD has a corresponding SIMS identity before relying on the trust contract. The migration method and data checks belong to the operational cutover plan, not this development task.
- Coordinate the transition so SIMS is the sole minter of tracked aggregate identities. Do not prescribe SEAD table, column, or sequence changes as SIMS responsibilities.
- Confirm separately that SEAD consumes SIMS-issued identities under the agreed trust contract. Any SEAD persistence constraints remain SEAD's responsibility.
- Handle package eligibility and deployment procedures in the SEAD operational plan.

**Depends On**

- Phases 1–3 and a separately approved operational plan for establishing the trust contract with existing data.

**Outputs**

- An operationally established trust contract under which each tracked SEAD entity has a SIMS identity.
- Recorded follow-up scope for SIMS manual confirmation, pending-set expiry or supersession, and unsupported child/derived insertion paths.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-5`, `P-AC-13`, `P-AC-16`) Operational adoption establishes that every tracked entity represented in SEAD has a corresponding SIMS identity and that SIMS is the sole minter of tracked aggregate identities.
- `PH4-AC-2` (from `P-AC-8`) The operational deployment process defines how an earlier package is withdrawn or superseded before a regenerated package becomes eligible.
- `PH4-AC-3` (from `P-AC-12`) SEAD-owned validation confirms the target system's persistence and artifact contract; this is not a SIMS database-integrity guarantee.
- `PH4-AC-4` (from `P-AC-13`) Operational coverage checks confirm that every tracked entity represented in SEAD has a corresponding SIMS identity without requiring SIMS to map identities to SEAD table or column names.

**Validation Milestones**

- `VM-8` Separately approved operational checks confirm the SIMS–SEAD trust contract for existing tracked entities, covering `PH4-AC-1` and `PH4-AC-4`.
- `VM-9` Separately approved SEAD operational checks validate SEAD's own persistence and artifact contract behavior; they do not assign database-integrity guarantees to SIMS, covering `PH4-AC-1` and `PH4-AC-3`.
- `VM-10` Change Control workflow validation proves superseded packages cannot become eligible after regeneration, covering `PH4-AC-2`.

**Task-Plan Handoff**

- Do not treat this follow-on operational phase as part of the current development task.
- Verify that tracked entities without source bindings still have SIMS identities. Coordinate data migration and operational adoption through a separately approved plan.
- Treat SIMS Binding Set state as audit state; it does not revoke generated SQL.
- SEAD owns its persistence constraints; SIMS guarantees uniqueness only within its own identity store.

**Readiness**

Requires a separately approved operational plan for existing-data migration, trust-contract adoption, and deployment.

## Cross-Phase Rules

- Keep system-owned implementation decisions in the owning repository's proposal; this plan records only cross-system sequencing and acceptance.
- Keep the target model authoritative for Shape Shifter's identity intent, Shape Shifter responsible for reconciliation and approval, and SIMS responsible for its generic tracked-identity store and identity minting. SIMS does not map identities to SEAD tables or enforce SEAD database integrity.
- Treat `site` and `sample` as initial configuration and verification examples, not the limits of generic SIMS support.
- Keep existing-data trust establishment and production cutover as separate operational work; neither is part of the current development task.
- Fail closed before artifact generation for unsupported configured capabilities, missing identity values, invalid untracked-row insertion contracts, and unconfirmed Binding Sets.
- Use one Binding Set per run; do not add chunking or multi-set aggregation in this plan.
- Do not auto-confirm proposed sets or retry ambiguous requests with a new run ID.
- Add entity types through validated configuration and the generic allocator, with behavior tests; do not add entity-specific allocator code.

## Validation Strategy

Validate the current development task in layers: SIMS API and identity-store behavior first; target-model planning and semantic capability compatibility second; single-batch orchestration and both artifact strategies third. Existing-data migration, operational trust-contract adoption, production validation, and cutover are separate future work and are not validation milestones for this development task. Exact commands, test files, fixtures, and assertions belong in each phase task plan.

## Final Recommendation

Implement and validate the generic SIMS identity mechanism and Shape Shifter integration before planning production adoption. The disposable candidate guide records initial examples; it does not constrain the architecture. Cutover, existing-data migration, and SEAD integrity checks remain separate operational work outside this development task.