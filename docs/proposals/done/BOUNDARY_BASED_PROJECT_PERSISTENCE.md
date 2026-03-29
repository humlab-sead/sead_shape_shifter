# Proposal: Boundary-Based Project Persistence

## Status

- **Implemented** (March 2026)
- Scope: backend persistence layer, project save boundaries, future editing workflows
- Goal: introduce isolated persistence boundaries for project sections such as `metadata`, `options`, and `entities[entity_name]`

## Summary

Introduce boundary-based project persistence as a platform capability. Instead of treating every save as whole-document regeneration, the persistence layer should be able to reload the current YAML document and merge changes at a small number of stable project boundaries.

The initial boundaries should be:

- `metadata`
- `options`
- `entities[entity_name]`

This is worth doing because it gives the system a cleaner persistence model for several separate needs: comment-preserving save behavior, entity-level optimistic locking, and future collaborative or concurrent editing improvements. The recommendation is to introduce narrow subtree-merge support at those stable boundaries, not a generic update-any-dot-path patch engine.

## Problem

Today Shape Shifter has targeted mutation paths at the API level, but not targeted persistence primitives.

In practice that means:

- an entity editor can update one entity in memory
- metadata and options can be changed independently at the API level
- but persistence still falls back to rebuilding and saving the full project document

That current approach has three limitations:

- it makes comment-preserving save behavior harder because the whole YAML document is effectively regenerated
- it makes isolated compare-and-swap flows harder because persistence does not naturally align with the logical unit being edited
- it raises the blast radius of each save, which is not a good foundation for stronger collaborative behavior later

The core problem is not just YAML formatting. It is that the persistence layer does not yet expose stable write boundaries that match the logical units users actually edit.

## Scope

This proposal covers:

- isolated persistence boundaries for top-level project sections
- save-time reload and subtree merge as the persistence strategy
- backend-oriented persistence capabilities that other features can build on

## Non-Goals

This proposal does not:

- introduce real-time collaboration, CRDT, OT, or auto-merge
- define a generic arbitrary dot-path patch API for all YAML nodes
- require exact byte-for-byte YAML round-tripping
- replace feature-specific proposals such as comment-preserving save or entity optimistic locking

## Current Behavior

The current backend flow effectively does this:

1. load YAML
2. convert it to plain data and API models
3. mutate the relevant part in memory
4. rebuild a full sparse config dict
5. save the whole project again

That is simple and correct for semantics, but it does not give the persistence layer a notion of “replace just this stable project boundary while preserving the rest of the document as much as possible.”

## Proposed Design

Introduce boundary-based persistence helpers that operate on a reloaded YAML document and a semantic target state.

The first implementation should support three stable boundaries:

- `metadata`
- `options`
- `entities[entity_name]`

High-level behavior:

1. load the latest YAML document from disk in a comment-aware form
2. compute the semantic target state from the current API project or entity payload
3. merge only the target boundary into the reloaded document
4. write the merged document atomically

This is intentionally narrower than a general-purpose patch engine. The aim is to provide a small number of persistence operations that align with real editing workflows.

### Why These Boundaries

These boundaries are a good first cut because they are:

- already meaningful in the project model
- stable enough to support conservative merge logic
- directly useful for current editor flows
- sufficient to support other near-term features

### Why Not Generic Dot-Path Updates

A fully generic patch language sounds flexible, but it is a worse first move here.

- YAML comments attach to structure, not just logical paths
- list edits and insertion order quickly become policy questions
- many paths are implementation detail, not stable product boundaries
- a broad patch engine would increase scope without proving product value first

The persistence layer should first learn a few explicit boundaries well.

## Alternatives Considered

### Keep Whole-Project Persistence And Solve Each Feature Separately

This keeps the persistence layer simple, but it forces every feature to work around the same limitation independently.

- comment-preserving save has to fight full-document regeneration
- optimistic locking has to treat whole-project persistence as an unavoidable background behavior
- future collaborative improvements get no cleaner write boundary to build on

### Build A Fully Generic Patch Framework First

This likely overreaches.

- more abstraction than current use cases justify
- more edge cases around lists, comments, and ordering
- higher implementation cost before core user value is proven

## Risks And Tradeoffs

- adds persistence-layer complexity compared with whole-project regeneration
- requires careful merge logic to avoid accidental subtree rewrites
- may still leave some formatting normalization when nodes are newly created or heavily changed

