# Task Management System Review and Overhaul Proposal

**Date:** March 7, 2026  
**Status:** Review + Redesign Proposal (based on implemented code)  
**Scope:** Task model, storage, API, graph UX, and status coloring

---

## Executive Summary

Task management is already implemented and available in both backend and frontend, but it has grown in a partially inconsistent way.

The current feature is usable for simple progress tracking:
1. Tasks are stored in project YAML under top-level `task_list`.
2. Status is updated through graph node right-click actions.
3. API endpoints exist and are in production code.

The main opportunity now is not "adding tasks" but **consolidating and simplifying what already exists**.

This update proposes:
1. A clearer status model with primary status + secondary flags.
2. Moving task persistence from `shapeshifter.yml` into a dedicated sidecar file.
3. Completing graph integration, including explicit "Color By" modes (`type` vs `task`).

---

## Current State (Verified in Code)

### Backend and API

Implemented endpoints in `backend/app/api/v1/endpoints/tasks.py`:
1. `GET /projects/{name}/tasks`
2. `POST /projects/{name}/tasks/initialize`
3. `POST /projects/{name}/tasks/{entity_name}/complete`
4. `POST /projects/{name}/tasks/{entity_name}/ignore`
5. `DELETE /projects/{name}/tasks/{entity_name}`

Implemented service in `backend/app/services/task_service.py`:
1. Merges stored task list state with derived validation and dependency state.
2. Includes required-but-not-yet-created entities (`set(project.table_names) | set(project.task_list.required_entities)`).
3. Enforces validation + preview checks before marking `done`.

Implemented task model in `src/model.py` (`TaskList`):
1. Stored keys are `required_entities`, `completed`, `ignored`.
2. `reset_status()` removes from both `completed` and `ignored`.
3. Empty task list is supported.

### Frontend

Implemented UI in `frontend/src/components/dependencies/GraphNodeContextMenu.vue`:
1. `Mark as Done`
2. `Mark as Ignored`
3. `Reset Status`

Implemented client/store wiring:
1. `frontend/src/composables/useTaskStatus.ts`
2. `frontend/src/stores/taskStatus.ts`
3. Integrated in `frontend/src/views/ProjectDetailView.vue`

Task filter dropdown exists in `frontend/src/components/dependencies/TaskFilterDropdown.vue` with options:
1. `all`
2. `todo`
3. `done`
4. `ignored`
5. `blocked`
6. `critical`

### Changelog and Git History

Changelog and git history show the staged rollout:
1. `a371814` task management + completion stats + filters.
2. `7e64c67` and `edbbf3d` task initialization endpoint/strategies.
3. `1c3ec0e` graph display/layout + task filter dropdown.
4. `426c302` task actions in node context menu.

---

## Current Gaps and Inconsistencies

### 1. Styling Gap: Task classes are applied but not styled

`ProjectDetailView.vue` applies Cytoscape classes:
1. `task-done`
2. `task-ignored`
3. `task-blocked`
4. `task-critical`
5. `task-ready`

But `frontend/src/config/cytoscapeStyles.ts` has no selectors for these classes. Result: status-color behavior is partial/non-visible.

### 2. Filter Gap: UI offers filters that logic does not apply

The dropdown includes `blocked` and `critical`, but `applyTaskFilter()` in `ProjectDetailView.vue` currently handles only:
1. `all`
2. `todo`
3. `done`
4. `ignored`

### 3. Stats Contract Drift

Backend completion stats currently emit keys like `done`, `required_done`, `required_total`. Some frontend components expect `completed` and `completion_percentage`.

### 4. Storage Location

Task state is embedded in `shapeshifter.yml`. This works, but it bloats the project file and mixes workflow state with transformation design.

---

## User Use Cases to Support

1. Define "definition of done" via `required_entities`, including entities not yet created.
2. Quickly move entities between statuses from graph right-click.
3. See clear project progress at graph level.
4. Focus on what is blocked and what is ready next.
5. Keep task data lightweight and separate from entity config.
6. Toggle graph coloring by semantics:
   `Color by Type` for structural understanding, `Color by Task` for progress understanding.

---

## Proposed Status Model (Recommended)

### Primary Status (stored)

