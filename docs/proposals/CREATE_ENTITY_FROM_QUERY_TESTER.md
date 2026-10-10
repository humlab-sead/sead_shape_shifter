# Create Entity From Query Tester

## Status

- Proposed feature
- Scope: a Create Entity entry point in Query Tester, create-mode prefill for the entity dialog, and an authorization-aware project selector
- Goal: let a user turn a tested SQL query into a `sql` entity without re-entering the data source and query, and only into projects where the user may create entities
- Related issue: [#512](https://github.com/humlab-sead/sead_shape_shifter/issues/512)

## Summary

Add a **Create Entity** action to Query Tester. It opens the existing Create Entity dialog with:

1. entity type set to `sql`
2. data source set to the data source currently selected in Query Tester
3. query set to the SQL currently in the Query Tester editor

Query Tester is a global route with no project context, and entity creation requires `project:edit` on a project. The flow therefore needs a project selector, and that selector must list only projects where the caller may create entities.

Recommended mechanism: add an optional `required_action` filter to `GET /api/v1/projects` so the server returns only projects where the caller holds the requested action. The selector uses `required_action=edit`. This keeps the authorization decision server-owned and reuses the route's existing "narrow the response, do not deny" behavior.

## Problem

A user writes and validates SQL in Query Tester, then must navigate to a project and re-enter the data source and SQL by hand in the Create Entity dialog. Nothing carries the tested query across.

Two constraints make this more than a UI shortcut:

- **Query Tester has no project context.** Its route is `/query-tester` with no project parameter, and `EntityFormDialog` requires a `projectName`. The create flow has to introduce a project choice where none exists today.
- **The project list cannot answer "where may I create entities".** `GET /api/v1/projects` filters by `read` only. Entity creation requires `project:edit`. A project the caller can read but not edit would appear selectable and then fail with `403 Insufficient authorization`.

The authorization domains also differ. Query Tester's SQL routes require `shared_data_source:read` on a shared data source; creating an entity requires `project:edit` on a project. A user can legitimately be able to test a query and be unable to create an entity in any project, so the selector must handle an empty result.

## Scope

- A Create Entity action in Query Tester, disabled until a data source is selected and the SQL is non-empty.
- Exposing the current data source and SQL from the query editor to the Query Tester view.
- A create-mode prefill input on `EntityFormDialog`.
- An authorization-aware project selector backed by a server-filtered project list.
- Handling the difference between the Query Tester data source and the entity `data_source` key.

## Non-Goals

- No new entity authoring capability beyond prefilling existing fields.
- No general frontend permission or capability framework. This adds only what the selector needs.
- No change to who may create entities. `project:edit` remains the rule.
- No project-scoped routing of Query Tester and no change to how queries execute.
- No automatic attachment of a shared data source to a project.

## Current Behavior

| Concern | Location | Current state |
|---|---|---|
| Query Tester route | `frontend/src/views/QueryTesterView.vue` | Route `/query-tester`, no project context. Reads `route.query.query` and `route.query.dataSource` for initial values only. |
| Live SQL and source | `frontend/src/components/query/QueryEditor.vue` | `query` and `selectedDataSource` are local refs. The component emits only `result` and `error` and has no `defineExpose`, so the parent cannot read them. |
| Create Entity dialog | `frontend/src/components/entities/EntityFormDialog.vue` | Props are `{ modelValue, projectName, entity, mode, initialTab }`. Create mode has no prefill input and defaults `type` to `entity`. |
| Project list | `backend/app/api/v1/endpoints/projects.py`, `backend/app/services/project_service.py` | `GET /api/v1/projects` calls `list_authorized_projects`, which filters by `Action.READ`. `ProjectMetadata` carries no permission field. |
| Entity creation | `backend/app/api/v1/endpoints/entities.py` | `POST /projects/{project_name}/entities` requires `project:edit`. |
| Query Tester SQL | `backend/app/api/v1/endpoints/query.py` | Query execute and validate require `shared_data_source:read`. |
| Data source scope | `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/stores/data-source.ts` | The dialog's `availableDataSources` comes from `project.options.data_sources`. Query Tester's sources come from the global `/api/v1/data-sources` list. |

## Proposed Design

### Query Tester action and state exposure

`QueryEditor` exposes its current `query` and `selectedDataSource` to `QueryTesterView`, either through `defineExpose` or two additional emits. `QueryTesterView` renders a **Create Entity** button, disabled unless a data source is selected and the SQL is non-empty.

### Create Entity dialog prefill

Add an optional `createDefaults` prop to `EntityFormDialog`:

```ts
createDefaults?: { name?: string; type?: string; data_source?: string; query?: string }
```

Rules:

- Applied once, when the dialog opens with `mode === 'create'`.
- Never applied in `mode === 'edit'`, and never re-applied after the user edits a field.
- Field values the user changes are not overwritten.
- Existing create-mode defaults fill any field left unset.

Prefilling the SQL keeps the existing column-detection path working, so the column list still populates from the query.

### Authorization-aware project selector

Backend:

- Add an optional `required_action` query parameter to `GET /api/v1/projects`.
- When present and valid, return only projects where `authorization_service.is_allowed(principal, Action(required_action), resource)` is true.
- Reject an unknown action value rather than falling back to the default.
- Without the parameter, behavior is unchanged and still filters by `read`.

Frontend:

- Add a `requiredAction` option to the projects API `list` call and a store action that fetches editable projects.
- The selector's options come only from that filtered call, so a read-only project cannot be chosen.
- Preselect the active project when it appears in the filtered list; otherwise leave the selector empty and require an explicit choice.
- When the list is empty, show an explanation (the caller may not create entities in any project) and keep Create disabled.

### Data source scope handling

The Query Tester data source is a shared data source name; the entity `data_source` must be a key declared in `project.options.data_sources`. When the target project declares the same name, preselect it. When it does not, leave `data_source` unset and show an inline notice. The flow always warns in this case; it does not attach the shared data source to the project. Do not write an undeclared source into the project.

Name equality is sufficient to identify the same database. Confirmed: both paths resolve a name to the same global file. Query Tester resolves the shared-data-source locator (the file stem) and loads `<global_data_source_dir>/<name>.yml`. A project that declares the source by `@include:` or by bare name resolves through the same loader and reads the same file. A name therefore maps to exactly one global data source file, so the database the query was tested against is the database the entity will read.

One implementation note: a project may declare a data source as an inline dict instead of a file reference under `project.options.data_sources`. An inline dict is used as written and is the only case where a project-local definition can differ from the global file of the same name. For an inline declaration, compare the resolved configuration and warn on a mismatch rather than assuming equality.

## Alternatives Considered

- **Reuse `CreateEntityFromTableDialog`.** Rejected. It generates an entity from a table and has no field for an arbitrary SQL query.
- **Client-side permission inference.** Rejected. Showing every readable project and letting `403` handle the rest is not authorization-aware, offers options that cannot succeed, and makes the server's rule implicit in the UI.
- **Add `permitted_actions` to `ProjectMetadata`.** Deferred. It would also support showing read-only projects as disabled with a reason, but it changes a shared response model and would be empty on other project responses. Revisit when a second consumer needs per-project capabilities.
- **A dedicated capability endpoint.** Deferred. More surface area than one consumer justifies.
- **Make Query Tester project-scoped.** Deferred. A larger navigation and state change; query testing is not inherently project-bound.

## Risks And Tradeoffs

- The `required_action` parameter widens the projects route contract. Validate the action and deny unknown values so a typo cannot silently broaden or narrow results.
- The two authorization domains can produce a confusing state: a user can test a query and still have no project to create it in. The empty-list message must be clear.
- The data source key mismatch is the most likely user-visible friction, and the inline notice is the minimum acceptable handling.
- `EntityFormDialog` has complex edit-mode hydration and watch logic. The prefill must be confined to create mode to avoid disturbing it.
- Prefill introduces a second way to open the dialog, so its create-mode entry path needs coverage in the existing dialog tests.

## Testing And Validation

Backend:

- `GET /projects?required_action=edit` returns only projects the caller may edit.
- An unknown `required_action` value is rejected.
- `GET /projects` without the parameter is unchanged.
- Use the existing authorization test fixtures (`authorized_client`, `backend/tests/api/v1/test_entities.py`) so a principal with mixed project roles is covered.

Frontend:

- `QueryEditor` exposes the current source and SQL.
- The Query Tester action is disabled without a source or with empty SQL.
- `EntityFormDialog` applies `createDefaults` in create mode and does not affect edit mode.
- The selector excludes projects without edit permission.

Manual:

- A user with edit on one project and read-only on another sees only the editable project.
- A user with no editable project sees the empty-state message.

## Acceptance Criteria

- `P-AC-1`: Query Tester shows a Create Entity action, disabled unless a data source is selected and the SQL is non-empty.
- `P-AC-2`: Activating it opens the Create Entity dialog in create mode with type `sql`, the current SQL, and the current data source when the target project declares it.
- `P-AC-3`: The project selector lists only projects where the caller may create entities, determined by the server.
- `P-AC-4`: A project the caller can read but not edit cannot be selected through this flow.
- `P-AC-5`: When the caller may create entities in no project, the flow explains why and prevents submission.
- `P-AC-6`: Prefill does not modify the edit-mode dialog or an existing entity.
- `P-AC-7`: `GET /api/v1/projects` without `required_action` behaves as it does today.

## Planning Handoff

- Confirmed decision: authorization for the selector is computed server-side. The client does not infer permissions.
- Confirmed decision: the selector is backed by a filtered project list, not by a client-side capability model.
- Confirmed decision: the flow warns when the target project does not declare the tested data source. It does not attach a shared data source to the project.
- Confirmed decision: preselect the active project when it is in the authorized list; otherwise require an explicit choice.
- Confirmed decision: a data source name identifies the same database in Query Tester and in a project, because both resolve the name to the same global data source file. Matching by name is sufficient; no configuration comparison is required for file-backed declarations.
- Preserve: the default read-filtering of `GET /api/v1/projects`; `project:edit` as the entity creation rule; the existing edit-mode hydration path in `EntityFormDialog`.
- Preserve: `ProjectMetadata`'s current shape unless the deferred alternative is chosen later.
- Expected validation outcomes: the backend filter tests pass; the frontend exposure, prefill, and selector tests pass; manual checks confirm the empty-project state and the same-name data source preselect.

## Recommended Delivery Order

1. Backend `required_action` filter on `GET /api/v1/projects`, with tests.
2. Frontend projects API and store method for editable projects.
3. `QueryEditor` source and SQL exposure.
4. `EntityFormDialog` create-mode prefill, with tests.
5. Query Tester Create Entity action and project selector.
6. Data source scope notice and empty-state handling.

## Final Recommendation

Proceed. This is a small frontend change plus one small, additive backend filter parameter. The only part that needs a real decision is the authorization-aware project selector, and the recommended approach keeps that decision on the server.
