# SEAD Change Request Ingester

## Purpose

This directory contains the active and archived proposals for the `sead_change_request` ingester. This README is the portfolio overview and consolidated status tracker. Update it when a workstream changes status; keep task-level checklists and validation results in their owning plans and handoffs.

## Current Status

**Overall:** The SEAD Change Request Ingester MVP Delivery (historically, Delivery 1) and provider-submission lifecycle are complete. The submission metadata implementation is present, but its generated-package database contract is blocked on sequence safety. Cutover and separate follow-up proposals remain open or undecided.

The MVP delivery includes:

- Identity-aware row handling: use SIMS to allocate IDs for new provider-owned rows and eligible unmatched classifiers; use reconciliation to find existing classifiers. Existing rows are referenced rather than inserted again.
- Safe relationship handling: resolve local system_id references to SEAD IDs. Evaluate bridge and association rows independently, using metadata-defined uniqueness rules.
- Fail-closed generation: stop before SQL output if identities are unresolved, Binding Set confirmation is incomplete, or target-side collision checks fail. Return diagnostics rather than a partial package.
- A forward-only package: generate INSERT statements and package metadata. Revert and verify files, when required, are explicit placeholders; the package is marked non-revertible. Deferred foreign-key checks are the preferred insert strategy.
- It deliberately does not include rollback, updates or deletes, broad semantic duplicate detection, advanced change detection, or immediate retirement of the existing Clearinghouse ingester. Those were left for separate follow-up work or candidate proposals. Frontend integration and persisted submission metadata/defaults were also handled separately, not as part of this closed baseline.

Status reviewed 2026-10-12. No new PostgreSQL validation was run for this update.

| Workstream | Status | Remaining work / next action |
|---|---|---|
| SEAD Change Request Ingester MVP and baseline follow-ups | Complete | Historical MVP Delivery records are under [done/CHANGE_REQUEST_INGESTER_MVP](./done/CHANGE_REQUEST_INGESTER_MVP). |
| Frontend workflow and persisted defaults | Complete | Frontend integration shipped in PR #456; stable metadata defaults are implemented and covered by the submission metadata work. |
| Provider-submission lifecycle | Complete | Rules are promoted to the [durable lifecycle reference](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md); implementation history is under [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE). |
| Submission metadata and generated packages | Implemented; database contract blocked | Both current artifact strategies explicitly insert IDs without advancing database sequences. First agree the SIMS/SEAD target-ID and sequence contract, then fix and validate both strategies on disposable database clones. See the [task plan](./REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md) and [PostgreSQL validation handoff](./CUTOVER_AND_DEPLOYMENT/POSTGRESQL_CONTRACT_VALIDATION.md). Do not deploy packages until the sequence checks pass. |
| SIMS-SEAD adoption, cutover, and deployment | Draft; decisions open | Resolve tracked-entity mapping, missing UUIDs, backfill and writer ordering, upstream schema/compatibility ownership, and package supersession. Track in [CUTOVER_AND_DEPLOYMENT](./CUTOVER_AND_DEPLOYMENT/README.md). |
| Shared-data review and operator contract | Draft; ownership blocked | Decide who owns review and approval, and define its split from provider-owned updates. See the [proposal](./SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md). |
| Ingester authorization and filesystem access | Proposed; not ready to enable | Define and implement resource authorization and filesystem containment. Keep operations unavailable until required checks are enforced. See the [authorization proposal](../INGESTER_AUTHORIZATION_TASKS/INGESTER_AUTHORIZATION_TASKS.md) and [filesystem proposal](../INGESTER_FILESYSTEM_BOUNDARIES/INGESTER_FILESYSTEM_BOUNDARIES.md). |
| Next-delivery capabilities | Undecided candidates | Select and accept a narrow capability before planning implementation. See [NEXT_DELIVERY_CANDIDATES.md](./future/NEXT_DELIVERY_CANDIDATES.md). |

### Next Priority

Unblock the submission metadata database contract first. Agree how SIMS-issued target IDs interact with SEAD sequences, implement the agreed behavior without bypassing SIMS, and rerun the inline INSERT and copy-CSV checks on separate disposable clones. Keep the task plan open until both strategies pass, including checks that subsequent default-generated IDs cannot collide.

The other open workstreams are separate decisions, not prerequisites for that validation. Do not treat the whole proposal portfolio as complete while cutover and independent proposals remain open.

## SEAD Change Request Ingester MVP

The MVP delivery uses DataFrame-first ingestion, identity resolution before SQL generation, reconciliation-first handling for existing classifier matches, and forward-only change-package generation. New tracked aggregates may use generic SIMS allocation where validated service configuration permits it. Existing rows with `public_id` remain reference-only; unresolved blocked rows stop the run before SQL generation.

See the [closed MVP proposal](./done/CHANGE_REQUEST_INGESTER_MVP/SEAD_CHANGE_REQUEST_INGESTER.md) for the accepted design and [implementation plan](./done/CHANGE_REQUEST_INGESTER_MVP/MVP_IMPLEMENTATION_PLAN.md) for its record.

## Active Documents

- [Submission metadata proposal](./REFACTOR_SEAD_SUBMISSION_METADATA.md) and [task plan](./REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md)
- [Cutover and deployment workstream](./CUTOVER_AND_DEPLOYMENT/README.md)
- [Shared-data review proposal](./SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md)
- [Ingester authorization proposal](../INGESTER_AUTHORIZATION_TASKS/INGESTER_AUTHORIZATION_TASKS.md)
- [Ingester filesystem proposal](../INGESTER_FILESYSTEM_BOUNDARIES/INGESTER_FILESYSTEM_BOUNDARIES.md)
- [Next-delivery candidates](./future/NEXT_DELIVERY_CANDIDATES.md)
- [Stronger idempotency and resubmission proposal](../INGESTER_IDEMPOTENCY_AND_RESUBMISSION/INGESTER_IDEMPOTENCY_AND_RESUBMISSION.md)

## Completed And Historical Records

- [Frontend workflow integration](./done/FRONTEND_UX_INTEGRATION_CR.md) and [issue record](./done/FRONTEND_UX_INTEGRATION_ISSUES.md)
- [SIMS identity allocation contract](./done/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_CONTRACT.md) and [completed phase plan](./done/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md)
- [Provider-submission lifecycle archive](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/README.md)
- [September 24, 2026 status assessment](./archive/STATUS_ASSESSMENT_2026-09-24.md), retained as a historical snapshot and superseded by this README

## Related References

- [Shape Shifter Design](../../DESIGN.md)
- [Configuration Guide](../../CONFIGURATION_GUIDE.md)
- [Developer Guide](../../DEVELOPMENT.md)
- [Ingester System](../../../backend/app/ingesters/README.md)
