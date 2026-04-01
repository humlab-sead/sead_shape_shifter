# Raw Source Data Explorer Proposal

## Status

- Proposed product and technical direction
- Scope: frontend and backend enhancements for investigating raw source data before mapping and transformation
- Goal: improve the Schema Explorer from a basic preview tool into a more powerful raw-data investigation workflow

## Summary

The current Schema Explorer is useful for confirming that a data source is reachable, listing tables, checking schema details, and previewing a small slice of rows.

That is enough for basic validation, but it is too limited for deeper source-data investigation.

The main current constraints are:

1. the preview pane uses a simple table renderer,
2. the page size is fixed to small preview limits,
3. the backend preview API is capped at 100 rows per request,
4. sorting, filtering, selection, and export workflows are not designed for investigative use,
5. the current experience is optimized for a quick peek, not for exploring messy source data.

This proposal recommends evolving Schema Explorer into a raw source data explorer with a phased implementation path.

The first phase can improve the frontend substantially without changing the backend contract. Later phases can add more powerful querying, larger result windows, export, and server-driven exploration features.

## Why This Matters

Users working with source systems often need to answer questions such as:

1. what values actually exist in a column,
2. how common are nulls, blanks, duplicates, or malformed values,
3. which rows would be affected by a given mapping or filter rule,
4. whether a foreign key join assumption is valid before configuration is written,
5. whether the source data contains anomalies that should influence entity design.

The current preview tool is not built for this class of work.

## Current State

### Existing strengths

The current Schema Explorer already provides:

1. data source selection,
2. schema-aware table browsing,
3. table metadata and column details,
4. row preview with offset and limit,
5. cache invalidation and refresh behavior.

Relevant files:

1. [frontend/src/views/SchemaExplorerView.vue](frontend/src/views/SchemaExplorerView.vue)
2. [frontend/src/components/SchemaTreeView.vue](frontend/src/components/SchemaTreeView.vue)
3. [frontend/src/components/TableDetailsPanel.vue](frontend/src/components/TableDetailsPanel.vue)
4. [frontend/src/components/DataPreviewTable.vue](frontend/src/components/DataPreviewTable.vue)
5. [frontend/src/stores/data-source.ts](frontend/src/stores/data-source.ts)
6. [frontend/src/api/schema.ts](frontend/src/api/schema.ts)
7. [backend/app/api/v1/endpoints/schema.py](backend/app/api/v1/endpoints/schema.py)
8. [backend/app/services/schema_service.py](backend/app/services/schema_service.py)

### Existing limitations

The main practical limitations are:

1. `DataPreviewTable` uses a plain Vuetify table and is not optimized for column-heavy or value-dense exploration.
2. The frontend only offers `10`, `25`, `50`, and `100` rows per page.
3. The preview endpoint enforces `limit <= 100`.
4. Any sorting or filtering is effectively manual because the current preview is a passive rendering surface.
5. Users cannot perform a meaningful "select all" across an entire dataset because only one small page is loaded.
6. There is no dedicated export flow for the currently investigated raw rows.
7. There is no path to inspect value distributions, distinct values, or column-level quality signals.

## Recommendation

Treat this as a broader raw-data exploration feature, not just an AG Grid swap.

AG Grid is a good rendering foundation, but the real user value comes from pairing a stronger grid with better data-retrieval and inspection capabilities.

## Proposed Direction

### Phase 1: Stronger client-side preview experience

Replace the current preview renderer in [frontend/src/components/DataPreviewTable.vue](frontend/src/components/DataPreviewTable.vue) with AG Grid while keeping the current preview API.

This phase should include:

1. AG Grid rendering for the loaded result set,
2. resizable and sortable columns,
3. client-side filtering for the loaded page,
4. row selection for the loaded page,
5. better handling of wide tables and long cell values,
6. clearer loaded-row messaging such as "50 of 12,431 rows loaded".

This phase does not require backend changes.

### Phase 2: Larger preview windows and explicit investigation mode

Add an explicit investigation mode that allows larger preview fetches than the current 100-row cap.

This phase should include:

1. higher allowed fetch limits such as `250`, `500`, and `1000`,
2. frontend controls that clearly separate "preview" from "investigate",
3. warnings for potentially expensive operations,
4. better empty-state and loading-state messaging for large fetches,
5. optional CSV export for the currently loaded rows.

This phase requires backend API and service changes.

### Phase 3: Server-driven exploration features

Add features that move beyond a single result page and support real data investigation.

Candidate capabilities:

1. server-side sorting,
2. server-side filtering,
3. simple search across the current table,
4. infinite scrolling or progressive block loading,
5. stable row identifiers where available,
6. export of filtered result sets.

This phase turns the explorer from a preview widget into a true investigation tool.

### Phase 4: Column intelligence and profiling

