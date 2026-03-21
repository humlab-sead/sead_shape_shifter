# Vuetify 4 Migration Resume Plan

## Status

- Proposed migration plan / implementation checkpoint
- Scope: frontend Vuetify upgrade from 3.x to 4.x
- Goal: capture current findings, safe vs unsafe pre-migration work, and the next execution steps so work can resume later without re-discovery
- Current baseline: frontend production build passes on Vuetify 3
- Tracking issues: none yet

## Summary

This proposal records the current state of Vuetify 4 migration analysis for the Shape Shifter frontend.

The project was scanned using the Vuetify MCP guidance and then validated against the actual Vue/Volar/TypeScript behavior in the current Vuetify 3 toolchain.

The main conclusion is:

1. some Vuetify 4 changes can be identified now,
2. some apparent pre-migration fixes are **not** safe to apply while still on Vuetify 3,
3. the frontend build baseline is now clean, which makes a future migration much safer,
4. the remaining Vuetify 4 work should be done as a dedicated migration pass rather than as piecemeal speculative edits.

## Current Verified State

As of this proposal:

1. the frontend build succeeds with `pnpm build`,
2. the `ProjectDataSources` typing and include-path parsing issues were fixed during cleanup,
3. dependency graph frontend typing was aligned with the current backend/frontend object-edge model,
4. several unrelated frontend TypeScript issues were fixed to restore a clean baseline.

This matters because the Vuetify 4 migration should start from a clean build, not from a frontend already carrying unrelated type failures.

## Confirmed Vuetify 4 Findings

### 1. Select-like item slot rename is a real Vuetify 4 change

Vuetify MCP reports that for `VSelect`, `VAutocomplete`, and `VCombobox`, the item slot prop is renamed from `item` to `internalItem` in Vuetify 4.

Affected files identified during scanning:

1. [frontend/src/components/execute/ExecuteDialog.vue](frontend/src/components/execute/ExecuteDialog.vue)
2. [frontend/src/components/entities/CreateEntityFromTableDialog.vue](frontend/src/components/entities/CreateEntityFromTableDialog.vue)
3. [frontend/src/components/entities/MaterializeDialog.vue](frontend/src/components/entities/MaterializeDialog.vue)
4. [frontend/src/components/entities/EntityFormDialog.vue](frontend/src/components/entities/EntityFormDialog.vue)
5. [frontend/src/components/ProjectDataSources.vue](frontend/src/components/ProjectDataSources.vue)
6. [frontend/src/components/SchemaTreeView.vue](frontend/src/components/SchemaTreeView.vue)
7. [frontend/src/components/DataSourceFormDialog.vue](frontend/src/components/DataSourceFormDialog.vue)
8. [frontend/src/components/query/QueryBuilder.vue](frontend/src/components/query/QueryBuilder.vue)

### 2. Those slot renames are not safe to pre-apply on the current Vuetify 3 setup

Even though some Vuetify 3 metadata suggested both names may exist in some internal typings, the actual current template type checker in this repo reported errors such as:

```text
Property 'internalItem' does not exist on type '{ item: ListItem<...>; index: number; props: Record<string, unknown>; }'.
```

That means these slot renames should be applied when the project actually migrates to Vuetify 4, not before.

### 3. Grid migration remains a review item, not an automated pre-fix

Vuetify 4 changes the grid system significantly. This project contains multiple `v-row dense` usages and some direct CSS overrides targeting Vuetify grid classes.

These are migration hotspots, but not safe blanket edits ahead of the real upgrade.

Examples:

1. [frontend/src/components/entities/ExtraColumnsEditor.vue](frontend/src/components/entities/ExtraColumnsEditor.vue)
2. [frontend/src/components/entities/FiltersEditor.vue](frontend/src/components/entities/FiltersEditor.vue)
3. [frontend/src/components/entities/ReplacementsEditor.vue](frontend/src/components/entities/ReplacementsEditor.vue)
4. [frontend/src/components/entities/ForeignKeyEditor.vue](frontend/src/components/entities/ForeignKeyEditor.vue)
5. [frontend/src/components/LogViewerOverlay.vue](frontend/src/components/LogViewerOverlay.vue)
6. [frontend/src/components/dependencies/TaskCompletionStats.vue](frontend/src/components/dependencies/TaskCompletionStats.vue)
7. [frontend/src/components/reconciliation/SpecificationEditor.vue](frontend/src/components/reconciliation/SpecificationEditor.vue)
8. [frontend/src/styles/global.css](frontend/src/styles/global.css)

### 4. One safe visual alignment change was retained

The overlay card elevation in [frontend/src/components/entities/EntityEditorOverlay.vue](frontend/src/components/entities/EntityEditorOverlay.vue) was reduced from `24` to `5` to match Vuetify 4's Material Design 3 elevation scale.

