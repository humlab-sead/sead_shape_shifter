# Split-Pane Preview Implementation

## Overview
Added split-pane layout with live preview to the Entity Form Dialog, providing a REPL-like experience for entity editing.

## Features Implemented

### 1. Split-Pane Layout
- **Toggle Button**: Expand/collapse preview panel with toolbar button
- **Keyboard Shortcut**: `Ctrl+Shift+P` to toggle split view
- **Responsive Design**: Dialog width adjusts to 95vw when split view is active
- **50/50 Split**: Form on left, preview on right

### 2. Live Preview Panel
- **Real-time Data**: Shows entity data as it would appear after transformations
- **Column Info**: Displays column names, data types, and key indicators
- **Row Count**: Shows number of rows in preview
- **Last Refresh**: Timestamp showing when preview was last updated

### 3. Auto-Refresh
- **Manual Refresh**: Button to manually update preview
- **Auto-Refresh Toggle**: Checkbox to enable automatic refresh on changes
- **Debounced Updates**: 1-second delay after last change to prevent excessive API calls
- **Loading Indicator**: Progress bar while preview is loading

### 4. Error Handling
- **Error Display**: Alert shown when preview fails
- **Validation**: Only available in edit mode (not create mode)
- **Graceful Degradation**: Shows helpful message when entity not yet saved

## Files Modified

### `/frontend/src/composables/useEntityPreview.ts`
- Added `lastRefresh` ref to track when preview was last updated
- Added `debouncedPreviewEntity` function using `useDebounceFn` from `@vueuse/core`
- Updated return object to include new state and functions

### `/frontend/src/components/entities/EntityFormDialog.vue`
**Template Changes:**
- Replaced `v-card-title` with `v-toolbar` for better layout
- Added split-view toggle button with tooltip
- Wrapped content in split-pane layout structure (`.split-layout`, `.form-panel`, `.preview-panel`)
- Added live preview panel with:
  - Header with refresh button, row count, timestamp, and auto-refresh toggle
  - Preview table with column headers and data rows
  - Error and empty state displays

**Script Changes:**
- Imported `useEntityPreview` composable and `onMounted`/`onUnmounted` lifecycle hooks
- Added split-pane state management (`splitView`, `autoRefreshEnabled`)
- Added preview state (`livePreviewData`, `previewLoading`, `previewError`, `livePreviewLastRefresh`)
- Implemented helper functions:
  - `toggleSplitView()` - Toggle split view and refresh preview
  - `refreshPreview()` - Manually refresh preview data
  - `formatRefreshTime()` - Format refresh timestamp
  - `handleKeyPress()` - Handle Ctrl+P keyboard shortcut
- Added watchers for auto-refresh on form changes
- Added keyboard event listeners

**Style Changes:**
- Added split-pane layout styles (`.split-container`, `.split-layout`, `.form-panel`, `.preview-panel`)
- Added preview-specific styles (`.preview-header`, `.preview-content`, `.preview-table-container`)
- Added striped row styling for better readability
- All styles use Vuetify theme variables for dark mode compatibility

## Usage

### Opening Split View
1. Open an entity in edit mode
2. Click the expand icon in the toolbar (or press `Ctrl+Shift+P`)
3. Preview panel appears on the right side
4. Click refresh to load initial preview data

### Auto-Refresh
1. Enable "Auto-refresh" checkbox in preview header
2. Edit entity configuration (change columns, filters, etc.)
3. Preview automatically updates 1 second after last change
4. Disable auto-refresh for manual control

### Best Practices
- Use split view for iterative development and testing
- Enable auto-refresh when making multiple small changes
- Disable auto-refresh when making large structural changes
- Use manual refresh for full control over preview updates

## Technical Details

### Debouncing
- Auto-refresh uses 1000ms (1 second) debounce
- Prevents excessive API calls during rapid edits
- Uses `useDebounceFn` from `@vueuse/core` library

### Performance
- Preview component lazy-loaded only when needed
- Grid component (FixedValuesGrid) already lazy-loaded with `defineAsyncComponent`
- Preview limited to 100 rows by default for performance

### Accessibility
- Keyboard shortcut (`Ctrl+Shift+P`) for power users
- Clear visual indicators for loading, errors, and empty states
- Tooltips on buttons for discoverability
- Disabled state when preview not available (create mode)

## Future Enhancements
- Resizable split pane (drag to adjust width)
- Preview settings (limit, cache control)
- Column filtering and sorting in preview
- Export preview data
- Compare before/after for edits
- Pin/unpin preview panel position