Even with those tradeoffs, this is a better long-term foundation than making every higher-level feature invent its own partial-save strategy.

## Testing And Validation

Validation should focus on boundary-oriented behavior:

- update `metadata` and preserve unrelated document sections
- update `options` and preserve unrelated document sections
- update `entities[entity_name]` and preserve comments and structure elsewhere where practical
- add and remove entities through the entity boundary
- ensure saves remain atomic

## Acceptance Criteria

- the backend can reload the latest YAML and merge changes at `metadata`
- the backend can reload the latest YAML and merge changes at `options`
- the backend can reload the latest YAML and merge changes at `entities[entity_name]`
- the implementation does not depend on a generic dot-path patch engine
- the capability is usable as a foundation for comment-preserving save and entity-level optimistic locking

---

## Implementation Plan

### Context

`YamlService` already uses `ruamel.yaml` for all reads and writes. The comment
metadata is available at load time. The gap is that `YamlService.load()` converts
the parsed result to plain Python objects with `json.loads(json.dumps(data))` before
returning it. That conversion is correct at the normal I/O boundary (it prevents
ruamel wrapper types from leaking into service layer code), but it means comment
metadata is discarded before any boundary merge can use it.

Entity saves today pass through `EntityOperations`, which calls a full
`save_project(project)` callback. That rebuilds and serialises the entire project
document on every entity change.

The implementation inserts one new layer in `YamlService` and one new family of
methods in `ProjectService`, without changing the existing full-save path.

### Delivery Steps

#### Step 1 — `YamlService`: add `load_commented()` and `save_commented()`

Add a second load method that returns the raw `CommentedMap` from ruamel.yaml
without the POPO conversion:

```python
def load_commented(self, filename: str | Path) -> CommentedMap:
    """Load YAML preserving ruamel comment metadata. Do not call json.dumps."""
    path = Path(filename)
    with path.open("r", encoding="utf-8") as f:
        return self.yaml.load(f)
```

Add a matching save method that writes a `CommentedMap` without converting it:

```python
def save_commented(
    self,
    data: CommentedMap,
    filename: str | Path,
    create_backup: bool = True,
) -> Path:
    """Write a CommentedMap atomically. Applies flow-style and key ordering first."""
    path = Path(filename)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    if create_backup and path.exists():
        self.create_backup(path)
    self._apply_flow_style(data, self._flow_style_max_items)
    with temp_path.open("w", encoding="utf-8") as f:
        self.yaml.dump(data, f)
    temp_path.replace(path)
    return path
```

These two methods form the low-level primitive. They do not touch business logic.

#### Step 2 — `YamlService`: add `merge_boundary()`

```python
def merge_boundary(
    self,
    filename: str | Path,
    boundary: str | tuple[str, str],
    new_value: Any,
    create_backup: bool = True,
) -> Path:
    """
    Load the current YAML, replace one boundary, write back atomically.

    boundary may be:
      "metadata"                  → replaces doc["metadata"]
      "options"                   → replaces doc["options"]
      ("entities", entity_name)   → replaces doc["entities"][entity_name]
                                    (new_value=None deletes the entity)
    """
    doc: CommentedMap = self.load_commented(filename)

    if isinstance(boundary, str):
        doc[boundary] = new_value
    else:
        section_key, child_key = boundary
        if new_value is None:
            doc[section_key].pop(child_key, None)
        else:
            doc[section_key][child_key] = new_value

    return self.save_commented(doc, filename, create_backup=create_backup)
```

The method is intentionally minimal. `new_value` is a plain Python dict at this
stage; ruamel will serialize it in block style alongside any preserved comments
in adjacent nodes.

#### Step 3 — `ProjectService`: add boundary save methods

Three thin methods that resolve the file path, build the target value, and
delegate to `YamlService.merge_boundary()`:

```python
def save_metadata_boundary(self, project_name: str, metadata: ProjectMetadata) -> None:
    """Replace only the metadata section on disk."""
    file_path = self._resolve_file_path(project_name)
    metadata_dict = metadata.model_dump(exclude_none=True, mode="json")
    self.yaml_service.merge_boundary(file_path, "metadata", metadata_dict)
    self.state.invalidate(project_name)

def save_options_boundary(self, project_name: str, options: dict[str, Any]) -> None:
    """Replace only the options section on disk."""
    file_path = self._resolve_file_path(project_name)
    self.yaml_service.merge_boundary(file_path, "options", options)
    self.state.invalidate(project_name)

def save_entity_boundary(
    self,
    project_name: str,
    entity_name: str,
    entity_dict: dict[str, Any] | None,
) -> None:
    """Replace or delete one entity on disk without touching other entities."""
    file_path = self._resolve_file_path(project_name)
    self.yaml_service.merge_boundary(
        file_path, ("entities", entity_name), entity_dict
    )
    self.state.invalidate(project_name)
```

