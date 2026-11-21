# Reconciliation Search and Browse: Phase 2 Frozen Save Contract

## Status

Frozen on 2026-11-19 for Phase 2 planning and revised the same day to move stale-view
detection out of Phase 2. The proposal
[owns the semantics](./RECONCILIATION_SEARCH_AND_BROWSE.md); this document fixes the
wire-level and persistence details that the
[phase plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_PLAN.md#phase-2-atomic-decisions-and-verified-export)
lists as blocking decisions. Implementation has not started.

Revision 2 removes the client-supplied catalog precondition that revision 1 recorded as `D2` and `D4`.
Phase 2 relies on the per-project lock that already serializes catalog writes, and the long-lived review
workspace owns stale-view detection in Phase 3, as `PH3-AC-6` records.

The decisions below were taken explicitly and are not open for reinterpretation during implementation:

| ID | Decision | Choice |
|---|---|---|
| `D1` | Contract location | This document, linked from Phase 2. |
| `D2` | Changed source row | The encoded business key must resolve, and every displayed value the client sent must still match the resolved row. |
| `D3` | Concurrent catalog writes | No client-supplied hash. Every writer loads, changes, and saves the catalog under `ProjectService._get_lock`, so unrelated changes are never lost. Two writes to the same business key are last-writer-wins. |
| `D4` | Stale-view detection | Deferred to Phase 3, which owns the workspace view that can outlive a read. |

## Purpose

Give Phase 2 one reference for the batch save, save-time source-row validation, the shared reference
validator, catalog write serialization, and error shapes so that implementation and validation do not
re-decide them.

## Scope

- **Fixed here:** the serialized catalog write rule, the batch decision request and response, save-time
  source-row validation, the shared local reference validator, and error shapes.
- **Not fixed here:** stale-view detection and any client-supplied precondition, export and sidecar behavior
  beyond the verification requirement, the browser draft format, review-queue presentation, keyboard bindings,
  search/browse client behavior, and per-type capability release. Those belong to Phase 3 and Phase 4.

## Verified Current State

Repository basis: Shape Shifter `reconciliation-search-and-browse` at `5727bed8`.

| Area | Current behavior | Consequence |
|---|---|---|
| `backend/app/models/reconciliation.py` | `EntityResolutionCatalog` has `version: str` (default `"3.0"`), `service_url`, and `entities: dict[str, dict[str, EntityResolutionSet]]`. `EntityResolutionSet` has `source`, `property_mappings`, `remote`, `auto_accept_threshold`, `review_threshold`, and `mapping: list[ResolvedEntityPair]`. `ResolvedEntityPair` has `local_key_value`, `source_value`, `status` (`proposed`/`accepted`/`rejected`/`local-only`), `target_id`, `candidate_id`, `confidence`, `notes`, `candidates`, and timestamps. | Decisions live in one YAML document per project, so a whole-catalog precondition would be coarser than the per-key writes it guards. Phase 2 changes decisions per business key instead. |
| `backend/app/services/reconciliation/mapping_manager.py` | `save_catalog` writes `model_dump(exclude_none=True)` through a temporary file and `os.replace`. `load_catalog` returns a default catalog when the file is absent and rejects versions other than `"3.0"`. | A failed write leaves the previous catalog intact, so all-or-nothing needs no additional mechanism. |
| `backend/app/services/reconciliation/service.py` | `update_mapping` rejects a business key with no existing row (`run matching first`). `delete_decision`, `mark_as_unmatched`, `replace_catalog`, and `delete_specification` write the whole catalog and run inside `self.project_service._get_lock(project_name)`. `replace_catalog` also removes owned sidecar links for dropped specifications. | First-time decisions are currently impossible; the batch route must add them without changing the lock or the side-effect rules. |
| `backend/app/services/reconciliation/service.py::auto_reconcile_entity` | Matching merges its proposals into a freshly loaded catalog and skips decisions that are not `proposed`. The no-service-type threshold path saves without the project lock. | A decision saved during matching already survives. Only the unlocked threshold write needs the lock; no precondition is needed. |
| `backend/app/api/v1/endpoints/reconciliation.py` | `POST /reconciliation/mapping-registry` and `PUT /reconciliation/mapping-registry/{entity_name}/{target_field}` call `catalog_manager.create_entity_mapping` and `update_entity_mapping` directly. `mapping_manager` takes no lock. `DELETE` goes through `delete_specification`, which does lock. | These two routes can lose a concurrent write. Closing that gap is part of Phase 2. |
| `backend/app/services/reconciliation/service.py` | `_extract_id_from_uri` matches a trailing `/123` on any host and path. No type-aware validator exists. | `P-AC-5` cannot be met until a shared validator replaces this. |
| `backend/app/utils/error_handlers.py` | `ValidationError` maps to HTTP 400 and `ResourceConflictError` to 409, both with `detail` equal to `{error_type, error_code, message, tips, recoverable, context}`. | Row issues attach to `detail` without inventing a new envelope. |
| `backend/app/services/reconciliation/service.py` | `get_resolved_source_data` returns resolved rows plus the ordered business key and reports missing or duplicate key rows; `QueryBuilder.index_rows` encodes the key. | Save-time validation must reuse this, not re-derive row identity. |
| `frontend/src/stores/reconciliation.ts` | Calls the catalog GET and both PUT routes. No route takes a precondition today. | Phase 2 adds none, so these call sites do not change. |

## Frozen Contracts

### 1. Serialized catalog writes

Every write loads the catalog, changes only its own decisions or specification, and saves, all inside
`ProjectService._get_lock(project_name)`:

| Writer | Lock today |
|---|---|
| `update_mapping`, `delete_decision`, `mark_as_unmatched` | Yes. |
| `replace_catalog`, `delete_specification` | Yes. |
| `create_entity_mapping`, `update_entity_mapping` (registry create and update routes) | **No.** Phase 2 moves them behind the lock. |
| `auto_reconcile_entity` merge write | Yes. Its no-service-type threshold write does not take the lock; Phase 2 fixes that path. |

Rules:

- A writer never saves a catalog it loaded outside the lock.
- A writer applies its own decisions to the loaded catalog instead of replacing it wholesale, so a concurrent
  change to another business key survives.
- Two writes to the same business key are last-writer-wins. Phase 2 does not detect or report that case; the
  Phase 3 workspace owns the stale-view warning.
- No route gains a precondition field, a query parameter, or a new conflict status. Request payloads and
  response shapes stay as they are, so no client, script, or CLI changes in Phase 2.
- Work that needs `await`, such as source resolution, happens before the lock is taken. Nothing awaits while
  holding `_get_lock`, because it is a non-reentrant `threading.Lock` shared with other async routes.

### 2. Catalog read

`GET /projects/{project_name}/reconciliation` keeps its current body and its `require_project(Action.READ)`
authorization. Phase 2 adds no field to it.

### 3. Batch decision request

`POST /projects/{project_name}/reconciliation/{entity_name}/{target_field}/decisions` with `require_project(Action.EDIT)`.

```json
{
  "drafts": [
    {
      "local_key_value": "sample:42",
      "displayed_values": {"sample_name": "Alpha", "site_name": "Uppsala"},
      "status": "accepted",
      "target_id": 123,
      "candidate_id": "https://w3id.org/sead/id/feature_type/123",
      "notes": null
    }
  ]
}
```

- `drafts` must be non-empty and at most one entry per `local_key_value`.
- `status` accepts exactly `"accepted"` or `"local-only"`. `"accepted"` requires both `target_id` and `candidate_id`; `"local-only"` requires neither. `"proposed"` and `"rejected"` remain writable only through the legacy routes.
- `displayed_values` holds the columns the operator saw, as the client rendered them. They are change-detection input only and are never written as source data.
- `local_key_value` is the encoded ordered business key already used by the catalog. The batch does not accept a raw key component list.
- The request carries no catalog precondition. The endpoint applies the drafts to the catalog it loads under the project lock.
- The endpoint performs no Authority details or existence call and writes no sidecar link.

### 4. Batch decision response

`200` on success:

```json
{
  "saved": [
    {
      "local_key_value": "sample:42",
      "status": "accepted",
      "target_id": 123,
      "candidate_id": "https://w3id.org/sead/id/feature_type/123",
      "notes": null,
      "last_modified": "2026-11-19T15:04:05+00:00"
    }
  ],
  "counts": {
    "saved": 1,
    "accepted": 1,
    "local_only": 0,
    "specification": {"accepted": 40, "local_only": 8, "proposed": 5, "rejected": 0, "total": 53}
  }
}
```

- `saved` echoes one entry per stored draft, accepted and local-only, in request order.
- `counts.saved`, `counts.accepted`, and `counts.local_only` describe this batch. `counts.specification` holds the post-save totals for the specification so the client can patch queue counts without recomputing them.
- The response does not include the whole catalog. Clients patch affected rows from `saved`.

### 5. Save-time source-row validation

Steps 1-5 run before the project lock is taken. Steps 6-8 run inside `self.project_service._get_lock(project_name)`. The order is fixed so a doomed request fails cheaply and deterministically, and so nothing awaits while the lock is held.

1. Resolve current source rows once with `get_resolved_source_data(project_name, entity_name, entity_mapping)`, regardless of draft count. The resolution is fresh: it must not reuse cached preview rows or cached dependency frames, because an external source change leaves the cache valid.
2. If resolution reports missing or duplicate business-key rows, reject the whole batch with `source_resolution_failed`. Keys cannot be trusted against an incomplete index.
3. Reject the whole batch if any draft key is malformed, repeated, or absent from the resolved rows. Codes: `invalid_draft`, `duplicate_draft`, `row_not_found`.
4. For each draft, compare every key in `displayed_values` with the resolved row. A missing column or a different value rejects the batch with code `row_changed` and the column name in `field`.
   - Comparison is on canonical JSON of each value (`json.dumps(value, sort_keys=True, default=str)`) with one relaxation: numerically equal integers and floats compare equal (`1` equals `1.0`). Dates and datetimes compare as ISO strings.
5. For `accepted` drafts, run the shared local reference validator (section 6). Failures reject the batch with `invalid_reference`.
6. Take the project lock and load the catalog. A `local-only` draft must not silently clear a conflicting protected manual link or an existing public ID. Use the established export/ingester conflict rules and reject the batch with `protected_link`.
7. Build the decision objects. For an accepted decision, take `source_value` from the resolved row, keep
   `created_at`, `created_by`, and `candidates` from an existing decision, and set `last_modified` to now. A new
   decision gets `source_value` from the resolved row, an empty `candidates` list, `created_by: "user"`, and
   `created_at` set to now.
8. Apply every decision to the loaded catalog, then call `save_catalog` once. A write failure leaves the catalog file unchanged and preserves every draft.

Rejections are all-or-nothing: no partial catalog write, and the response carries every issue found, not just the first.

### 6. Shared local reference validator

One function validates an accepted reference everywhere it matters: batch accepts, legacy decision writes,
whole-catalog JSON/YAML replacement, catalog read diagnostics, and export preflight. A whole-catalog replacement
validates every accepted reference it contains before changing the catalog or any owned sidecar link.

Required checks:

- The URI is absolute: it parses, has a scheme and a host, and has no query string or fragment.
- The path ends with exactly two segments: the expected type for the specification, taken from its
  `remote.service_type`, then the numeric ID. No segment follows the ID.
- The final segment is positive ASCII decimal, so leading zeros are accepted.
- The value fits a PostgreSQL `integer`.
- `target_id` equals the URI's integer ID.

The validator deliberately does not compare the scheme, host, or base path with a configured identifier base.
That comparison needs the Authority manifest `identifierSpace`, whose cache expires after 30 seconds and is lost
on restart, so it would make local validation depend on a reachable service. Type, ID, and agreement checks plus
export verification already cover the risk: a reference from another host must still echo the expected type and
ID and resolve to the same `aggregate_id` when it is exported.

The validator is local and offline. It cannot establish that a target exists, and it cannot tell a country
`location_id` from another location type. Country membership and existence stay with export verification, as
`P-AC-5`, `P-AC-12`, and `PH2-AC-4` require.

The current `_extract_id_from_uri` regular expression does not satisfy these checks and is replaced. This
mirrors the Authority Service helper in `sead_authority_service/src/record_identifiers.py`, but it is a Shape
Shifter-side implementation; Shape Shifter does not import from `src/` of the other repository.

### 7. Error shapes

Errors keep the existing envelope: `HTTPException(detail=exception.to_dict())`, so the body is `{"detail": {"error_type", "error_code", "message", "tips", "recoverable", "context"}}`.

- Row issues are added as `detail.issues`, a list of `{row_index, local_key_value, field, code, message}`. `row_index` is the server's index in the resolved rows or `null`; `field` is `null` unless a single column caused the issue. Every entry identifies its row by index or key.
- Draft and row validation failures return `400`, which is the existing `ValidationError` mapping. That status is retained so the envelope does not change; `P-AC-6` constrains atomicity and reporting, not the status code.
- An unknown specification returns `404`.
- Authorization stays with `require_project(Action.EDIT)`, which already raises `HTTPException(403)` for an unpermitted caller. The batch route adds no authorization path.

## Compatibility

- No catalog route changes its payload, its response, or its status codes in Phase 2. The frontend, the CLI in `scripts/project/auto_reconcile.py`, and any script using these routes keep working unchanged.
- Concurrent writes are serialized in-process by the project lock. Two processes, such as the CLI and the server, are not coordinated by that lock. That matches current behavior and is recorded as a risk in the phase plan.
- Catalogs that predate this contract are read normally, provided they declare version `"3.0"`. Version `"2.0"` and unversioned catalogs keep their current ignore-and-recreate behavior.

## Validation Requirements

Phase 2 must demonstrate, for this contract:

- A batch creates first-time accepted and `local-only` decisions for rows with no prior catalog entry, and resolves source rows once regardless of draft count.
- Missing, duplicate, unauthorized, and changed rows each reject the whole batch, report every issue, and leave the catalog file byte-identical.
- Registry create and update, a decision write, and a matching write cannot interleave: each saves a catalog that still contains the others' changes.
- Two batches that touch the same business key leave one deterministic decision and a readable catalog.
- The shared validator rejects a wrong type, a missing type segment, an extra path segment, a query, a fragment, a non-positive ID, an overflow ID, and mismatched URI/`target_id` pairs on batch accepts, legacy decision writes, whole-catalog replacement, and export preflight.
- Invalid legacy entries stay visible with row-specific issues, a replacement containing any invalid reference writes nothing, and valid prior manual reconciliations remain reusable.
- Saving does not call Authority details or existence endpoints, and no save writes a sidecar link.

## Deferred

- Stale-view detection, client-supplied catalog preconditions, conflict refresh, and conflict reapply. These belong to Phase 3.
- The browser draft format and its storage keys. These belong to Phase 3.
- Server paging, exact filtered totals, and recent-query history.
- Per-row version storage or server-side review sessions.
- Policy for links exported unverified by earlier versions.
- Any change to export verification beyond requiring it for accepted links.

## References

- [Proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md): semantics and acceptance criteria.
- [Phase plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_PLAN.md#phase-2-atomic-decisions-and-verified-export): sequencing and milestones.
- [Phase 1 task plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_1_TASK_PLAN.md): the delivered Authority Service contract this phase consumes.
- `sead_authority_service/src/record_identifiers.py`: Authority-side URI parser the validator must agree with.
