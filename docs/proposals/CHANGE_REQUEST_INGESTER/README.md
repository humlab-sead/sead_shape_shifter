# SEAD Change Request Ingester

## Overview

This folder contains the active follow-up proposals and planning material for the `sead_change_request` ingester.

The closed Delivery 1 baseline now lives under [closed_delivery_1](./closed_delivery_1).

The accepted Delivery 1 direction is:

- DataFrame-first ingestion inside the ingester core
- identity resolution before SQL generation
- SIMS allocation for new entities and allocatable classifiers
- reconciliation-first handling for existing classifier matches
- forward-only change-package generation with non-revertible placeholder handling when required

## Documents

- [closed_delivery_1/SEAD_CHANGE_REQUEST_INGESTER.md](./closed_delivery_1/SEAD_CHANGE_REQUEST_INGESTER.md) — Closed Delivery 1 baseline proposal and accepted design decisions
- [closed_delivery_1/DELIVERY_1_IMPLEMENTATION_PLAN.md](./closed_delivery_1/DELIVERY_1_IMPLEMENTATION_PLAN.md) — Closed Delivery 1 implementation plan and workstream record
- [closed_delivery_1/DELIVERY_1_HARDENING.md](./closed_delivery_1/DELIVERY_1_HARDENING.md) — Closed Delivery 1 hardening contract for the `copy_csv` artifact bundle
- [closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md](./closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md) — Closed follow-up CR for post-Delivery-1 SQL rendering strategy and target-model review
- [DELIVERY_1_FOLLOWUP_ISSUES.md](./DELIVERY_1_FOLLOWUP_ISSUES.md) — GitHub-ready issue drafts for the follow-up CR
- [NEXT_DELIVERY_CANDIDATES.md](./NEXT_DELIVERY_CANDIDATES.md) — Candidate next-delivery capabilities carried forward from the old Delivery 2 section, explicitly undecided
- [FRONTEND_UX_INTEGRATION_CR.md](./FRONTEND_UX_INTEGRATION_CR.md) — Separate CR for frontend workflow integration and required user interaction
- [FRONTEND_UX_INTEGRATION_ISSUES.md](./FRONTEND_UX_INTEGRATION_ISSUES.md) — GitHub-ready issue drafts for the frontend UX integration CR
- [DATA_PROVIDER_UPDATE_SCOPING_CR.md](./DATA_PROVIDER_UPDATE_SCOPING_CR.md) — Provider-focused CR that defines which update scenarios should be allowed, restricted, or blocked before existing-row update implementation
- [DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md) — Draft lifecycle specification for provider-owned data changes, history rules, and live-version invariants
- [DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md) — Draft implementation plan with phases, workstreams, exit criteria, and progress checklists for lifecycle work
- [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md) — Focused next-delivery CR for updating existing target rows
- [INGESTER_READABILITY_REFACTOR_PLAN.md](./INGESTER_READABILITY_REFACTOR_PLAN.md) — Focused plan for reducing `SeadChangeRequestIngester` size and mixed responsibilities

## Current Status

- Proposal status: Delivery 1 and its immediate follow-up CR are closed; active work now centers on candidate next-delivery capabilities and frontend UX integration
- Ingester key: `sead_change_request`
- Delivery 1 input contract: DataFrame-first, with adapter boundary only if framework compatibility requires it
- Delivery 1 confirmation model: synchronous at the change-package boundary; manual confirmation blocks artifact generation and returns a pending confirmation report
- Delivery 1 deploy artifact baseline: inline `INSERT` SQL plus placeholder revert and verify files when required
- Closed follow-up record: deploy-rendering strategy split, CSV plus `\copy` artifact format, Jinja2 evaluation, and target-model/schema review are archived under `closed_delivery_1`
- Next-delivery scope: candidate only; rollback, update handling, stronger idempotency, and related capabilities are not yet committed as one delivery
- Data-provider update scope is now tracked separately because ownership and permission rules should be decided before existing-row update behavior
- Provider-submission lifecycle work now has a 3-document split: proposal, implementation plan, and draft specification
- Update handling now has a dedicated next-delivery CR, but it remains proposed rather than accepted
- Frontend scope: tracked separately because this ingester requires user input, blocked-state handling, and operator rerun guidance
- Frontend issue breakdown is now captured separately for GitHub-ready tracking
- Upstream SIMS handoff docs now live in `humlab-sead/sead_authority_service:docs/proposals/`

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