Once the core exploration workflow is stronger, add lightweight profiling and diagnostics.

Candidate capabilities:

1. distinct value sampling,
2. null and blank counts,
3. duplicate-value signals for likely key columns,
4. min and max values for numeric and date columns,
5. value-length summaries for text columns,
6. quick anomaly indicators for mixed or suspicious values.

This would help users design entities and foreign key relationships from actual source-data evidence rather than guesswork.

## AG Grid Fit Assessment

AG Grid is already present in the frontend and used elsewhere in the application.

Relevant existing examples:

1. [frontend/src/components/entities/FixedValuesGrid.vue](frontend/src/components/entities/FixedValuesGrid.vue)
2. [frontend/src/components/reconciliation/ReconciliationGrid.vue](frontend/src/components/reconciliation/ReconciliationGrid.vue)
3. [frontend/src/components/entities/EntityFormDialog.vue](frontend/src/components/entities/EntityFormDialog.vue)

That means the frontend does not need a new grid dependency or a new styling strategy from scratch.

For this proposal, AG Grid is a good fit because it provides:

1. strong handling of wide tabular datasets,
2. selection support,
3. better column resizing and visibility behavior,
4. built-in filtering and sorting on loaded rows,
5. a path to more advanced row-model strategies later.

However, AG Grid alone does not solve the main product limitation.

If the backend only returns 50 or 100 rows, then the grid only knows about 50 or 100 rows.

That means:

1. select-all only applies to loaded rows,
2. sorting only applies to loaded rows,
3. filtering only applies to loaded rows,
4. users may incorrectly assume they are operating on the full table unless the UI makes the scope explicit.

## Technical Scope

### Frontend scope

Likely frontend changes include:

1. refactoring [frontend/src/components/DataPreviewTable.vue](frontend/src/components/DataPreviewTable.vue) to use AG Grid,
2. adding dynamic column definitions from the preview payload,
3. translating current formatting logic into grid formatters and cell classes,
4. adding selection and optional export actions for loaded rows,
5. improving status messaging around loaded rows versus total rows,
6. preserving the current refresh, page-size, and next/previous flows initially.

### Backend scope

Later phases would likely require changes to:

1. [backend/app/api/v1/endpoints/schema.py](backend/app/api/v1/endpoints/schema.py)
2. [backend/app/services/schema_service.py](backend/app/services/schema_service.py)
3. any relevant loader support used by `load_table()` and row counting

Key backend additions may include:

1. higher preview limits,
2. safe limits by driver,
3. sort and filter parameters,
4. optional lightweight profiling endpoints,
5. server-side export endpoints for filtered selections.

## UX Principles

If this proposal is implemented, the UI should follow these principles:

1. make it obvious whether the user is seeing a preview slice or a larger investigation result,
2. distinguish loaded rows from total table rows,
3. warn before expensive operations,
4. keep the fast preview path for routine use,
5. avoid turning Schema Explorer into a general-purpose SQL workbench,
6. optimize for inspection and validation, not arbitrary query authoring.

The existing query tools already cover free-form SQL use cases elsewhere in the application.

## Suggested Initial Deliverable

The recommended first deliverable is:

1. replace the preview table with AG Grid,
2. keep the current preview API and current limit behavior,
3. add row selection and copy/export for loaded rows,
4. add explicit messaging about loaded-row scope,
5. defer larger fetches and server-side filtering to a later phase.

This keeps the first iteration low risk and user-visible without overcommitting to backend changes in the same pass.

## Risks And Tradeoffs

### Risks

1. users may over-trust client-side sort and filter behavior if the loaded-row scope is not clear,
2. increasing preview limits too aggressively could create performance issues on some drivers or source systems,
3. export features can blur the boundary between preview and extraction,
4. adding too much analytical behavior to Schema Explorer could overlap with the query tooling.

### Tradeoffs

1. keeping the initial phase client-side is simpler and faster to deliver,
2. adding backend-backed exploration later is more complex but provides the real long-term value,
3. a staged approach allows the team to validate actual user behavior before expanding the scope.

## Recommendation Summary

The recommendation is:

1. approve a phased raw source data explorer direction,
2. use AG Grid as the Phase 1 rendering layer for loaded rows,
3. keep the initial implementation low risk,
4. plan a later backend enhancement phase for larger fetches and server-driven exploration,
5. treat this as a user-facing investigation workflow improvement rather than a purely technical grid refactor.

## Conclusion

Users would benefit from a more powerful way to investigate raw source data, but the right solution is broader than simply replacing a table component.

The strongest path is to evolve Schema Explorer into a raw-data investigation tool in phases:

1. improve the loaded-row experience first,
2. then expand fetch and exploration capabilities,
3. then add profiling and server-driven investigation features as needed.

That approach preserves the current fast preview workflow while creating a clear path toward a much more useful raw source data explorer.