Use four explicit, user-controlled statuses:
1. `todo`
2. `ongoing`
3. `done`
4. `ignored`

### Secondary Flags / Properties

Use independent properties, not mutually exclusive statuses:
1. `required: bool` (from required list)
2. `flagged: bool` (manual attention marker)

### Derived Indicators (not stored)

Compute at runtime:
1. `blocked` (dependency or validation blockers)
2. `critical` (required + blocked/invalid)
3. `ready` (all prerequisites satisfied)

### Why this model

1. Keeps status simple and user-editable.
2. Supports your requested `ongoing` without conflating it with blockers.
3. Supports your requested `flagged` as orthogonal metadata that can coexist with any status.
4. Avoids stale derived states in persisted data.

---

## Storage Overhaul: Sidecar Task File

### Recommendation

Store task data in a separate file next to `shapeshifter.yml`.

Suggested filename:
`shapeshifter.tasks.yml`

Suggested schema:

```yaml
version: 1
required_entities:
  - location
  - site
  - sample

entities:
  location:
    status: done
    flagged: false
  site:
    status: ongoing
    flagged: true
  sample:
    status: todo
    flagged: false
```

### Compatibility plan

1. Read order:
   `shapeshifter.tasks.yml` first, fallback to legacy `task_list` inside `shapeshifter.yml`.
2. Write target:
   new sidecar file only.
3. Migration command/API:
   one-time export from legacy in-file `task_list` to sidecar.
4. Keep backward compatibility for existing projects during transition.

---

## API Evolution Proposal

Current API is already available and should remain stable while introducing v2 semantics.

### Keep existing endpoints

1. `GET /projects/{name}/tasks`
2. `POST /projects/{name}/tasks/{entity}/complete`
3. `POST /projects/{name}/tasks/{entity}/ignore`
4. `DELETE /projects/{name}/tasks/{entity}`
5. `POST /projects/{name}/tasks/initialize`

### Add v2-compatible operations

1. `PATCH /projects/{name}/tasks/{entity}`
   body: `{ "status": "ongoing|todo|done|ignored", "flagged": true|false }`
2. `PUT /projects/{name}/tasks/required`
   body: list of required entities, including not-yet-created entities.
3. Optional `POST /projects/{name}/tasks/bulk` for batch status updates.

---

## Graph UX and Node Coloring

### Display Menu Additions

Add in `GraphDisplayOptionsDropdown.vue`:
1. `Color By: Type | Task`
2. Keep both options available at all times.

### Color modes

1. `By Type` (current behavior): source/entity type semantics.
2. `By Task` (new): progress/status semantics.

Suggested `By Task` colors:
1. `done`: green
2. `ongoing`: blue
3. `todo`: gray
4. `ignored`: muted gray
5. `flagged`: amber outline/accent (works with any primary status)
6. `blocked/critical`: red border or glow (derived)

### Required implementation fixes

1. Add Cytoscape style selectors for `task-*` classes in `frontend/src/config/cytoscapeStyles.ts`.
2. Make `applyTaskFilter()` implement `blocked` and `critical` cases to match UI options.
3. Align completion stats contract (`done` vs `completed`, percentage field) across backend and frontend.

---

## Phased Overhaul Plan

### Phase 1: Stabilize Existing Feature (1-2 days)

1. Fix task class styling in Cytoscape styles.
2. Fix `blocked`/`critical` filtering behavior.
3. Align completion stats keys and types across API and frontend.
4. Add tests for filter behavior and node class rendering.

### Phase 2: Introduce New Status Semantics (2 days)

1. Add `ongoing` status and `flagged` flag.
2. Extend backend model/service and frontend composable/store.
3. Add context menu actions for `Mark Ongoing` and `Toggle Flag`.

### Phase 3: Externalize Storage (2 days)

1. Implement `shapeshifter.tasks.yml` read/write.
2. Add migration path from legacy in-project `task_list`.
3. Keep compatibility with existing projects.

### Phase 4: Color Mode Toggle (1 day)

1. Add `Color By` option in Display menu.
2. Implement class switching and style variants.
3. Validate accessibility and contrast in light/dark themes.

Total estimate: ~6-7 days including migration and compatibility.

---

## Proposed "Definition of Done" Logic

