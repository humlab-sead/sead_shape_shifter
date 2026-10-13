# Proposal: Shared Data Review And Operator Contract

## Status

- Draft
- Handoff from the provider-submission lifecycle work
- Separate proposal for shared-data ownership, review routing, and operator-visible outcomes

## Summary

Keep the Change Request Ingester MVP limited to binding existing shared lookup values. A lookup miss blocks or returns a review outcome; it does not create a value or start an operator request. Post-MVP, an authorized internal operator may start a shared-data request from a reconciliation no-match. The request must be reviewed and approved before publication. Normal external provider ingest must not create shared values.

## Handoff

The provider-submission lifecycle work now covers provider-owned corrections, no-op reruns, and existing-row update handling.

This proposal starts where that work stops. It considers a future reviewed path for shared-data requests in internal SEAD workflows. That path is not part of the current MVP and does not change the provider-submission lifecycle rules.

The split is deliberate:

- provider-owned rows follow the ownership-first lifecycle rules in the archived data-provider submission lifecycle docs
- shared terms, shared lookups, and other shared rows need a separate review and operator contract
- normal provider ingest must not create new shared data, directly or through the provider-owned update path

## Purpose

Define how shared-data requests are routed, reviewed, and reported so the system can handle both internal SEAD-owned ingest and external provider ingest without mixing the two paths.

## Scope

This proposal covers:

- who owns reviewed shared-data requests
- when a request should go to shared-data review instead of the provider-owned path
- whether an authorized internal operator can start a request from a reconciliation no-match
- how operator-facing outcomes should describe review, approval, block, and no-op cases
- how external provider ingest should prevent new shared data from being created directly
- how shared-lookup rules align with SIMS identity allocation capabilities

## Non-Goals

- redefining provider-owned lifecycle rules
- changing the durable lifecycle baseline for provider submissions
- implementing database schema changes in this document
- designing frontend screens in detail
- allowing reconciliation or SIMS identity allocation to publish a shared lookup without review and approval

## Problem

Shape Shifter is used in two different ways:

- internal SEAD ingest for SEAD-owned data, which may need a governed way to request new shared data
- external provider ingest, which must not create shared data through its normal ingest path

Those two uses need different routing rules. Treating a reconciliation miss as permission to create a lookup risks unreviewed shared-data changes. Treating every miss as a provider-owned update can also obscure a future, review-governed internal request path.

## Current Behavior

- Reconciliation looks up existing shared values. On a miss, the current lookup-only path blocks; it does not create a lookup or start a shared-data request.
- The current Change Request Ingester MVP binds existing lookups only. A no-match may be reported as a review outcome, but that outcome does not itself create a request or value.
- The SIMS `allocate_new` capability concerns allocation of a tracked identity. It does not authorize reconciliation to create or publish a shared lookup.
- The current SIMS identity policy enables `allocate_new` for `site` and `sample_group`. Both have `role: lookup` in the supplied SEAD standard model. This capability configuration must be reconciled with the MVP rule; it is not by itself an exception to shared-data review.

## Proposed Design

### MVP And Post-MVP Boundary

- **MVP:** Bind existing shared lookup values. A no-match blocks or returns a review outcome. Do not create a value or initiate an operator-triggered shared-data request.
- **Post-MVP:** Let an authorized internal operator initiate a shared-data request from a reconciliation no-match. Reconciliation creates a reviewable request or change-request artifact, not the shared lookup itself. Check for duplicates and record audit and provenance details. Publish the lookup only after the required approval.
- **Provider ingest:** Do not create shared values through the normal external provider ingest path. A reconciliation request action for internal operators must not make that path capable of publishing shared data.

### Workflow Options

1. **Current lookup-only reconciliation.** Reconcile against existing shared values. A no-match blocks or returns a review outcome without creating a value or request.

2. **Post-MVP internal shared-data request (recommended).** An authorized internal operator starts a request from a no-match. SEAD reviews it, checks for duplicates, records its provenance, and publishes the shared lookup only after approval.

3. **Provider-facing reconciliation service (future option).** A provider-facing view or service could let providers reconcile against shared lookups before submission. It must respect SEAD ownership and must not create or publish shared values through normal provider ingest.

4. **Third-party authority-backed lookup (future option).** For concepts with trusted external authorities, a provider could select an authority-backed match before submission. SEAD would record the resolved value without duplicating the lookup. This option does not grant providers permission to create shared values.

## Risks And Tradeoffs

- Requiring review and approval adds time before a requested lookup becomes available, but prevents reconciliation or provider ingest from publishing unreviewed shared data.
- Leaving the `site` and `sample_group` allocation policy unresolved can make configured identity capabilities disagree with the bind-existing-only MVP. Resolve this before treating the MVP policy as complete.

## Testing And Validation

- Verify that an existing lookup can be bound and that a no-match blocks or returns a review outcome without creating a lookup or request during the MVP.
- For the post-MVP flow, verify that an authorized operator creates a review artifact only; duplicate checks, audit/provenance, approval, and publication are enforced as specified.
- Verify that normal external provider ingest cannot create or publish shared values.
- Verify that the `site` and `sample_group` allocation settings match the resolved MVP policy.

## Relationship To Provider Lifecycle Docs

- The archived provider lifecycle docs live in [DATA_PROVIDER_SUBMISSION_LIFECYCLE](../../CHANGE_REQUEST_INGESTER/done/DATA_PROVIDER_SUBMISSION_LIFECYCLE)
- The archived lifecycle plan and issue drafts describe the provider-owned path that was completed first
- This proposal adds a separate, post-MVP review path for shared data without changing the provider-owned lifecycle rules

## Acceptance Criteria

- `P-AC-1`: MVP reconciliation binds existing shared lookup values only. A no-match blocks or returns a review outcome and does not create a value or request.
- `P-AC-2`: Post-MVP, only an authorized internal operator can initiate a shared-data request from a reconciliation no-match; that action creates a reviewable artifact, not a shared lookup.
- `P-AC-3`: Shared lookup publication requires approval. The request process defines duplicate checks, audit and provenance details, and operator-visible outcomes.
- `P-AC-4`: Normal external provider ingest cannot create or publish shared values.
- `P-AC-5`: The `allocate_new` policy for `site` and `sample_group` is explicitly resolved and kept consistent with the MVP's bind-existing-only rule. SIMS identity allocation alone does not authorize shared lookup creation or publication.

## Open Questions

- Which internal roles may request shared-data changes, and which roles may approve and publish them?
- For the MVP, are `site` and `sample_group` explicit `allocate_new` exceptions, or does bind-existing-only require disabling those allocation paths for the relevant ingester operations? Both entities are lookup roles in the supplied model, while the current SIMS policy enables `allocate_new` for both. Define any exception by workflow and effect; do not treat it as permission to publish a shared lookup.
- What request fields and operator outcomes are required to support duplicate checks, audit, provenance, review, and approval?

## Next Step

Resolve review ownership and approval roles, the `site` and `sample_group` allocation policy, and the request and outcome requirements before implementing the post-MVP internal workflow. Keep the MVP limited to binding existing lookups and keep normal provider ingest unable to create shared values.

## Final Recommendation

Keep the MVP bind-existing-only. Treat reconciliation as the post-MVP entry point for an authorized internal operator to request a shared value, not to create or publish it. Require review and approval before publication, and resolve the current `site` and `sample_group` allocation settings before claiming the MVP policy is consistent.
