# Project Folder Navigation With Breadcrumbs

## Status

- Proposed feature / change request
- Related issue: [#300](https://github.com/humlab-sead/sead_shape_shifter/issues/300)
- Scope: folder navigation in the Projects view
- Goal: make existing project folder structure visible and browsable

## Summary

Projects can already be stored in nested folders, but the Projects view shows them as a flat list. Add client-side folder navigation with breadcrumbs so users can browse projects by their existing folder structure without changing project identity or the project-list API.

## Problem

As the project collection grows, users need a way to find projects by their folder organization. The backend already returns nested project paths using `:` separators, but the Projects view displays those names as flat strings.

## Scope

- Show folders and projects at the current folder level.
- Let users navigate into a folder and return to parent folders through breadcrumbs.
- Reflect the browsed folder in the Projects view URL so navigation survives refresh and the browser back button.
- Keep global search available; show each matching project’s folder path in search results.
- Preserve current project-list sorting and project actions.

## Non-Goals

- Creating, renaming, moving, or deleting folders.
- Listing empty folders that contain no projects.
- Changing project names, API routes, authorization locators, or project-list response data.
- Changing the project-list cache or backend discovery behavior.

## Current Behavior

The backend recursively discovers project files and derives API names from their relative directory paths. `ProjectNameMapper` represents path separators as `:` in project names, such as `arbodat:arbodat-test`.

The Projects view currently displays those names in one flat list and filters by the full project name. The frontend project store caches the list for 30 seconds and revalidates stale data in the background.

## Proposed Design

Treat the colon-separated project name as the existing project path for display purposes only:

1. Split each project name into folder segments and a project name.
2. At the current folder, display projects directly in that folder and child folders containing projects. Folders are always listed before projects and sorted by name; the selected sort option applies to projects only.
3. Selecting a child folder displays its contents and updates the breadcrumb path.
4. Selecting a breadcrumb returns to that folder.
5. Store the current folder in the Projects view URL as a query parameter, for example `/projects?folder=arbodat`. Loading the Projects view with that parameter opens the folder directly; the browser back button undoes one folder step; a folder absent from the current list renders as empty until the list revalidates.
6. Global search continues to search project names and folder segments. While a search is active it replaces the folder view with a flat result list; each result shows its folder path so users can identify where the match belongs. Clearing the search restores the browsed folder. Selecting a result opens the project detail page as it does today.
7. Keep the complete colon-separated project name unchanged for routing, selection, copy, validation, and deletion.

Build the folder view from the cached project metadata. No backend folder tree or separate cache representation is needed. Existing stale-while-revalidate behavior remains in effect after project list changes or external folder moves.

## Risks And Tradeoffs

- A client-derived folder view cannot show empty directories because the project list contains only discovered projects.
- Search results spanning multiple folders need to show their location and should not imply that they belong to the currently browsed folder.
- Display parsing must not change the colon-separated project name passed to routes or API actions.
- Projects moved outside the application may appear under their old path until the list is refreshed or revalidated.
- A directory created outside the application whose name literally contains `:` is indistinguishable from a nested project and will display as an extra folder level. Backend name validation treats `:` as a separator, so no application-created name can produce this case.

## Testing And Validation

Verify the Projects view with top-level and nested project names, including multiple nesting levels. Cover folder navigation, breadcrumb navigation, global search results with paths, sorting, and project actions to confirm they still use the full project name. Confirm cached project data can be rendered without additional folder requests. Confirm the URL reflects the browsed folder, that refresh and the browser back button restore it, and that folders list before projects regardless of the selected sort.

## Acceptance Criteria

- `P-AC-1` Nested project names are presented through visible folder navigation rather than only as flat colon-separated strings.
- `P-AC-2` Breadcrumb navigation reaches the root and each visited parent folder.
- `P-AC-3` Global search finds projects across folders and displays enough path context to identify each result.
- `P-AC-4` Project actions continue to use the original full project name.
- `P-AC-5` Folder navigation uses the existing project-list data and preserves current cache behavior.
- `P-AC-6` The browsed folder is encoded in the Projects view URL and restored on refresh and browser back navigation.
- `P-AC-7` Folders display before projects and are sorted by name regardless of the selected project sort.

## Recommended Delivery Order

Implement as one focused frontend change. A separate multi-phase plan is not needed unless scope expands to folder management or backend folder APIs.

## Final Recommendation

Proceed with client-side folder navigation and breadcrumbs. It makes the existing directory structure useful in the UI while keeping project identity, API behavior, and caching unchanged.
