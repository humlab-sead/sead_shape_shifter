# Project Grouping and Folder Filter Plan

## Summary

The projects page already receives project names derived from their relative filesystem path under the projects root. Nested folders are converted from `/` to `:` at the API boundary.

Examples:

- `arbodat/site-a/shapeshifter.yml` → `arbodat:site-a`
- `sead/demo/shapeshifter.yml` → `sead:demo`
- `standalone/shapeshifter.yml` → `standalone`

This means grouping and filtering by top-level folder can be added without changing how projects are stored on disk.

---

## Current Backend Behavior

Relevant code:

- `backend/app/services/project_service.py`
- `backend/app/mappers/project_name_mapper.py`

The backend currently:

1. Recursively discovers `shapeshifter.yml` files under the configured projects directory.
2. Derives the project name from the relative parent path.
3. Converts `/` to `:` for API-safe names.
4. Returns `ProjectMetadata`, including `name`, `file_path`, `entity_count`, and timestamps.

This already provides enough information for a frontend-only folder filter.

---

## Recommended First Step

Implement **option 2** from the design discussion:

- Keep the current flat, compact project list.
- Add a `Folder` filter dropdown to the toolbar.
- Optionally show a small folder chip in each project row.

This gives the benefit of folder-aware browsing without introducing a more complex grouped layout immediately.

Why this is the best first step:

- Minimal code change
- No backend API changes required
- Keeps the list dense and easy to scan
- Easy to extend later into grouped/collapsible sections

---

## Proposed UX

Toolbar:

```text
[ Search projects ] [ Sort by ] [ Folder: All / arbodat / sead / ... ] [ New Project ]
```

List rows:

```text
arbodat:survey-2024   [arbodat] [12 entities] Modified 2d ago   [edit] [copy] [validate] [delete]
arbodat:test-import   [arbodat] [4 entities]  Modified 5d ago   [edit] [copy] [validate] [delete]
sead:demo-project     [sead]    [8 entities]  Modified 1h ago   [edit] [copy] [validate] [delete]
```

Behavior:

- `All` shows every project.
- Selecting `arbodat` shows only projects whose top-level folder is `arbodat`.
- Projects without a `:` separator are treated as `ungrouped` or `root`.

---

## Frontend Implementation Shape

Primary file:

- `frontend/src/views/ProjectsView.vue`

Suggested additions:

### 1. Local state

Add:

```ts
const folderFilter = ref('all')
```

### 2. Helper function

Derive top-level folder from the current API name:

```ts
function getProjectFolder(name: string): string {
  return name.includes(':') ? name.split(':')[0] : 'ungrouped'
}
```

### 3. Folder filter options

Build options from the loaded projects:

```ts
const folderOptions = computed(() => {
  const folders = new Set(projects.value.map((project) => getProjectFolder(project.name)))

  return [
    { title: 'All folders', value: 'all' },
    ...Array.from(folders).sort().map((folder) => ({ title: folder, value: folder })),
  ]
})
```

### 4. Filter pipeline

Extend the existing `filteredProjects` computed:

1. apply search query
2. apply folder filter
3. apply sort

Example folder filter stage:

```ts
if (folderFilter.value !== 'all') {
  filtered = filtered.filter((project) => getProjectFolder(project.name) === folderFilter.value)
}
```

### 5. Row-level chip

Optional but recommended:

- Show a small chip with the derived folder name in each list row.
- This makes the filter model obvious to users.

---

## Alternative Follow-Up

If the folder filter works well, a later enhancement could add actual grouped display:

- section headers per folder
- collapsible groups
- per-group counts

That should be treated as a separate UX enhancement after the filter is proven useful.

---

## Future Backend Enhancement

If we want to remove the frontend's dependency on parsing `name`, add an explicit field to `ProjectMetadata`, for example:

- `group`
- `top_level_folder`
- `relative_path`

That is cleaner long-term, but not necessary for the first implementation.

---

## Open Questions

1. Should projects without `:` be shown as `ungrouped`, `root`, or hidden from the folder filter?
2. Should the folder chip be visible by default, or only when a folder filter is active?
3. Should the selected folder be persisted in route query params or local storage?
4. If grouped sections are added later, should sort apply globally or within each folder group?

---

## Resume Point

If this work is resumed later, start in `frontend/src/views/ProjectsView.vue` and implement:

1. `folderFilter` state
2. `getProjectFolder()` helper
3. `folderOptions` computed
4. folder-filter step in `filteredProjects`
5. optional folder chip in each list row

No backend changes are required for the first pass.