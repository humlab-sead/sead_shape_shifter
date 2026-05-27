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
- [DELIVERY_1_FOLLOWUP_CR.md](./DELIVERY_1_FOLLOWUP_CR.md) — Follow-up CR for post-Delivery-1 SQL rendering strategy and target-model review
- [DELIVERY_1_FOLLOWUP_ISSUES.md](./DELIVERY_1_FOLLOWUP_ISSUES.md) — GitHub-ready issue drafts for the follow-up CR
- [NEXT_DELIVERY_CANDIDATES.md](./NEXT_DELIVERY_CANDIDATES.md) — Candidate next-delivery capabilities carried forward from the old Delivery 2 section, explicitly undecided
- [FRONTEND_UX_INTEGRATION_CR.md](./FRONTEND_UX_INTEGRATION_CR.md) — Separate CR for frontend workflow integration and required user interaction
- [FRONTEND_UX_INTEGRATION_ISSUES.md](./FRONTEND_UX_INTEGRATION_ISSUES.md) — GitHub-ready issue drafts for the frontend UX integration CR
- [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md) — Focused next-delivery CR for updating existing target rows
- [INGESTER_READABILITY_REFACTOR_PLAN.md](./INGESTER_READABILITY_REFACTOR_PLAN.md) — Focused plan for reducing `SeadChangeRequestIngester` size and mixed responsibilities

## Current Status

- Proposal status: Delivery 1 closed; active work now split into follow-up hardening, candidate next-delivery capabilities, and frontend UX integration
- Ingester key: `sead_change_request`
- Delivery 1 input contract: DataFrame-first, with adapter boundary only if framework compatibility requires it
- Delivery 1 confirmation model: synchronous at the change-package boundary; manual confirmation blocks artifact generation and returns a pending confirmation report
- Delivery 1 deploy artifact baseline: inline `INSERT` SQL plus placeholder revert and verify files when required
- Follow-up focus: deploy-rendering strategy split, possible CSV plus `\copy` artifact format, Jinja2 evaluation, and target-model/schema review
- Next-delivery scope: candidate only; rollback, update handling, stronger idempotency, and related capabilities are not yet committed as one delivery
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