These methods acquire no project-level lock themselves. Callers that need locking
(entity update, entity delete) should wrap the call as they do today.

#### Step 4 — `EntityOperations`: wire boundary save as the preferred path

`EntityOperations` already receives a `save_project_callback`. Add an optional
second callback:

```python
def __init__(
    self,
    project_lock_getter,
    load_project_callback,
    save_project_callback,
    save_entity_boundary_callback=None,   # NEW: optional
    persistence_strategy_registry=None,
):
    ...
    self._save_entity_boundary = save_entity_boundary_callback
```

In `update_entity_by_name`, `delete_entity_by_name` (the load→mutate→save
methods), replace the trailing `self._save_project(project)` call:

```python
if self._save_entity_boundary:
    self._save_entity_boundary(project_name, entity_name, entity_dict_or_none)
else:
    self._save_project(project)   # fallback: full save
```

`add_entity_by_name` (new entity case) uses `save_entity_boundary` the same way.
The object-based methods (`add_entity`, `update_entity`) keep their current
signature; they are called by callers that manage the full project object and
already call `save_project` externally.

`ProjectService` injects both callbacks when constructing `EntityOperations`:

```python
entity_operations = EntityOperations(
    project_lock_getter=self._get_lock,
    load_project_callback=self.load_project,
    save_project_callback=self.save_project,
    save_entity_boundary_callback=self.save_entity_boundary,
)
```

#### Step 5 — Tests

`backend/tests/services/test_yaml_service_boundary.py`:
- `merge_boundary("metadata", ...)` replaces metadata, preserves entities section verbatim
- `merge_boundary("options", ...)` replaces options, preserves entities section verbatim
- `merge_boundary(("entities", "sample"), ...)` replaces that entity, preserves comments on adjacent entities
- `merge_boundary(("entities", "sample"), None)` removes the entity, preserves all others
- YAML comments present before the call are present after (spot-check on a fixture file with known comments)
- Atomic write: temp file is removed on success; original is not corrupted on failure

`backend/tests/services/test_project_service_boundary.py`:
- `save_entity_boundary` writes only the named entity; load and compare the rest
- `save_metadata_boundary` writes only metadata; check entities are unchanged
- `save_options_boundary` writes only options; check entities are unchanged

`backend/tests/services/project/test_entity_operations_boundary.py`:
- `update_entity_by_name` calls `save_entity_boundary_callback` when provided
- `update_entity_by_name` falls back to `save_project_callback` when boundary callback absent
- `delete_entity_by_name` calls `save_entity_boundary_callback(name, entity_name, None)`

### Implementation Notes

**ruamel type handling.** When `new_value` is a plain Python dict, ruamel will
serialize it correctly but without inline comments. That is the expected initial
behaviour. A follow-up can convert the incoming dict to a `CommentedMap` to
improve formatting consistency for newly-created sections.

**Key ordering.** The existing `_order_entity_keys` in `YamlService` operates on
a plain dict. For `save_commented`, apply the same ordering pass on the new value
before inserting it into the `CommentedMap`, so entity key order remains
consistent.

**Lock scope.** `merge_boundary` does a read-modify-write. Callers that need a
consistent view (optimistic locking, concurrent edits) should hold the project
lock for the full duration. This proposal does not change locking policy; it just
ensures the persistence primitive exists.

**Fallback safety.** Because `save_entity_boundary_callback` is optional in
`EntityOperations`, the full `save_project` path remains the fallback. Rolling
back to whole-project saves during debugging or testing is trivial: pass no
boundary callback.

## Final Recommendation

Promote boundary-based project persistence to a separate platform proposal.

Keep it narrow: explicit subtree merge at `metadata`, `options`, and `entities[entity_name]`.

Then let feature-specific work build on it:

- comment-preserving save uses it to preserve surrounding YAML structure and comments
- entity optimistic locking uses it as the natural persistence boundary for compare-and-swap
- future collaboration features can build on the same stable units of change