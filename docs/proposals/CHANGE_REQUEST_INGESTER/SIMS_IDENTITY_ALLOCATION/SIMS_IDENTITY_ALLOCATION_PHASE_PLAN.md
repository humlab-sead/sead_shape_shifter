# Phase Plan: Target-Model and SIMS Identity Allocation

Source proposal: [Target-Model and SIMS Identity Allocation Contract](./SIMS_IDENTITY_ALLOCATION_CONTRACT.md)

## Summary

This plan sequences the cross-system work needed for a constrained `sead_change_request` rollout. It keeps the contract proposal as the shared source of decisions and separates delivery into SIMS capability and persistence work, Shape Shifter planning and orchestration, then cutover validation.

The initial rollout supports only auto-confirmable operations with defined target-ID and insertion behavior. Unsupported child or derived ID paths and manual-review entities remain outside the rollout and must fail closed.

## Problem

The ingester currently plans identity work by entity role and calls SIMS per row. SIMS does not publish its supported operations, does not provide a target ID for newly allocated tracked identities, and does not provide run-level idempotency. These gaps prevent a safe, model-driven batch workflow.

## Scope

This plan covers the end-to-end changes needed to plan from effective target-model identity rules, check SIMS capabilities, resolve one batch per run, generate artifacts only with valid IDs and a confirmed Binding Set, and validate a constrained rollout.

It does not include manual-review workflow, automatic expiry or supersession of pending Binding Sets, allocation for unsupported child or derived rows, request chunking, or expansion beyond the initial capability allowlist.

## Current Position

- The target model defines effective identity modes and reconciliation behavior; the ingester planner still routes by role. See the source proposal's Current Behavior section.
- The SIMS endpoint accepts a list of requests, but the current Shape Shifter adapter calls it once per row. Each resolve call creates a Submission and Binding Set.
- SIMS capabilities, strict rejection of unsupported types, target-ID allocation for new identities, pending-binding conflicts, and run-level idempotency are not implemented as required by the proposal.
- The contract proposal is still marked Proposed change. Its initial entity allowlist and target-ID/insertion paths must be confirmed before implementation planning is ready.

## Phase Plan

### Phase 1: SIMS Capability And Batch Guarantees

**Goal**

Provide a versioned SIMS capability contract and reliable batch resolution for an explicitly limited set of supported operations.

**Focus**

- Confirm the initial entity-operation allowlist. Include only operations with defined target-ID and insertion paths; exclude manual-review entities and child or derived rows without a supported ID path.
- Publish supported capabilities and reject unsupported entity types or operations instead of applying defaults.
- Persist target IDs for supported tracked identities and return them with resolution outcomes.
- Use a scoped run ID, payload fingerprint, database locking, and a unique key constraint to replay identical runs and reject key reuse with different payloads.
- Commit the idempotency record, Submission, identity changes, Binding Set, and target IDs in one transaction.
- Reuse confirmed bindings on later runs; return a pending-identity conflict when a distinct run encounters an unresolved proposed Binding Set. Serialize resolution for the same source identity.

**Depends On**

- Approval of the initial entity-operation allowlist, with a verified target-ID and insertion path for every included operation.

**Outputs**

