# SEAD Change Request Ingester

## Overview

This folder contains active and historical proposal material for the `sead_change_request` ingester.

The closed Delivery 1 baseline now lives under [CHANGE_REQUEST_INGESTER_DELIVERY_1](./done/CHANGE_REQUEST_INGESTER_DELIVERY_1).

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
- Provider-submission lifecycle docs are archived under [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE).
- Shared-data review and operator contract work now lives in [SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md](./SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md).
- Candidate next-delivery capabilities remain undecided and are not committed scope.

For the single consolidated tracker of remaining work, use:

- [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md)

## Authoritative Active Documents

- [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md) — durable lifecycle rules reference
- [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/README.md](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/README.md) — archived provider-submission lifecycle set
- [SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md](./SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md) — separate shared-data review proposal
- [REFACTOR_SEAD_SUBMISSION_METADATA.md](./REFACTOR_SEAD_SUBMISSION_METADATA.md) — proposed CR for persisted submission defaults and SEAD submission container
- [STRONGER_IDEMPOTENCY_AND_RESUBMISSION_TASK_PLAN.md](./STRONGER_IDEMPOTENCY_AND_RESUBMISSION_TASK_PLAN.md) — proposed next-phase plan for exact reruns and partially overlapping re-submissions
- [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/LIFECYCLE_PHASE_1_2_ISSUES.md](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/LIFECYCLE_PHASE_1_2_ISSUES.md) — issue-ready phase 1 and phase 2 implementation slices
- [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/LIFECYCLE_PHASE_3_ISSUES.md](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/LIFECYCLE_PHASE_3_ISSUES.md) — phase 3 implementation record for existing-row provider update handling
- [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/LIFECYCLE_SPEC_PROMOTION_NOTE.md](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/LIFECYCLE_SPEC_PROMOTION_NOTE.md) — promotion handoff for moving accepted lifecycle rules into durable docs
- [future/UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./future/UPDATE_HANDLING_FOR_EXISTING_ROWS.md) — focused existing-row update proposal (candidate)
- [NEXT_DELIVERY_CANDIDATES.md](./future/NEXT_DELIVERY_CANDIDATES.md) — undecided candidate capability backlog

## Implemented Or Historical References

- [done/CHANGE_REQUEST_INGESTER_DELIVERY_1/SEAD_CHANGE_REQUEST_INGESTER.md](./done/CHANGE_REQUEST_INGESTER_DELIVERY_1/SEAD_CHANGE_REQUEST_INGESTER.md) — Closed Delivery 1 baseline proposal and accepted design decisions
- [done/CHANGE_REQUEST_INGESTER_DELIVERY_1/DELIVERY_1_IMPLEMENTATION_PLAN.md](./done/CHANGE_REQUEST_INGESTER_DELIVERY_1/DELIVERY_1_IMPLEMENTATION_PLAN.md) — Closed Delivery 1 implementation plan and workstream record
- [done/CHANGE_REQUEST_INGESTER_DELIVERY_1/DELIVERY_1_HARDENING.md](./done/CHANGE_REQUEST_INGESTER_DELIVERY_1/DELIVERY_1_HARDENING.md) — Closed Delivery 1 hardening contract for the `copy_csv` artifact bundle
- [done/CHANGE_REQUEST_INGESTER_DELIVERY_1/DELIVERY_1_FOLLOWUP_CR.md](./done/CHANGE_REQUEST_INGESTER_DELIVERY_1/DELIVERY_1_FOLLOWUP_CR.md) — Closed follow-up CR for post-Delivery-1 SQL rendering strategy and target-model review
- [done/DELIVERY_1_FOLLOWUP_ISSUES.md](./done/DELIVERY_1_FOLLOWUP_ISSUES.md) — historical issue draft record for Delivery 1 follow-up slices
- [FRONTEND_UX_INTEGRATION_CR.md](./done/FRONTEND_UX_INTEGRATION_CR.md) — Separate CR for frontend workflow integration and required user interaction
- [FRONTEND_UX_INTEGRATION_ISSUES.md](./done/FRONTEND_UX_INTEGRATION_ISSUES.md) — issue-level tracking for frontend UX integration, including deferred follow-up item
- [done/INGESTER_READABILITY_REFACTOR_PLAN.md](./done/INGESTER_READABILITY_REFACTOR_PLAN.md) — Focused plan for reducing `SeadChangeRequestIngester` size and mixed responsibilities
- [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md) — proposal-era lifecycle baseline record retained after promotion

## Current Status

- Proposal status: Delivery 1 and frontend UX integration are implemented; lifecycle policy gate is accepted and active work now centers on lifecycle phase implementation plus downstream update scope decisions
- Ingester key: `sead_change_request`
- Delivery 1 input contract: DataFrame-first, with adapter boundary only if framework compatibility requires it
- Delivery 1 confirmation model: synchronous at the change-package boundary; manual confirmation blocks artifact generation and returns a pending confirmation report
- Delivery 1 deploy artifact baseline: inline `INSERT` SQL plus placeholder revert and verify files when required
- Closed follow-up record: deploy-rendering strategy split, CSV plus `\copy` artifact format, Jinja2 evaluation, and target-model/schema review are archived under `done/CHANGE_REQUEST_INGESTER_DELIVERY_1`
- Next-delivery scope: candidate only; rollback, stronger idempotency, and related capabilities are not yet committed as one delivery
- Data-provider update scope is accepted and now governs downstream existing-row update behavior
- Provider-submission lifecycle work is archived under `done/DATA_PROVIDER_SUBMISSION_LIFECYCLE`
- Shared-data review and operator routing now has a separate proposal folder
- Frontend issue breakdown exists as implementation record and deferred follow-up tracking
- Upstream SIMS handoff docs now live in `humlab-sead/sead_authority_service:docs/proposals/`

## Remaining Tasks Snapshot

- lifecycle baseline promotion is complete; use the archived provider lifecycle folder for history
- keep link alignment with [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md) as the durable lifecycle reference
- continue shared-data review design in the separate proposal folder
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
