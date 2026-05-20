# Fixed Entity Column Type Controls In The Grid Header

## Status

- Proposed change
- Scope: fixed-entity column type controls in the frontend grid editor
- Goal: reduce vertical space and keep type selectors aligned with AG Grid columns

## Summary

The current fixed-entity editor renders column type selectors in a separate row above the grid. This wastes space and cannot stay aligned with AG Grid columns during resize or horizontal scroll. The recommendation is to move the selectors into the grid header area and use a compact custom header component for editable data columns.

This keeps the controls attached to the columns they affect and removes the detached control row. The header implementation should stay compact and preserve AG Grid header behavior.

## Problem

The current layout has two UX problems.

First, it consumes too much vertical space. Each column gets a separate control card above the grid with a label, a source label, and a select.

Second, the controls do not align with the grid columns. The controls are rendered in a standalone CSS grid, while AG Grid controls the real column widths, resize behavior, and horizontal scroll state.

This makes the UI feel disconnected and harder to scan.

## Scope

This proposal covers:

- the placement of fixed-entity column type controls in the frontend grid
- the expected compact layout for those controls
- the interaction constraints needed to keep AG Grid header behavior usable

## Non-Goals

This proposal does not cover:

- backend or persistence changes for `column_types`
- new type options beyond the currently supported set
- broader redesign of the fixed-values grid
- replacement of AG Grid built-in sorting, resizing, or header mechanics

## Current Behavior

The current implementation renders the column type selectors in a block above the grid. That block is separate from the AG Grid header.

This separation causes both reported issues:

- the extra block adds permanent vertical height
- the selectors cannot reliably align with column widths, resize events, pinned state, or horizontal scrolling

## Proposed Design

### Recommendation

Move the column type selector into the AG Grid header area for each editable data column.

Use a compact custom header component. Do not move the current three-line control card into the header unchanged.

### Header layout

Each editable column header should use a compact two-line layout:

- line 1: column name
- line 2: type selector

The current persistent source label such as `Declared:` or `Inferred:` should not remain as a full extra line in the header. It should move to a tooltip, title attribute, or other low-space hint.

### Column coverage

Show the header selector only where it is useful.

- normal editable data columns: show the selector
- `system_id`: omit the selector
- selection checkbox column: keep the existing simple header

If the existing product decision remains that selectors are visible for all logical columns, the compact header still applies. The key point is that the control must live inside the grid header area, not above it.

### Interaction constraints

The header solution must preserve AG Grid behavior.

- column resize must continue to work
- sort and other built-in header interactions must not break
- interacting with the select must not trigger unintended sort or drag behavior

This means the header component should be treated as a thin UI layer on top of AG Grid, not as a full replacement for header behavior unless that replacement is implemented deliberately.

### Visual target

Increase header height enough to fit the compact header layout, but keep it materially smaller than the current detached control row plus grid header combined.

## Alternatives Considered

### Keep the current detached controls row

Rejected. It does not solve either problem.

### Use a second aligned header-like row outside the grid

Rejected. It still duplicates AG Grid layout responsibility and remains fragile under resize and scroll.

### Use AG Grid floating filters as the control row

Deferred. This would align correctly, but it uses filtering UI for a non-filtering concern. The semantic mismatch is not worth it when a header-based solution fits the problem more directly.

## Risks And Tradeoffs

The main risk is header complexity. A full custom header can accidentally regress built-in AG Grid behavior if it intercepts clicks, sorting, dragging, or resize affordances incorrectly.

There is also a density tradeoff. Moving the selector into the header fixes alignment, but the header must stay compact or it will recreate the same space problem inside the grid.

Finally, very narrow columns may make a header select hard to use. The implementation may need a minimum width or a simplified presentation for narrow columns.

## Testing And Validation

Validate the change in the fixed-values grid with emphasis on layout and interaction.

- selectors remain aligned while resizing columns
- selectors remain aligned during horizontal scroll
- changing a selector still updates `column_types`
- sort, resize, and selection behavior still work as expected
- the header uses less total vertical space than the current detached controls row plus header

## Acceptance Criteria

- the standalone column-type controls row above the grid is removed
- each supported column type selector is rendered inside the AG Grid header area
- the selector stays aligned with its column during resize and scroll
- the header remains compact and does not use a persistent third line for source metadata
- AG Grid header interactions continue to work

## Recommended Delivery Order

1. Extract the selector UI into a small header component that receives the current column, current type, available options, and a change callback.
2. Remove the detached selector row from the fixed-values grid and wire the header component into the editable AG Grid columns.
3. Increase header height just enough to fit the compact two-line layout.
4. Keep `system_id` and the checkbox column on the simpler header path.
5. Validate the result with focused component tests for header wiring, type updates, and existing load-time coercion behavior.

## Final Recommendation

Adopt a compact, grid-native header approach for fixed-entity column type controls.

Use a custom header component for the columns that need a selector, keep the layout to column name plus selector, and move source metadata out of the permanent header layout. This is the smallest change that addresses both current problems without introducing a parallel layout system above the grid.
