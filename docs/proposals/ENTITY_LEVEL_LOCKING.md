# Entity-Level Optimistic Locking

## Status

- Proposed feature / change request
- Scope: backend API, entity editor client flow, YAML persistence hardening
- Goal: reduce false edit conflicts without redesigning the project model or cache architecture

## Summary

Shape Shifter currently has optimistic locking at the project level. That is appropriate for whole-project save flows, but it is too coarse for the most frequent use case in the UI, where a user opens, edits, and saves one entity at a time.

This feature introduces entity-level optimistic locking for entity configuration updates. The mechanism should be based on a fingerprint of the logical entity content, not on the project cache and not on raw YAML text.

The recommended implementation is a small compare-and-swap flow around the existing entity update path:

1. Client fetches an entity and receives an entity ETag.
2. Client edits the entity.
3. Client sends the updated entity together with the ETag it originally fetched.
4. Server loads the latest entity state, compares ETags, and either:
    - accepts the update and persists it, or
    - rejects the update with `409 Conflict` if the entity has changed.

This reduces false conflicts compared with project-level locking while staying compatible with the current single-process FastAPI deployment and current project save pipeline.

## Why This Change Is Needed

### Current Behavior

- The backend already has project-level optimistic locking for whole-project saves.
- Entity updates currently go through the normal entity CRUD path and project save path.
- The server-side project cache is project-scoped and is primarily a performance mechanism, not the correct source of truth for fine-grained concurrency decisions.

### Problem

Two users or two browser tabs can legitimately edit different entities within the same project. With project-level locking, those independent edits can conflict even when the users are not touching the same entity.

That is the wrong granularity for the current product behavior.

### Constraint

This should not turn into collaborative editing, CRDT, OT, or automatic merging. We only need a clean optimistic concurrency check at the entity boundary.

## Recommended Design

### Core Principle

Treat each entity update as a small compare-and-swap transaction on `entities[entity_name]`.

The comparison unit should be the parsed entity data structure, not:

- the project cache version
- the raw YAML text
- file modification time alone
- project-level metadata

### ETag / Fingerprint

Compute an ETag from canonical JSON of the entity data:

```python
canonical = json.dumps(entity_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
etag = sha256(canonical.encode("utf-8")).hexdigest()
```

Properties:

- stable for logically identical entity content
- unaffected by YAML formatting differences
- affected only by meaningful entity content changes
- easy to recompute on both read and write paths

### Source of Truth

The source of truth for the concurrency check must be the latest project content loaded within the update transaction.

The server-side project cache should continue to exist as a cache, but it should not decide whether an entity update is stale. The cache can be updated after a successful save, as it is today.

## Why Not Use the Project Cache

The project cache is the wrong abstraction level for this feature.

Reasons:

- It is project-scoped, not entity-scoped.
- It exists to avoid repeated disk loads and to track active project state.
- It can legitimately be invalidated, refreshed, or replaced independently of user edit intent.
- Using it as the concurrency authority would couple optimistic locking to cache lifecycle rather than persisted entity state.

Entity-level locking should instead sit directly on the entity read/update flow.

## Proposed API Contract

### Read Entity

`GET /api/v1/projects/{project_name}/entities/{entity_name}` should return:

- entity name
- entity data
- entity ETag

Recommended shape:

```json
{
   "name": "sample_type",
   "entity_data": {
      "type": "fixed",
      "keys": ["sample_type_name"]
   },
   "etag": "3f7d..."
}
```

### Update Entity

`PUT /api/v1/projects/{project_name}/entities/{entity_name}` should accept:

- updated entity data
- expected ETag from the previous read

Recommended request body:

```json
{
   "entity_data": {
      "type": "fixed",
      "keys": ["sample_type_name", "sample_type_code"]
   },
   "expected_etag": "3f7d..."
}
```

### Conflict Response

When the expected ETag does not match the current entity ETag, return `409 Conflict` with enough information for the UI to react.

Recommended shape:

```json
{
   "error": "entity_conflict",
   "message": "Entity was modified by another user. Reload before saving.",
   "current_etag": "8a42...",
   "current_entity": {
      "name": "sample_type",
      "entity_data": {
         "type": "fixed",
         "keys": ["sample_type_name"]
      }
   }
}
```

Returning `current_entity` is recommended because it makes later UI improvements possible without changing the API again.

## Why Body Fields Are Preferred Here

This could be implemented with HTTP `ETag` and `If-Match` headers, but for this codebase the simpler choice is to put the ETag in the JSON body.

Reasons:

- The frontend entity store and API layer already work primarily with JSON body payloads.
- The entity editor already has a comparable pattern for external values optimistic locking, but entity config editing is currently simpler if it stays body-based.
- Returning and posting body fields avoids plumbing response headers through the existing API client abstractions.

This is slightly less strict from an HTTP semantics perspective, but simpler and more maintainable in the current architecture.

## Backend Implementation Approach

### Existing Strengths to Reuse

The codebase already has the right basic structure:

- Dedicated entity endpoints
- Dedicated entity CRUD service path
- Per-project locking around mutating entity operations
- Centralized YAML save pipeline
- Existing optimistic locking precedent for external values

This feature should reuse those pieces rather than inventing a new concurrency subsystem.

### Minimal Change Strategy

Add a dedicated service method for entity compare-and-swap, for example:

```python
update_entity_by_name_with_etag_check(project_name, entity_name, entity_data, expected_etag)
```

Within that method:

1. Acquire the existing per-project lock.
2. Load the latest project state for the transaction.
3. Extract the current entity.
4. Compute the current entity ETag.
5. Compare it with `expected_etag`.
6. If mismatched, raise a conflict error.
7. If matched, replace only that entity.
8. Save the project.
9. Return the updated entity and new ETag.

This keeps the change local to the entity update path.

### Important Read/Write Rule

The stale-check must happen against freshly loaded project data inside the write transaction, not against a previously cached in-memory object held by the caller.

That ensures the check reflects the latest persisted state.

## Persistence Requirements

### Current Situation

The YAML service already writes to a temp file and replaces the original file. That is a good foundation.

### Required Hardening

The save path should be tightened to a proper atomic write-by-rename sequence:

1. Serialize the YAML content.
2. Write to a temp file in the same directory.
3. Flush the temp file.
4. `fsync()` the temp file.
5. `os.replace()` the temp file over the target.
6. If practical, `fsync()` the parent directory.

This is not specific to entity-level locking, but it is the right time to harden the persistence guarantee because the compare-and-swap contract depends on reliable whole-file replacement.

## Frontend Impact

### Current Client Flow

The entity editor already fetches entity data and saves a full entity payload. That fits this feature well.

### Recommended Frontend Changes

1. Extend the entity response type to include `etag`.
2. Extend the update request type to include `expected_etag`.
3. Store the ETag with the loaded entity in the editor state.
4. Send the ETag back on save.
5. Handle `409 Conflict` by showing a clear message and offering reload.

### Suggested Loading Behavior

There are two acceptable approaches:

- Include `etag` in both entity list responses and single-entity responses, so the client cache already contains it.
- Or always perform a fresh entity fetch when opening edit mode.

The preferred approach is to include `etag` in entity responses generally, because it keeps the editor responsive and avoids adding another mandatory read round trip when the entity is already present in the store.

## Non-Goals

This feature does not attempt to solve:

- collaborative editing
- real-time synchronization
- field-level merges
- automatic conflict resolution
- multi-process distributed locking
- comment-preserving YAML diff merges

Conflict on entity save is sufficient.

## Edge Cases and Expected Behavior

### Different Entities Edited Concurrently

Expected result: both saves succeed.

Reason: each entity has its own fingerprint, and the stale-check is limited to the target entity.

### Same Entity Edited Concurrently

Expected result: first save succeeds, second save receives `409 Conflict`.

### Disk Change Outside the App

Expected result: if the entity content changed, the ETag mismatch detects it and the save is rejected.

### Formatting-Only YAML Changes

Expected result: no conflict if parsed entity content is unchanged.