- A versioned SIMS capability contract and an explicit initial allowlist.
- Atomic, idempotent batch resolution with defined conflict behavior for unsupported operations, changed retry payloads, and pending bindings.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-3`, `P-AC-4`) The capability response describes supported operations, and unsupported types or operations receive a stable error rather than default policy behavior.
- `PH1-AC-2` (from `P-AC-5`) Every enabled operation that requires a target ID returns one before artifact generation; unsupported ID paths are not advertised as supported.
- `PH1-AC-3` (from `P-AC-7`) A later run reuses a confirmed identity, while a distinct run encountering a proposed Binding Set receives a conflict and does not allocate a second identity or target ID.
- `PH1-AC-4` (from `P-AC-9`, `P-AC-11`) A run creates one Submission and one Binding Set; identical retries return the stored result, changed payloads conflict, and failed batches leave no partial result.

**Validation Milestones**

- `VM-1` Capability and API tests prove supported operations are advertised and unsupported operations fail closed, covering `PH1-AC-1` and `PH1-AC-2`.
- `VM-2` Database-backed tests prove concurrent duplicate requests do not create duplicate identities, pending bindings block distinct runs, and failed batches roll back, covering `PH1-AC-3` and `PH1-AC-4`.

**Task-Plan Handoff**

- Keep the agreed database-locking and atomic-transaction requirements; leave the specific lock implementation to the task plan.
- Do not expand the allowlist to manual-review entities or rows without defined target-ID and insertion behavior.
- Map normalized target-model requirements to SIMS capabilities without equating target-model modes directly to SIMS entity subtypes.

**Readiness**

Requires a named decision: approve the initial entity-operation allowlist after verifying the target-ID and insertion path for each included operation.

### Phase 2: Model-Driven Planning And Capability Preflight

**Goal**

Make Shape Shifter plan identity work from the target model and reject unsupported work before SIMS resolution or artifact generation.

**Focus**

- Use the same effective identity-policy resolution as target-model validation and documentation.
- Route tracked, reconciled, derived, and child rows from their effective metadata, not role alone.
- Normalize identity requirements and compare them with the Phase 1 capability contract.
- Record target-model name and version for diagnostics without requiring an exact version match.
- Block unsupported operations and missing target-ID or insertion paths before writing artifacts.

**Depends On**

- Phase 1 capability contract and approved allowlist.

**Outputs**

- Model-driven identity plans and fail-closed SIMS capability preflight for the enabled operations.
- Diagnostics identifying the entity and unsupported requirement.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`, `P-AC-2`) Planning uses effective `identity_tracking`, `reconciliation`, and `aggregate_parent` values, including defaults, and matches target-model validation behavior.
- `PH2-AC-2` (from `P-AC-3`, `P-AC-4`, `P-AC-5`) Preflight checks normalized requirements against SIMS capabilities, records model name and version, and blocks unsupported or incomplete operations before artifact generation.

**Validation Milestones**

- `VM-3` Target-model and planner tests prove explicit mode settings override conflicting roles and omitted settings use documented defaults, covering `PH2-AC-1`.
- `VM-4` Contract tests prove semantic compatibility is independent of exact model-version equality and unsupported requirements block before artifacts are written, covering `PH2-AC-2`.
- `VM-5` Comparisons against existing artifact behavior document every changed identity route for the enabled allowlist before promotion, covering `PH2-AC-1`.

**Task-Plan Handoff**

- Limit parity comparisons and implementation to the Phase 1 allowlist.
- Preserve fail-closed behavior; do not silently fall back from lookup-only reconciliation to allocation or from unsupported child/derived handling to parent IDs.

**Readiness**

Ready for a task plan after Phase 1 publishes the capability contract and allowlist.

### Phase 3: Single-Batch Orchestration And Artifact Generation

**Goal**

Use one idempotent SIMS request per artifact-producing run and produce artifacts only from supported identities and confirmed Binding Sets.

**Focus**

- Collect all SIMS work for the run and submit it in one request; skip the call when there is no SIMS work.
- Persist the run ID across transport retries and preserve request-to-row correlation using response order or an explicit correlation value.
- Do not confirm proposed Binding Sets from the ingester. Block artifact generation until SIMS reports the set as confirmed.
- Associate the confirmed Binding Set once with the generated change request.
- Keep Inline INSERT and copy-CSV output consistent for the supported allowlist.

**Depends On**

- Phase 1 idempotent batch API and Phase 2 model-driven plan and preflight.

**Outputs**

