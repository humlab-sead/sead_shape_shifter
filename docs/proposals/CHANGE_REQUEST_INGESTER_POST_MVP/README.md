# SEAD Change Request Ingester Post-MVP Proposals

## Status

- Deferred; no combined post-MVP delivery is approved.
- MVP support for shared lookups is limited to binding existing records. Creation and review of new shared values are deferred.

## Purpose

Collect proposal work that is outside the closed Change Request Ingester MVP without implying that the topics form one accepted delivery.

Existing MVP behavior for provider-owned aggregate allocation remains governed by the closed MVP contract. This portfolio does not change that behavior.

## Proposals

| Topic | Status | Scope |
|---|---|---|
| [Next-delivery candidates](NEXT_DELIVERY_CANDIDATES.md) | Undecided | Record capability candidates without committing to one combined delivery. |
| [Existing-row update handling](UPDATE_HANDLING_FOR_EXISTING_ROWS.md) | Candidate, not accepted | Define safe updates to existing target rows. |
| [Shared-data review and operator contract](SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md) | Draft | Define internal review and operator outcomes for new shared data; keep direct provider creation prohibited. |
| [Idempotency and re-submission](INGESTER_IDEMPOTENCY_AND_RESUBMISSION/INGESTER_IDEMPOTENCY_AND_RESUBMISSION.md) | Proposed; contract decisions pending | Define deterministic reruns, partial overlap, and recovery from interrupted requests. |

## Boundary

These proposals do not reopen or expand the closed MVP acceptance baseline. A post-MVP proposal must be selected and accepted on its own before implementation planning.