# SEAD Change Request Ingester

## Overview

This folder contains active and historical proposal material for the `sead_change_request` ingester.

The closed Delivery 1 baseline now lives under [closed_delivery_1](./closed_delivery_1).

The accepted Delivery 1 direction is:

- DataFrame-first ingestion inside the ingester core
- identity resolution before SQL generation
- SIMS allocation for new entities and allocatable classifiers
- reconciliation-first handling for existing classifier matches
- forward-only change-package generation with non-revertible placeholder handling when required

## Consolidated State

- Delivery 1 baseline work is closed.
- Delivery 1 follow-up issue slices are resolved or implemented on the current branch.
- Frontend UX integration is implemented, with one deferred follow-up for stable metadata defaults.
- Provider-update lifecycle policy gate is accepted.
- Provider-submission lifecycle rules are promoted to durable docs at [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md).
- Phase entry status is active: Phase 1, Phase 2, and Phase 3 existing-row update handling are implemented on the current branch.
- Existing-row update handling is now an implemented baseline; future work shifts to governance and broader next-delivery decisions.
- Candidate next-delivery capabilities remain undecided and are not committed scope.

For the single consolidated tracker of remaining work, use:

- [CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md](./CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md)

## Authoritative Active Documents

- [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md) — durable lifecycle rules reference
- [DATA_PROVIDER_UPDATE_SCOPING_CR.md](./DATA_PROVIDER_UPDATE_SCOPING_CR.md) — decision proposal for provider-owned versus shared-data update scope
- [DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md) — lifecycle delivery sequencing phases
- [LIFECYCLE_PHASE_1_2_ISSUES.md](./LIFECYCLE_PHASE_1_2_ISSUES.md) — issue-ready phase 1 and phase 2 implementation slices
- [LIFECYCLE_PHASE_3_ISSUES.md](./LIFECYCLE_PHASE_3_ISSUES.md) — phase 3 implementation record for existing-row provider update handling
- [LIFECYCLE_PHASE_4_ISSUES.md](./LIFECYCLE_PHASE_4_ISSUES.md) — phase 4 issue draft for shared-data review ownership and routing
- [LIFECYCLE_SPEC_PROMOTION_NOTE.md](./LIFECYCLE_SPEC_PROMOTION_NOTE.md) — promotion handoff for moving accepted lifecycle rules into durable docs
- [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md) — focused existing-row update proposal (candidate)
- [NEXT_DELIVERY_CANDIDATES.md](./NEXT_DELIVERY_CANDIDATES.md) — undecided candidate capability backlog

## Implemented Or Historical References

- [archive/closed_delivery_1/SEAD_CHANGE_REQUEST_INGESTER.md](./archive/closed_delivery_1/SEAD_CHANGE_REQUEST_INGESTER.md) — Closed Delivery 1 baseline proposal and accepted design decisions
- [archive/closed_delivery_1/DELIVERY_1_IMPLEMENTATION_PLAN.md](./archive/closed_delivery_1/DELIVERY_1_IMPLEMENTATION_PLAN.md) — Closed Delivery 1 implementation plan and workstream record
- [archive/closed_delivery_1/DELIVERY_1_HARDENING.md](./archive/closed_delivery_1/DELIVERY_1_HARDENING.md) — Closed Delivery 1 hardening contract for the `copy_csv` artifact bundle
- [archive/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md](./archive/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md) — Closed follow-up CR for post-Delivery-1 SQL rendering strategy and target-model review
- [archive/DELIVERY_1_FOLLOWUP_ISSUES.md](./archive/DELIVERY_1_FOLLOWUP_ISSUES.md) — historical issue draft record for Delivery 1 follow-up slices
- [FRONTEND_UX_INTEGRATION_CR.md](./FRONTEND_UX_INTEGRATION_CR.md) — Separate CR for frontend workflow integration and required user interaction
- [FRONTEND_UX_INTEGRATION_ISSUES.md](./FRONTEND_UX_INTEGRATION_ISSUES.md) — issue-level tracking for frontend UX integration, including deferred follow-up item
- [archive/INGESTER_READABILITY_REFACTOR_PLAN.md](./archive/INGESTER_READABILITY_REFACTOR_PLAN.md) — Focused plan for reducing `SeadChangeRequestIngester` size and mixed responsibilities
- [DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md) — proposal-era lifecycle baseline record retained after promotion

## Current Status

- Proposal status: Delivery 1 and frontend UX integration are implemented; lifecycle policy gate is accepted and active work now centers on lifecycle phase implementation plus downstream update scope decisions
- Ingester key: `sead_change_request`
- Delivery 1 input contract: DataFrame-first, with adapter boundary only if framework compatibility requires it
- Delivery 1 confirmation model: synchronous at the change-package boundary; manual confirmation blocks artifact generation and returns a pending confirmation report
- Delivery 1 deploy artifact baseline: inline `INSERT` SQL plus placeholder revert and verify files when required
- Closed follow-up record: deploy-rendering strategy split, CSV plus `\copy` artifact format, Jinja2 evaluation, and target-model/schema review are archived under `closed_delivery_1`
- Next-delivery scope: candidate only; rollback, stronger idempotency, and related capabilities are not yet committed as one delivery
- Data-provider update scope is accepted and now governs downstream existing-row update behavior
- Provider-submission lifecycle work uses a durable lifecycle reference plus phase plan structure
- Phase 1 and Phase 2 issue-ready drafts are tracked in `LIFECYCLE_PHASE_1_2_ISSUES.md`
- Update handling has a dedicated next-delivery CR; existing-row update handling is implemented and the next open work is governance or broader candidate selection
- Phase 4 issue-ready draft now captures shared-data review ownership and routing
- Frontend issue breakdown exists as implementation record and deferred follow-up tracking
- Upstream SIMS handoff docs now live in `humlab-sead/sead_authority_service:docs/proposals/`

## Remaining Tasks Snapshot

- lifecycle baseline promotion is complete; keep [LIFECYCLE_SPEC_PROMOTION_NOTE.md](./LIFECYCLE_SPEC_PROMOTION_NOTE.md) as the handoff record
- maintain link alignment with [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md) as the durable lifecycle reference
- complete lifecycle phase implementation starting with metadata and classification contracts
- decide shared-data review ownership and governance routing
- decide first existing-row entity set for mutable-field update support
- resolve deferred frontend metadata-defaults follow-up
- choose one next-delivery candidate slice for the next accepted proposal

## Delivery 1 Scope Snapshot

- existing entity rows remain reference-only when `public_id` is populated
- bridge and association rows are evaluated independently using metadata-defined uniqueness rules where available
- classifier rows try reconciliation first and may allocate through SIMS in Delivery 1 if needed
- blocked unresolved rows stop the run before SQL generation
- collision checks cover target ID collisions plus metadata-defined bridge uniqueness checks

## Related References

- [Shape Shifter Design](../DESIGN.md)
- [Configuration Guide](../CONFIGURATION_GUIDE.md)
- [Developer Guide](../DEVELOPMENT.md)
- [Ingester System](../../backend/app/ingesters/README.md)