- One Binding Set per artifact-producing run, with deterministic row assignments and no artifact output for unsupported or unconfirmed work.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-9`, `P-AC-11`) Each run sends all SIMS work in one request, skips empty batches, and reuses its run ID only for identical retries.
- `PH3-AC-2` (from `P-AC-10`) Outcomes map deterministically to planned rows; the ingester does not confirm proposed sets and writes artifacts only when the set is confirmed.
- `PH3-AC-3` (from `P-AC-5`, `P-AC-12`) Both artifact strategies emit the required target IDs consistently and emit no package when capability, ID, insertion, or confirmation requirements are unmet.

**Validation Milestones**

- `VM-6` Runtime tests prove one request and one Binding Set per run, stable row mapping, empty-batch skipping, and same-run retry behavior, covering `PH3-AC-1` and `PH3-AC-2`.
- `VM-7` Artifact tests prove both strategies produce equivalent IDs for supported work and neither writes a package for unsupported or unconfirmed work, covering `PH3-AC-3`.

**Task-Plan Handoff**

- Treat each intentional execution as a new run ID; persist that ID for retries and never retry an ambiguous failure under a new ID.
- Leave manual-review workflows and request chunking out of this phase.

**Readiness**

Ready for a task plan after Phases 1 and 2 are complete.

### Phase 4: Cutover And Constrained Rollout

**Goal**

Validate allocation ownership and database safeguards, then enable the supported allowlist without exposing unsupported entity groups.

**Focus**

- Account for existing target IDs before SIMS becomes the sole allocator for enabled entities.
- Stop other allocation paths for SIMS-managed IDs and verify the single-writer assumption.
- Verify Change Control rejects ID collisions transactionally and supersedes earlier packages before regenerated packages become eligible for deployment.
- Run the disposable PostgreSQL artifact checks and promote only the validated allowlist.

**Depends On**

- Phases 1-3 and a verified cutover inventory for existing IDs and allocation paths.

**Outputs**

- A validated, constrained rollout with explicit exclusions for unsupported operations.
- Recorded follow-up scope for manual review, pending-set expiry or supersession, and child/derived ID allocation.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-5`, `P-AC-6`) The cutover accounts for existing IDs, keeps SIMS the sole allocator for enabled entities, and a collision aborts the Change Control transaction without remapping.
- `PH4-AC-2` (from `P-AC-8`) An earlier package for the same logical submission is withdrawn or superseded before a regenerated package is eligible for deployment.
- `PH4-AC-3` (from `P-AC-12`) Inline INSERT and copy-CSV packages pass the disposable PostgreSQL submission-artifact assertions for the enabled allowlist.

**Validation Milestones**

- `VM-8` Cutover checks confirm existing IDs are accounted for and alternate allocation paths are stopped for enabled entities, covering `PH4-AC-1`.
- `VM-9` Disposable PostgreSQL checks prove collision rollback and artifact contract behavior for both strategies, covering `PH4-AC-1` and `PH4-AC-3`.
- `VM-10` Change Control workflow validation proves superseded packages cannot become eligible after regeneration, covering `PH4-AC-2`.

**Task-Plan Handoff**

- Do not enable an entity that lacks a confirmed target-ID, insertion, or confirmation path.
- Treat SIMS Binding Set state as audit state; it does not revoke generated SQL.
- Keep database uniqueness constraints as the collision backstop under the single-writer assumption.

**Readiness**

Requires a named decision: approve the cutover inventory and confirm that other allocation paths for enabled entities can be stopped.

## Cross-Phase Rules

- Keep the target model authoritative for intended identity behavior and SIMS authoritative for supported operations and allocated identities.
- Fail closed before artifact generation for unsupported capabilities, missing IDs, invalid insertion contracts, and unconfirmed Binding Sets.
- Use one Binding Set per run; do not add chunking or multi-set aggregation in this plan.
- Do not auto-confirm proposed sets or retry ambiguous requests with a new run ID.
- Expand the capability allowlist only after its target-ID, insertion, and confirmation behavior passes the same validation gates.

## Validation Strategy

Validate in layers: SIMS API and database behavior first; target-model planning and semantic capability compatibility second; single-batch orchestration and both artifact strategies third; cutover, collision rollback, Change Control eligibility, and disposable PostgreSQL contracts last. Map phase milestones `VM-1` through `VM-10` to the phase acceptance criteria above. Exact commands, test files, fixtures, and assertions belong in each phase task plan.

## Final Recommendation

Sequence SIMS guarantees before Shape Shifter integration, then cut over only the explicitly enabled operations. The plan supports a constrained pilot but does not treat manual-review entities or undefined child/derived ID paths as implicitly supported. Do not begin implementation task planning for Phase 1 until the initial allowlist and each included operation's target-ID and insertion path are confirmed.