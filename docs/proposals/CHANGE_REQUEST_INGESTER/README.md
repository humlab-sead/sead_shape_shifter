# SEAD Change Request Ingester

## Purpose

This directory contains the active and archived proposals for the `sead_change_request` ingester. This README is the portfolio overview and consolidated status tracker. Update it when a workstream changes status; keep task-level checklists and validation results in their owning plans and handoffs.

## Current Status

**Overall:** The SEAD Change Request Ingester MVP Delivery (historically, Delivery 1), provider-submission lifecycle, and submission metadata work are complete. The submission package contract passed disposable PostgreSQL validation; upstream schema deployment and legacy compatibility remain release dependencies. Cutover and separate follow-up proposals remain open or undecided.

The MVP delivery includes:

- Identity-aware row handling: use SIMS to allocate IDs for new provider-owned aggregates where configured; reconcile and bind existing shared lookups and classifiers. A missing shared lookup does not create a new value in the MVP and blocks that row.
- Safe relationship handling: resolve local system_id references to SEAD IDs. Evaluate bridge and association rows independently, using metadata-defined uniqueness rules.
- Fail-closed generation: stop before SQL output if identities are unresolved, Binding Set confirmation is incomplete, or target-side collision checks fail. Return diagnostics rather than a partial package.
- A forward-only package: generate INSERT statements and package metadata. Revert and verify files, when required, are explicit placeholders; the package is marked non-revertible. Deferred foreign-key checks are the preferred insert strategy.
- It deliberately does not include rollback, updates or deletes, broad semantic duplicate detection, advanced change detection, or immediate retirement of the existing Clearinghouse ingester. Those were left for separate follow-up work or candidate proposals. Frontend integration and persisted submission metadata/defaults were also handled separately, not as part of this closed baseline.

Status reviewed 2026-10-17. No new PostgreSQL validation was run for this update.

| Workstream | Status | Remaining work / next action |
|---|---|---|
| SEAD Change Request Ingester MVP and baseline follow-ups | Complete | Historical MVP Delivery records are under [done/CHANGE_REQUEST_INGESTER_MVP](./done/CHANGE_REQUEST_INGESTER_MVP). |
| Deployment-time staging | Inline staging implemented | The inline staging work merged in [PR #565](https://github.com/humlab-sead/sead_shape_shifter/pull/565); copy-CSV parity and Sqitch promotion remain separate follow-up work. See the [completed proposal and phase plans](./done/DEPLOYMENT_TIME_STAGING/DEPLOYMENT_TIME_STAGING.md). |
| Frontend workflow and persisted defaults | Complete | Frontend integration shipped in PR #456; stable metadata defaults are implemented and covered by the submission metadata work. |
| Provider-submission lifecycle | Complete | Rules are promoted to the [durable lifecycle reference](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md); implementation history is under [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE). |
| Submission metadata and generated packages | Complete | Both artifact strategies passed contract checks on separate disposable clones, including PostgreSQL sequence advancement. Upstream schema deployment and legacy compatibility remain release dependencies tracked in the [cutover and deployment workstream](./CUTOVER_AND_DEPLOYMENT/README.md). See the [completed proposal and task plan](./done/REFACTOR_SEAD_SUBMISSION_METADATA/REFACTOR_SEAD_SUBMISSION_METADATA.md). |
| SIMS-SEAD adoption, cutover, and deployment | Draft; decisions open | Resolve tracked-entity mapping, missing UUIDs, backfill and writer ordering, upstream schema/compatibility ownership, and package supersession. Track in [CUTOVER_AND_DEPLOYMENT](./CUTOVER_AND_DEPLOYMENT/README.md). |
| Ingester authorization and filesystem access | Proposed; not ready to enable | Define and implement resource authorization and filesystem containment. Keep operations unavailable until required checks are enforced. See the [authorization proposal](../INGESTER_AUTHORIZATION_TASKS/INGESTER_AUTHORIZATION_TASKS.md) and the [target-bundle access proposal](../done/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md). |
| Post-MVP proposals | Deferred; no combined delivery accepted | Select and accept a narrow capability before planning implementation. See the [post-MVP proposal portfolio](../CHANGE_REQUEST_INGESTER_POST_MVP/README.md). |

### Next Priority

Finish the separate SIMS-SEAD cutover decisions and release gates. The submission metadata package contract is complete: inline INSERT and copy-CSV artifacts passed disposable PostgreSQL checks with SIMS-assigned IDs and verified sequence advancement. The broader cutover work still requires upstream schema deployment, compatibility ownership, and identity-coverage checks.

The other open workstreams are separate decisions, not prerequisites for that validation. Do not treat the whole proposal portfolio as complete while cutover and independent proposals remain open.

## SEAD Change Request Ingester MVP

The MVP delivery uses DataFrame-first ingestion, identity resolution before SQL generation, reconciliation-first handling for existing classifier matches, and forward-only change-package generation. New tracked aggregates may use generic SIMS allocation where validated service configuration permits it. Existing rows with `public_id` remain reference-only; unresolved blocked rows stop the run before SQL generation.

See the [closed MVP proposal](./done/CHANGE_REQUEST_INGESTER_MVP/SEAD_CHANGE_REQUEST_INGESTER.md) for the accepted design and [implementation plan](./done/CHANGE_REQUEST_INGESTER_MVP/MVP_IMPLEMENTATION_PLAN.md) for its record.

## Active Documents

- [Cutover and deployment workstream](./CUTOVER_AND_DEPLOYMENT/README.md)
- [Ingester authorization proposal](../INGESTER_AUTHORIZATION_TASKS/INGESTER_AUTHORIZATION_TASKS.md)
- [Target-bundle access proposal](../done/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md)
- [Post-MVP proposal portfolio](../CHANGE_REQUEST_INGESTER_POST_MVP/README.md)

## Completed And Historical Records

- [Frontend workflow integration](./done/FRONTEND_UX_INTEGRATION_CR.md) and [issue record](./done/FRONTEND_UX_INTEGRATION_ISSUES.md)
- [SIMS identity allocation contract](./done/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_CONTRACT.md) and [completed phase plan](./done/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md)
- [Provider-submission lifecycle archive](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/README.md)
- [Deployment-time staging](./done/DEPLOYMENT_TIME_STAGING/DEPLOYMENT_TIME_STAGING.md)
- [Submission metadata proposal](./done/REFACTOR_SEAD_SUBMISSION_METADATA/REFACTOR_SEAD_SUBMISSION_METADATA.md) and [completed task plan](./done/REFACTOR_SEAD_SUBMISSION_METADATA/REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md)
- [September 24, 2026 status assessment](./archive/STATUS_ASSESSMENT_2026-09-24.md), retained as a historical snapshot and superseded by this README

## Related References

- [Shape Shifter Design](../../DESIGN.md)
- [Configuration Guide](../../CONFIGURATION_GUIDE.md)
- [Developer Guide](../../DEVELOPMENT.md)
- [Ingester System](../../../backend/app/ingesters/README.md)