Project done when all `required_entities` are either:
1. `done`, or
2. `ignored`

This must continue supporting required entities that are not yet created at configuration time.

---

## Success Criteria

1. Required entities not yet created are first-class in task tracking.
2. Status updates via graph context menu are fast and reliable.
3. "Color By Task" gives immediate progress clarity without losing "Color By Type".
4. Task storage no longer bloats `shapeshifter.yml`.
5. Existing projects load without manual migration breaks.
6. Filter dropdown behavior fully matches implemented filtering logic.

---

## Final Recommendation

Proceed with an incremental overhaul, not a full rewrite.

Start by fixing current integration gaps, then adopt:
1. Primary statuses: `todo`, `ongoing`, `done`, `ignored`
2. Secondary flag: `flagged`
3. Derived indicators: `blocked`, `critical`, `ready`
4. Sidecar persistence: `shapeshifter.tasks.yml`

This keeps the system simple, robust, and graph-friendly while directly addressing current workflow needs.

---

## Phase 1 Execution Checklist (Issue-Ready)

Use this checklist as the implementation issue for "stabilize existing feature".

### Scope

1. Make task status coloring visible in graph.
2. Make task filters behave as advertised.
3. Align backend/frontend completion stats contract.
4. Add regression tests for the above.

### Backend Tasks

1. `backend/app/models/task.py`
   Add explicit completion stats model (or typed dict equivalent) and align field naming with frontend usage.
2. `backend/app/services/task_service.py`
   Update `_calculate_stats()` to emit a stable contract, including:
   `total`, `todo`, `done`, `ignored`, `required_total`, `required_done`, `required_todo`, and `completion_percentage`.
3. `backend/app/api/v1/endpoints/tasks.py`
   Ensure endpoint docstrings/examples match the actual response contract.

### Frontend Tasks

1. `frontend/src/config/cytoscapeStyles.ts`
   Add node style selectors for:
   `node.task-done`, `node.task-ignored`, `node.task-blocked`, `node.task-critical`, `node.task-ready`.
2. `frontend/src/views/ProjectDetailView.vue`
   Update `applyTaskFilter()` to support:
   `blocked` (has `blocked_by`) and `critical` (`priority === 'critical'`).
3. `frontend/src/composables/useTaskStatus.ts`
   Align `ProjectTaskStatus.completion_stats` typing with backend response.
4. `frontend/src/stores/taskStatus.ts`
   Verify computed fields (`completionPercentage`, `completionSummary`) use the aligned stats fields.
5. `frontend/src/components/dependencies/TaskFilterDropdown.vue`
   Verify counts map to aligned stats and derived filters without duplicate semantics.
6. `frontend/src/components/dependencies/TaskCompletionStats.vue`
   Ensure progress and percentage rendering match backend values and do not rely on mismatched field names.

### Test Tasks

1. `backend/tests/api/v1/test_tasks.py`
   Add/adjust assertions for `completion_percentage` and stable completion stats keys.
2. `backend/tests/services/test_task_service.py`
   Add tests for stats calculation edge cases:
   empty task list, required-but-missing entities, ignored-only entities.
3. `frontend/src/components/dependencies/__tests__/`
   Add or update tests for task filtering logic (`all`, `todo`, `done`, `ignored`, `blocked`, `critical`).
4. `frontend/src/config` or graph integration tests
   Add regression test to verify task classes map to actual style selectors.

### Acceptance Criteria

1. Right-click task updates visibly change node appearance in graph.
2. Selecting `Blocked` filter hides non-blocked nodes.
3. Selecting `Critical` filter hides non-critical nodes.
4. Completion card and filter counts use the same stats contract.
5. API docs/examples match real payloads.

### Suggested Validation Commands

1. `uv run pytest backend/tests/api/v1/test_tasks.py -v`
2. `uv run pytest backend/tests/services/test_task_service.py -v`
3. `cd frontend && pnpm test:run`
4. `cd frontend && pnpm exec vue-tsc --noEmit`

### Out of Scope for Phase 1

1. Adding `ongoing` status.
2. Adding `flagged` property.
3. External task sidecar file (`shapeshifter.tasks.yml`).
4. Display menu `Color By: Type | Task` toggle.

These are handled in Phases 2-4 above.
