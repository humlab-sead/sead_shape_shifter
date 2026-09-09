# Proposal: Shared Data Review And Operator Contract

## Status

- Draft
- Handoff from the provider-submission lifecycle work
- Separate proposal for shared-data ownership, review routing, and operator-visible outcomes

## Handoff

The provider-submission lifecycle work now covers provider-owned corrections, no-op reruns, and existing-row update handling.

This proposal starts where that work stops. It handles the cases where Shape Shifter is used for SEAD-owned internal data as well as provider submissions, and where new shared data should be allowed for internal SEAD workflows but prohibited for external provider ingest.

The split is deliberate:

- provider-owned rows follow the ownership-first lifecycle rules in the archived data-provider submission lifecycle docs
- shared terms, shared lookups, and other shared rows need a separate review and operator contract
- provider submissions must not create new shared data through the default provider-owned update path

## Purpose

Define how shared-data requests are routed, reviewed, and reported so the system can handle both internal SEAD-owned ingest and external provider ingest without mixing the two paths.

## Scope

This proposal covers:

- who owns reviewed shared-data requests
- when a request should go to shared-data review instead of the provider-owned path
- how operator-facing outcomes should describe review, approval, block, and no-op cases
- how external provider ingest should prevent new shared data from being created directly

## Non-Goals

- redefining provider-owned lifecycle rules
- changing the durable lifecycle baseline for provider submissions
- implementing database schema changes in this document
- designing frontend screens in detail

## Problem

Shape Shifter is used in two different ways:

- internal SEAD ingest for SEAD-owned data, including new shared data
- external provider ingest, where new shared data should be blocked

Those two uses need different routing rules. If the system treats all shared-data cases like provider-owned updates, it can either allow unsafe shared-term changes or block valid SEAD-owned review work.

## Candidate Workflows

1. Current internal reconciliation workflow.

   Shape Shifter performs reconciliation inside the ingester and routes shared-data cases to SEAD review. This is the current boundary and is not published to providers.

2. Provider-facing reconciliation service.

   A future provider-facing view or service lets data providers reconcile against shared lookups before data is sent to SEAD. This reduces failed submissions, but it must still respect SEAD ownership and avoid duplicate shared values.

3. Third-party authority-backed lookup workflow.

   For shared concepts with trusted external authorities, the provider can select an authority-backed match before submission. SEAD then records the resolved shared value without duplicating the lookup.

4. Shared-data request workflow.

   When no safe match exists, the provider submits a shared-data request for review. SEAD owns the decision and publication of the shared lookup, and the result can later be reused by providers.

## Relationship To Provider Lifecycle Docs

- The archived provider lifecycle docs live in [../done/DATA_PROVIDER_SUBMISSION_LIFECYCLE](../done/DATA_PROVIDER_SUBMISSION_LIFECYCLE)
- The archived lifecycle plan and issue drafts describe the provider-owned path that was completed first
- The shared-data path is now a separate proposal so the ownership rules stay clear

## Next Step

Refine the review ownership, approval path, and operator outcome contract for shared data before wiring new ingest behavior into the provider or SEAD workflows.
