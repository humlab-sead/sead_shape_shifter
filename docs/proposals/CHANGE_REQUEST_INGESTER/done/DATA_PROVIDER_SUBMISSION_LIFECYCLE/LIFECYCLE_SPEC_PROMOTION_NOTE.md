# Archive Note: Lifecycle Specification Promotion

## Status

- Complete
- Created: 2026-06-30
- Scope: document the promotion path for the accepted lifecycle baseline from proposals into durable docs

## Summary

`DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md` is now the accepted lifecycle baseline for provider-submission rules.

This note records the promotion target, alignment checks, and the final completion state for the move into the main documentation set.

## Completed Scope

- confirmed source baseline document:
  - [DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md](../DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md)
- confirmed governing decision document:
  - [DATA_PROVIDER_UPDATE_SCOPING_CR.md](../DATA_PROVIDER_UPDATE_SCOPING_CR.md)
- defined target durable-doc path:
  - [docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md)
- defined minimum promotion checks:
  - preserve lifecycle invariants and state-transition contract
  - preserve allowed/restricted/blocked change classes
  - preserve one-live-version and history rules
  - keep implementation sequencing in phase-plan docs, not in durable lifecycle rules

## Validation Performed

- cross-checked current proposal-set status labels in:
  - [README.md](../README.md)
  - [CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md](../CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md)
- confirmed the specification text already states accepted-baseline status and a promotion rule.

## Remaining Follow-Up

- [x] create [docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md) from the accepted baseline content
- [x] update links in proposal docs to point to the durable lifecycle page
- keep [DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md](../DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md) as a proposal-era history record with a short pointer to the durable page
