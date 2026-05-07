---
applyTo: "frontend/src/composables/useCytoscape.ts,frontend/src/composables/useDependencies.ts,frontend/src/components/dependencies/**,frontend/src/utils/graphAdapter.ts,frontend/src/utils/taskGraph.ts,frontend/src/config/cytoscapeStyles.ts"
---

# Graph / Dependency Visualisation – AI Coding Instructions

## Architecture

- `useCytoscape.ts` — composable wrapping a Cytoscape.js instance; handles init, layout, element updates, and events.
- `graphAdapter.ts` — pure utility functions: `toCytoscapeElements()` (domain data → Cytoscape elements), `getLayoutConfig()` (layout type → Cytoscape layout options).
- `cytoscapeStyles.ts` — style sheets (light/dark themes, task status classes, materialized badge).
- `taskGraph.ts` — maps task status to Cytoscape node CSS classes.

## Layout Types

Three layout types, mapped in `getLayoutConfig()`:

| `layoutType` | Cytoscape algorithm | Use case |
|-------------|---------------------|---------|
| `'hierarchical'` | `dagre` | Directed dependency trees |
| `'force'` | `cose-bilkent` | Organic force-directed layout |
| `'custom'` | User-saved positions | Frozen manual layout |

- Default in `useCytoscape` is `'hierarchical'`; default in `ProjectDetailView` is `'force'`.
- Layouts are registered once at module load: `cytoscape.use(dagre)`, `cytoscape.use(coseBilkent)`. Never call `cytoscape.use()` again.

## Element Updates (`updateElements`)

- On initial render: adds all elements, then runs layout.
- On subsequent updates: diffs existing elements against new data; removes stale elements, adds new ones.
- Layout is only re-run when new nodes are added — not on data-only updates.
- Always call via `nextTick()` to ensure the container DOM is mounted.

## Task Status Node Classes

`TASK_STATUS_NODE_CLASSES` in `taskGraph.ts` lists all valid classes:
`task-todo`, `task-done`, `task-ignored`, `task-ongoing`, `task-blocked`, `task-critical`, `task-ready`, `task-flagged`, `task-has-note`.

- When updating a node's task status: first remove all status classes, then add the new one.
- Never apply status classes manually — always use `getTaskStatusNodeClasses()`.
- Styles are defined in `cytoscapeStyles.ts` per selector, e.g. `'node.task-ignored'`.

## Materialized Badge

An SVG overlay badge (`MATERIALIZED_BADGE_SVG`) is applied to materialized entity nodes via Cytoscape background overlay.
- Set via CSS `background-image` on the node selector.
- Never use a separate Cytoscape element for the badge — it is a style property only.

## `UseCytoscapeOptions`

All reactive inputs are `Ref<T>` — do not pass raw values. Key options:
- `container: Ref<HTMLElement | null>` — must be non-null at render time.
- `graphData: Ref<DependencyGraph | null>` — null graph renders nothing.
- `layoutType: Ref<'hierarchical' | 'force' | 'custom'>`
- `customPositions: Ref<CustomGraphLayout | null>` — only used when `layoutType === 'custom'`.

## Common Mistakes

- Calling `cytoscape.use(dagre)` or `cytoscape.use(coseBilkent)` inside a component or composable — layouts are registered at module level only.
- Updating Cytoscape elements without `nextTick()` — container may not be mounted.
- Applying task status classes without clearing old ones first.
- Passing raw values instead of `Ref<T>` to `useCytoscape`.
- Adding a new layout type without adding it to both `getLayoutConfig()` and the `layoutType` union type.

## Testing Expectations

- Test `toCytoscapeElements()` with a `DependencyGraph` fixture — verify node and edge structure.
- Test `getLayoutConfig()` for all three layout types.
- Test `getTaskStatusNodeClasses()` for each status value.
- Do not instantiate a real Cytoscape instance in unit tests — mock or stub `cytoscape()`.
