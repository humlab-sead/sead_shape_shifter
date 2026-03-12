Below is a prompt you can give your coding agent. I’ve filled in the assumptions from your description and the uploaded YAML structure, where `entities` is the relevant editable section and `metadata`/`options` can be ignored for this feature. 

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

A few details would still improve the prompt, but are not required before implementation:

* whether you want `_etag` in JSON or true HTTP `ETag` / `If-Match`
* what the current read-entity response shape looks like
* whether you want the `409` response to include the current server entity or only metadata

If you want, I can turn this into a more compact “Copilot-ready” version with stricter acceptance criteria and step-by-step tasks.