This is valid in Vuetify 3 as well, but it may have a visible shadow difference.

## What Was Tried And Learned

### Attempted pre-migration slot rename

The select-slot rename from `item` to `internalItem` was attempted first as a proactive migration step.

It was then reverted because the current Vuetify 3 template checker rejected it in several components.

### Resulting rule

Use this as the working migration rule for this repo:

1. do **not** rename item slots to `internalItem` while still on the current Vuetify 3 stack,
2. do that rename only in the Vuetify 4 upgrade branch or migration commit series,
3. validate with `vue-tsc` immediately after the dependency bump.

## Recommended Migration Strategy

### Phase 0: Start From The Clean Baseline

Before touching Vuetify versions:

1. confirm `pnpm build` still passes,
2. confirm the working tree is clean or intentionally scoped,
3. branch specifically for the migration.

### Phase 1: Upgrade Dependencies First

Upgrade the actual frontend dependencies before changing templates:

1. `vuetify`
2. related Vuetify build plugin if needed
3. any peer packages affected by the upgrade

Then run:

```bash
cd frontend
pnpm install
pnpm build
```

Only after the dependency upgrade should the template migrations begin.

### Phase 2: Apply The Known Breaking Template Changes

First pass after dependency upgrade:

1. rename select-style item slot props from `item` to `internalItem`,
2. update all `item.raw` references to `internalItem.raw` in those slots,
3. re-run `pnpm build`.

This should be the highest-priority code change because it is a direct API-level break.

### Phase 3: Resolve Grid And CSS Layer Issues

Second pass:

1. review all `v-row dense` usage,
2. review direct `.v-row`, `.v-col`, `.v-container` overrides in [frontend/src/styles/global.css](frontend/src/styles/global.css),
3. move fragile overrides toward explicit spacing utilities or custom layer-aware CSS,
4. visually test entity editors, project detail screens, table/config forms, and schema explorer layouts.

### Phase 4: Review Typography And Theme Visual Regressions

Third pass:

1. review legacy typography utility classes such as `text-h4`, `text-subtitle-1`, `text-body-2`, and `text-caption`,
2. confirm the current `defaultTheme: 'light'` setting in [frontend/src/plugins/vuetify.ts](frontend/src/plugins/vuetify.ts) still reflects the desired behavior after the upgrade,
3. compare key pages visually rather than assuming parity.

## Suggested Execution Checklist

When resuming, follow this order:

1. read this proposal,
2. verify the frontend still builds on the current branch,
3. bump Vuetify-related dependencies,
4. run `pnpm build` and collect the new Vuetify 4 errors,
5. apply the eight known slot-prop renames,
6. rerun `pnpm build`,
7. review grid and CSS overrides,
8. run a quick manual UI pass over:
   - project detail view,
   - entity form dialog,
   - data source dialogs,
   - schema explorer,
   - query builder/editor,
   - help and settings pages,
9. only then consider broader typography cleanup.

## Recommended Manual Test Areas

Focus manual testing on these views/components because they are most likely to show migration fallout:

1. [frontend/src/views/ProjectDetailView.vue](frontend/src/views/ProjectDetailView.vue)
2. [frontend/src/components/entities/EntityFormDialog.vue](frontend/src/components/entities/EntityFormDialog.vue)
3. [frontend/src/components/ProjectDataSources.vue](frontend/src/components/ProjectDataSources.vue)
4. [frontend/src/components/DataSourceFormDialog.vue](frontend/src/components/DataSourceFormDialog.vue)
5. [frontend/src/components/SchemaTreeView.vue](frontend/src/components/SchemaTreeView.vue)
6. [frontend/src/components/query/QueryBuilder.vue](frontend/src/components/query/QueryBuilder.vue)
7. [frontend/src/components/query/QueryEditor.vue](frontend/src/components/query/QueryEditor.vue)
8. [frontend/src/views/SchemaExplorerView.vue](frontend/src/views/SchemaExplorerView.vue)

## Proposed Deliverable Shape

When the actual migration is resumed, it should ideally be delivered in this order:

1. dependency bump,
2. template/API break fixes,
3. grid/layout fixes,
4. visual regression cleanup,
5. docs update summarizing the migration.

That sequence keeps the work auditable and reduces the chance of mixing API fixes with visual tuning.

## Conclusion

The project is now in a good state to resume Vuetify 4 migration later because the frontend build baseline is clean and the first known migration traps are already documented.

The most important learned constraint is this:

**Do not pre-apply the select slot `internalItem` rename on the current Vuetify 3 stack. Apply it only after the dependency upgrade to Vuetify 4.**

This proposal should be used as the handoff point for the next migration session.