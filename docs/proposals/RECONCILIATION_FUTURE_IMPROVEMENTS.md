# Reconciliation Future Improvements Proposal

**Author**: TBD
**Status**: Placeholder
**Scope**: Deferred reconciliation workflow improvements beyond explicit export-to-mapping

---

## Summary

This placeholder proposal tracks reconciliation workflow improvements that are intentionally out of scope for [RECONCILIATION_PERSISTENCE_CONSOLIDATION.md](RECONCILIATION_PERSISTENCE_CONSOLIDATION.md).

The consolidation proposal keeps REQ #5 to explicit "Export to Mapping" copy only. This document captures the next-stage enhancements.

---

## Deferred Items

1. Add draft/committed reconciliation states with full review UI.
2. Add reconciliation status model updates (for example, EntityResolutionSet lifecycle states).
3. Add audit logging for reconciliation acceptance and export actions.
4. Add rollback capability for exported/accepted reconciliation links.
5. Align export key handling with sidecar `local_key` semantics instead of writing raw reconciliation `source_value` strings.

---

## Problem

Explicit export is enough for current delivery scope, but it does not provide a full reconciliation lifecycle for teams that need staged review, traceability, and reversible decisions.

The current export step also assumes that the reconciliation field value is the same as the sidecar `local_key` value. That works when the reconciled field and the sidecar key are the same column, but it breaks when reconciliation uses one field and normalization later looks up links by a different `local_key`.

---

## Scope

In scope for this future proposal:
- Lifecycle states for reconciliation results.
- Reviewer-driven accept/reject workflows.
- Audit history for mapping changes from reconciliation.
- Rollback and recovery behavior.
- Export-time translation from reconciliation field values to the entity sidecar `local_key` format.

Out of scope for this future proposal:
- options.mapping legacy support.
- Materialized replace-on-save mapping sync semantics.

---

## Next Step

Expand this placeholder into a full proposal when the team decides to prioritize advanced reconciliation governance and UX.
