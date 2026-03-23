#   Path: Implementation Sketch

## Status

- Proposed technical sketch
- Scope: implementation approach for [COMMENT_PRESERVING_SAVE_PATH.md](COMMENT_PRESERVING_SAVE_PATH.md)
- Goal: describe a low-risk path for preserving YAML comments without introducing another long-lived cache layer

## Summary

This document turns the proposal into an implementation-oriented sketch.

It assumes the limited subtree-merge capability described in [BOUNDARY_BASED_PROJECT_PERSISTENCE.md](BOUNDARY_BASED_PROJECT_PERSISTENCE.md), rather than proposing a broader persistence redesign here.

The key recommendations are:

1. keep the current plain `Project` model flow for validation, services, and API work,
2. reload the latest YAML from disk at save time instead of keeping a separate comment-aware YAML cache in memory,
3. merge semantic changes from the in-memory project into the freshly loaded YAML tree using the stable boundaries defined in [BOUNDARY_BASED_PROJECT_PERSISTENCE.md](BOUNDARY_BASED_PROJECT_PERSISTENCE.md),
4. write the merged YAML back with the existing `ruamel.yaml`-based save path.

In short:

1. load plain data for normal app logic,
2. reload comment-aware YAML only when saving,
3. patch the YAML tree at stable subtree boundaries rather than rebuilding it from scratch,
4. save atomically.

## Relationship To Existing Code

The current load and save path already uses the right building block for comment preservation: `ruamel.yaml`.

Relevant files:

- [backend/app/services/yaml_service.py](../../backend/app/services/yaml_service.py)
- [backend/app/services/project_service.py](../../backend/app/services/project_service.py)
- [backend/app/mappers/project_mapper.py](../../backend/app/mappers/project_mapper.py)

Today the important behavior is:

- `YamlService.load()` parses with `ruamel.yaml`
- the parsed document is immediately converted to plain Python data
- `ProjectMapper.to_api_config()` and `ProjectMapper.to_core_dict()` operate on plain data and API models
- `ProjectService.save_project()` serializes a newly rebuilt config dict
- `YamlService.save()` writes that rebuilt structure

That means the current system preserves semantics, but not comment placement from the original file.

## Current Flow Vs Proposed Flow

| Step | Current Flow | Proposed Flow |
| --- | --- | --- |
| Load from disk | `YamlService.load()` parses YAML, then converts to plain Python objects | same for normal application logic |
| In-memory editing | services and frontend work on `Project` API model | same |
| Save preparation | `ProjectMapper.to_core_dict()` rebuilds the full sparse config dict that will be dumped as the new document | `ProjectMapper.to_core_dict()` provides semantic target data for the subtree being merged; it is merge input, not the final document |
| YAML source for save | rebuilt dict becomes the source of truth | latest YAML file is reloaded from disk as a comment-aware tree |
| Update behavior | whole YAML structure is effectively regenerated | stable sections such as `metadata`, `options`, or `entities[entity_name]` are patched into the reloaded YAML tree |
| Comment outcome | comments and nearby formatting are lost when regenerated | comments in unchanged areas are preserved; nearby comments around edited nodes are preserved when merge logic can keep them attached |
| Concurrency handling | current save path trusts in-memory project state | save path should detect if the file changed on disk since load and reject or defer conflicting saves |
| Persistence complexity | simpler serialization, no comment retention | slightly more complex save merge, but no extra long-lived cache |

## Why Reload On Save Instead Of Caching YAML In Memory

The safer default is to reload from disk at save time.

Reasons:

- avoids introducing another long-lived cache that can drift from the file on disk
- keeps comment preservation scoped to persistence rather than general application state
- supports mixed workflows better because hand-edited YAML changes are seen at save time
- reduces the risk of stale comment trees surviving across multiple edits or reloads

This does not remove the need for merge logic. It only avoids solving that problem with another persistent cache.

It also does not require a fully generic dot-path patch engine. The limited persistence boundaries needed here are proposed separately in [BOUNDARY_BASED_PROJECT_PERSISTENCE.md](BOUNDARY_BASED_PROJECT_PERSISTENCE.md).

## Design Goals

1. Preserve comments in unchanged sections during ordinary saves
2. Keep comments non-semantic and out of core/domain logic
3. Reuse the existing `Project` and `ProjectMapper` flow
4. Keep implementation concentrated in the YAML and project persistence layers
5. Prefer save-time reload and merge over a separate retained YAML document cache
6. Reuse explicit subtree merge boundaries instead of inventing an arbitrary document patch language here

## Non-Goals

1. Keep exact byte-for-byte formatting in all cases
2. Make every service understand `ruamel.yaml` wrapper types
3. Solve full multi-user merge conflicts in the first phase
4. Replace structured metadata fields with comments
5. Turn this sketch into a general persistence redesign proposal

## Proposed Execution Model

### Load Path

Keep the current load path for ordinary application behavior.

That means:

- load YAML from disk
- convert it to plain Python data
- build the API `Project`
- continue using the existing cache and service model for normal editing

No comment-aware structure needs to be retained in the active editing state for the first implementation.

### Save Path

Change only the save path.

At a high level:

1. convert the API `Project` to semantic config data with `ProjectMapper.to_core_dict()`
2. reload the latest YAML file from disk as a comment-aware `ruamel.yaml` document
3. compare or patch the relevant supported boundary using the semantic config data as the target state
4. preserve unchanged nodes and their comments
5. write the patched YAML document atomically

The save path should continue handling the task-list sidecar independently, just as it does today.

## Suggested Components

### 1. Extend `YamlService`

`YamlService` likely needs two explicit load modes:

- plain-data load for the current service layer
- comment-aware document load for save-time merge

And one additional save mode:

- save a comment-aware document tree without first flattening it into plain Python data

### 2. Add a YAML Merge Helper

Add a focused persistence helper, for example:

- `backend/app/services/project_yaml_merge.py`

Responsibility:

- take the current semantic project dict
- take the freshly reloaded YAML document tree
- update only the supported sections that need to change
- preserve comments on untouched nodes
- insert newly created nodes in stable key order

This helper should live beside persistence code, not in the mapper or domain layers.

The explicit persistence boundaries themselves are proposed in [BOUNDARY_BASED_PROJECT_PERSISTENCE.md](BOUNDARY_BASED_PROJECT_PERSISTENCE.md). This sketch only describes how the comment-preserving save feature would use them.

### 3. Update `ProjectService.save_project()`

`ProjectService.save_project()` becomes the orchestration point:

1. build semantic target config dict
2. reload the latest YAML document from disk
3. run conflict detection
4. merge semantic changes into the YAML document
5. save merged document
6. save task-list sidecar
7. verify result as today

## Conflict Detection

Reloading from disk at save time helps, but it does not by itself prevent overwriting someone else’s edits.

The first implementation should add optimistic conflict detection using one of:

- file modified time,
- file hash,
- explicit revision token stored in project metadata or server state.

If the file changed since the project was loaded, the safest first behavior is:

- reject save,
- report that the file changed on disk,
- ask the user to reload before saving again.

That is much safer than silently merging concurrent edits in phase one.

## Merge Strategy

The hard part of the feature is not YAML parsing. It is deciding how to patch the reloaded YAML tree.

The lowest-risk merge strategy is field-oriented, conservative, and boundary-based.

The important distinction is:

- targeted mutation APIs already exist today
- targeted persistence primitives do not

This sketch depends on adding those targeted persistence primitives at a few stable boundaries rather than trying to make every possible YAML path independently patchable.

Recommended order for this feature:

1. update top-level metadata and options keys in place
2. update existing entity subtrees in place when names already exist
3. append new entities or new nested blocks using canonical key order
4. remove deleted fields or entities explicitly
5. avoid rewriting whole sections unless necessary

This is intentionally narrower than a generic `read-yaml, update any dot path, save` design and intentionally narrower than the full persistence foundation described in [BOUNDARY_BASED_PROJECT_PERSISTENCE.md](BOUNDARY_BASED_PROJECT_PERSISTENCE.md).

Important cases to support early:

- metadata updates
- changing a scalar entity field
- changing `columns`, `keys`, or `depends_on`
- changing `foreign_keys`
- changing `extra_columns`
- changing `filters`, `append`, or `unnest`
- adding or removing entities

## Delivery Order

### Phase 1: Save-Time Reload Foundation

- add comment-aware load mode to `YamlService`
- add ability to save a comment-aware document
- add save-time reload in `ProjectService.save_project()`
- add save-time stale-file detection

### Phase 2: Conservative Merge Support

- merge top-level metadata and options
- merge existing entity subtrees in place
- preserve comments on unchanged sections
- verify atomic save behavior still works

### Phase 3: Structural Edits

- add support for entity insertion and deletion
- add support for nested list and object updates with comment preservation where practical
- expand regression coverage for append, filters, foreign keys, and `extra_columns`

## Testing Strategy

The primary tests should be save-roundtrip tests around:

- [backend/app/services/project_service.py](../../backend/app/services/project_service.py)
- [backend/app/services/yaml_service.py](../../backend/app/services/yaml_service.py)

Key scenarios:

- save after changing one metadata field while unrelated comments remain intact
- save after changing one entity field while comments in other entities remain intact
- save after editing `foreign_keys`, `extra_columns`, `filters`, `append`, and `unnest`
- save after adding and removing entities
- reject save when the on-disk file changed after load
- preserve task-list sidecar behavior

## Open Questions

1. How aggressive should the merge helper be before it falls back to rewriting a subtree?
2. Should entity renames be treated as rename operations or delete-plus-add in phase one?
3. How much formatting normalization is acceptable when a node is newly created?

## Recommendation

Implement the feature as a save-time reload and merge flow at stable subtree boundaries.

Do not introduce a second long-lived cache for comment-aware YAML documents unless real performance data later shows that reload-on-save is too expensive.

Do not turn this sketch into the place where boundary-based persistence is justified in general. Treat [BOUNDARY_BASED_PROJECT_PERSISTENCE.md](BOUNDARY_BASED_PROJECT_PERSISTENCE.md) as the foundation proposal, and treat this document as the feature-specific plan that uses that foundation for comment-preserving save behavior.