Reason: fingerprints are based on logical entity data, not raw YAML text.

## Testing Requirements

Tests should cover at minimum:

### Backend

1. ETag stability
    - same entity data produces same ETag
    - changed entity data produces different ETag

2. Successful entity update
    - matching ETag succeeds
    - entity is replaced
    - response returns new ETag

3. Conflict handling
    - stale ETag returns `409 Conflict`
    - file remains unchanged

4. Serialized concurrent updates
    - overlapping in-process updates do not interleave incorrectly
    - one succeeds and one conflicts when editing the same entity

5. Different-entity concurrency
    - concurrent updates to different entities do not conflict purely because they share a project

6. Atomic save path
    - temp-file write and replace path is exercised

### Frontend

1. Editor stores received ETag.
2. Save request includes `expected_etag`.
3. `409 Conflict` is surfaced clearly to the user.

## Acceptance Criteria

The feature is complete when:

- entity responses include an entity-level ETag
- entity update requests include the expected ETag
- stale updates to the same entity return `409 Conflict`
- updates to different entities in the same project do not conflict solely because of project-level versioning
- entity update locking does not depend on project cache version values
- YAML persistence uses hardened atomic replace semantics
- backend and frontend tests cover the main success and conflict paths

## Recommended Delivery Order

1. Add entity ETag helper and backend tests for fingerprinting.
2. Extend entity response/request models.
3. Implement compare-and-swap entity update method under existing project lock.
4. Harden YAML atomic save implementation.
5. Wire frontend types and editor state to send `expected_etag`.
6. Add conflict UI handling.

## Final Recommendation

Proceed with entity-level optimistic locking as a targeted feature in the entity CRUD path.

Do not redesign the server-side project cache for this. The cache should remain a cache.

The simplest viable solution is:

- body-level `etag` / `expected_etag`
- entity-level fingerprint from canonical JSON
- compare-and-swap under the existing per-project lock
- reuse the current save pipeline with a hardened atomic write implementation

That gives the right granularity, keeps the implementation small, and aligns with how users actually edit projects today.

---

**Prompt for coding agent**

Implement safer concurrent entity updates for the ShapeShifter FastAPI backend.

### Goal

Replace the current coarse version-counter save behavior with **entity-level optimistic concurrency control** using **ETag-style fingerprints**, and ensure persistence uses **atomic write-by-rename**.

This does **not** need to become full collaborative editing. A simple and robust solution is preferred over a complex merge system.

### Context

The project configuration is stored as YAML. The editable business content is under the top-level `entities` mapping. Each entity is a child of `entities`, keyed by unique entity name/ID. Ignore top-level sections like `metadata` and `options` for this feature. The uploaded example shows the structure clearly. 

Users typically edit and save **one full entity at a time**.

Current update endpoint:

* `PUT /api/v1/projects/{project_name}/entities/{entity_name}`

The server receives the **entire entity**, not a partial patch.

### Desired behavior

Implement **entity-level optimistic locking** as follows:

1. When a client fetches an entity, the response should include an **ETag/fingerprint** representing the current canonical content of that entity.
2. When the client saves an entity, it must send back the ETag it originally fetched.
3. On save, the server must:

   * load the latest YAML from disk
   * locate `entities[entity_name]`
   * compute the current ETag for that entity
   * compare it with the client-supplied ETag
   * if they differ, reject the update with a conflict response
   * if they match, replace only that entity in memory
   * persist the YAML using **atomic write-by-rename**

This is intended to reduce false conflicts compared to a global document version counter.

### Important constraints

* Use **entity-level** optimistic concurrency, not document-level.
* Do **not** implement CRDT, OT, websocket collaboration, or full automatic merge.
* Do **not** hash raw YAML text.
* Order, formatting, and comments do **not** matter for concurrency purposes.
* It is acceptable if users occasionally lose edits in rare edge cases outside this design.
* There are no expected concurrent writers besides this FastAPI app, unless someone manually edits the file on disk.
* The app currently runs as a **single-worker uvicorn** FastAPI service.
* Reuse the existing YAML save pipeline if practical; the project already uses `ruamel.yaml` with custom formatting.

### ETag / fingerprint design

Use a deterministic fingerprint of the parsed entity data.

Recommended approach:

* Serialize the entity to **canonical JSON**
* Use sorted keys
* Use compact separators
* Hash that canonical JSON to produce a stable fingerprint

You may use SHA-256, or another stable deterministic hash if there is a strong reason, but SHA-256 is preferred.

Suggested logic:

```python
canonical = json.dumps(entity_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
etag = sha256(canonical.encode("utf-8")).hexdigest()
```

This fingerprint must be based on the parsed Python structure of a single entity only.

### Atomic persistence requirements

Implement safe file persistence using **write temp file in same directory + fsync + atomic rename**.

Expected pattern:

1. Serialize the full YAML document after replacing the target entity
2. Write to a temp file in the same directory as the target YAML
3. Flush and fsync the temp file
4. Replace the original file using `os.replace(...)`
5. Prefer also fsyncing the parent directory if practical

This must ensure the YAML file is never left partially written.

### Locking expectations

Because the app runs in a single process, use a simple in-process lock around the full read-modify-write sequence.

Recommended:

* `asyncio.Lock` for async FastAPI code

The lock should guard the entire transaction:

* load latest YAML
* compare ETag
* replace entity
* save atomically

This is to avoid interleaved writes from concurrent requests within the same process.

Do not introduce new server-side processes, daemons, or distributed locking.

### API changes

Update the entity API so that:

#### Read entity

The response includes the entity data plus its ETag, either:

* in the JSON body as a field such as `_etag`, or
* in an HTTP `ETag` header

Pick one approach and use it consistently. Body field is acceptable if simpler for the existing frontend/API.

#### Update entity

The update request must include the expected ETag, either:

* in request body as `_etag`, or
* in `If-Match` header

Again, choose one approach and implement consistently. Simplicity and maintainability are more important than strict HTTP purity.

If the supplied ETag does not match the current entity ETag, return:

* HTTP `409 Conflict`

The conflict response should include enough information for a future UI to handle it, ideally:

* error type/code
* current server ETag
* optionally the current server entity

Keep this simple but useful.

### Scope boundaries

Implement the backend feature end-to-end where needed, including:

* ETag generation
* entity read response changes
* update endpoint validation
* atomic file write
* locking around save path
* tests

Do not redesign unrelated parts of the app.

Do not implement fine-grained field merging unless it falls out trivially from the existing code. Conflict-on-entity is sufficient.

### Assumptions about YAML model

Assume:

* the YAML root is a mapping
* `entities` is a mapping of entity-name -> entity-definition
* `entity_name` in the route corresponds to a key under `entities`
* entity keys are unique and stable

The uploaded sample YAML should be used to understand and validate the structure. 

### Implementation notes

* Keep existing `ruamel.yaml` usage if possible
* It is acceptable if formatting changes slightly, since formatting/comments/order do not matter for this feature
* Prefer clear small helper functions:

  * `compute_entity_etag(entity: dict) -> str`
  * `load_project_yaml(path) -> YAML doc`
  * `atomic_write_yaml(path, content) -> None`
  * `update_entity_with_etag_check(...)`
* Make sure the ETag is computed from the entity as stored logically, not from route params or file metadata

### Tests to add

Add tests for at least:

1. **ETag stability**

   * same entity content -> same ETag
   * changed entity content -> different ETag

2. **Successful save**

   * matching ETag allows update
   * entity is replaced
   * file is persisted

3. **Conflict**

   * stale ETag returns `409 Conflict`
   * file remains unchanged

4. **Atomic write behavior**

   * save writes through temp file and replaces target
   * no partial file content on normal path

5. **Concurrent request safety**

   * simulate overlapping updates in-process
   * ensure write path is serialized and conflicts are handled predictably

### Deliverables

Please produce:

1. the code changes
2. tests
3. a brief implementation note explaining:

   * where ETags are added
   * how clients must send them back
   * how conflict responses look
   * how atomic write is implemented

---
