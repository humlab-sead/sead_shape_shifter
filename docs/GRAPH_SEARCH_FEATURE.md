# Graph Filtering/Search Feature

## Overview

Feature to enable quick entity discovery and navigation in large dependency graphs. This will add real-time search with visual highlighting, match navigation, and keyboard shortcuts.

## User Interface Components

### Location
Add to the graph tools area in `frontend/src/views/ProjectDetailView.vue`, near the existing graph FAB controls.

### Components
- **Search text field** with clear button
- **Match counter** showing "X of Y matches"
- **Previous/Next navigation buttons** for cycling through results
- **Visual feedback** for active search state

## Core Features

### Search Capabilities
- **Case-insensitive** entity name matching
- **Real-time filtering** as user types (300ms debounce)
- **Visual highlighting** of matching nodes
- **Dimming** of non-matching nodes (30-40% opacity)
- **Auto-centering** viewport on selected match

### Navigation
- **Cycle through matches** with Previous/Next buttons
- **Keyboard shortcuts:**
  - `Enter` - Next match
  - `Shift+Enter` - Previous match
  - `Escape` - Clear search
- **Auto-center** on current match with smooth animation

### Visual Feedback
- **Matched nodes:** Blue border (3px), full opacity, z-index 10
- **Current match:** Orange border (4px), glow effect, z-index 100
- **Non-matches:** 30% opacity, z-index 1
- **Connected edges:** Maintain visibility for context

## Technical Implementation

### State Management

Add to `ProjectDetailView.vue`:

```typescript
const searchQuery = ref('')
const searchResults = ref<string[]>([])  // Array of matching node IDs
const currentMatchIndex = ref(-1)
const isSearchActive = ref(false)
```

### Search Logic

```typescript
import { debounce } from 'lodash-es'

const performSearch = debounce((query: string) => {
  if (!query.trim()) {
    clearSearch()
    return
  }

  const cy = cyInstance.value
  if (!cy) return

  // Find matching nodes
  const matches = cy.nodes().filter((node) => {
    const nodeData = node.data()
    const entityName = nodeData.label || nodeData.id
    return entityName.toLowerCase().includes(query.toLowerCase())
  })

  searchResults.value = matches.map(n => n.id())
  currentMatchIndex.value = searchResults.value.length > 0 ? 0 : -1
  isSearchActive.value = true

  // Apply visual styles
  cy.batch(() => {
    // Dim all nodes
    cy.nodes().addClass('search-dimmed')
    
    // Highlight matches
    matches.addClass('search-match')
    
    // Highlight current match
    if (currentMatchIndex.value >= 0) {
      cy.$id(searchResults.value[0]).addClass('search-current')
    }
  })

  // Center on first match
  if (matches.length > 0) {
    cy.animate({
      center: { eles: cy.$id(searchResults.value[0]) },
      zoom: cy.zoom(),
      duration: 300
    })
  }
}, 300)

const handleSearchInput = (value: string) => {
  searchQuery.value = value
  performSearch(value)
}
```

### Navigation Functions

```typescript
const navigateToMatch = (direction: 'next' | 'prev') => {
  if (searchResults.value.length === 0) return

  const cy = cyInstance.value
  if (!cy) return

  // Remove current highlight
  cy.nodes('.search-current').removeClass('search-current')

  // Update index
  if (direction === 'next') {
    currentMatchIndex.value = (currentMatchIndex.value + 1) % searchResults.value.length
  } else {
    currentMatchIndex.value = 
      currentMatchIndex.value === 0 
        ? searchResults.value.length - 1 
        : currentMatchIndex.value - 1
  }

  // Highlight new current
  const currentId = searchResults.value[currentMatchIndex.value]
  const currentNode = cy.$id(currentId)
  currentNode.addClass('search-current')

  // Center on node
  cy.animate({
    center: { eles: currentNode },
    duration: 300
  })
}

const clearSearch = () => {
  const cy = cyInstance.value
  if (!cy) return

  searchQuery.value = ''
  searchResults.value = []
  currentMatchIndex.value = -1
  isSearchActive.value = false

  cy.batch(() => {
    cy.nodes().removeClass('search-dimmed search-match search-current')
  })
}
```

### Keyboard Shortcuts

```typescript
const handleSearchKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter') {
    e.preventDefault()
    navigateToMatch(e.shiftKey ? 'prev' : 'next')
  } else if (e.key === 'Escape') {
    clearSearch()
  }
}
```

## UI Template

Add to the graph tools section in `ProjectDetailView.vue`:

```vue
<!-- Graph Search -->
<div class="graph-search-container">
  <v-text-field
    v-model="searchQuery"
    @input="handleSearchInput"
    @keydown="handleSearchKeydown"
    density="compact"
    variant="outlined"
    placeholder="Search entities..."
    prepend-inner-icon="mdi-magnify"
    clearable
    hide-details
    class="search-field"
    :class="{ 'search-active': isSearchActive }"
  >
    <template v-if="searchResults.length > 0" #append>
      <div class="search-counter">
        {{ currentMatchIndex + 1 }} of {{ searchResults.length }}
      </div>
    </template>
  </v-text-field>

  <v-btn-group v-if="searchResults.length > 1" density="compact">
    <v-btn 
      icon="mdi-chevron-up" 
      size="small"
      @click="navigateToMatch('prev')"
      title="Previous match (Shift+Enter)"
    />
    <v-btn 
      icon="mdi-chevron-down" 
      size="small"
      @click="navigateToMatch('next')"
      title="Next match (Enter)"
    />
  </v-btn-group>
</div>
```

## Cytoscape Styles

Add to the stylesheet definition in `useCytoscape.ts` or `ProjectDetailView.vue`:

```typescript
const stylesheet = [
  // ... existing styles ...
  
  // Search dimmed nodes
  {
    selector: '.search-dimmed',
    style: {
      'opacity': 0.3,
      'z-index': 1
    }
  },
  
  // Search match nodes
  {
    selector: '.search-match',
    style: {
      'opacity': 1,
      'border-width': 3,
      'border-color': '#2196F3',
      'z-index': 10
    }
  },
  
  // Current search result
  {
    selector: '.search-current',
    style: {
      'border-width': 4,
      'border-color': '#FF9800',
      'box-shadow': '0 0 10px #FF9800',
      'z-index': 100
    }
  }
]
```

## CSS Styling

Add to `ProjectDetailView.vue` styles:

```css
.graph-search-container {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.search-field {
  max-width: 300px;
  flex: 1;
}

.search-field.search-active {
  background-color: rgba(33, 150, 243, 0.05);
}

.search-counter {
  font-size: 0.75rem;
  color: rgba(0, 0, 0, 0.6);
  padding: 0 8px;
  white-space: nowrap;
}
```

## Context Help Integration

Add to `frontend/src/components/ContextHelp.vue` for the dependency graph route:

```typescript
{
  title: 'Graph Search',
  tips: [
    'Type in the search field to filter entities by name',
    'Use <span style="color: #2196F3;">↑/↓ buttons</span> or <span style="color: #FF9800;">Enter</span> to navigate matches',
    'Press <span style="color: #F44336;">Escape</span> to clear search and restore full view'
  ],
  shortcuts: [
    { keys: ['Enter'], action: 'Next match' },
    { keys: ['Shift', 'Enter'], action: 'Previous match' },
    { keys: ['Esc'], action: 'Clear search' }
  ]
}
```

## Enhanced Features (Future)

### Advanced Search Options
- **Filter by node type** - Entity vs data source filtering
- **Regex support** - Advanced pattern matching
- **Property search** - Search in node properties beyond name
- **Recent searches** - Save and recall previous searches

### Performance Optimizations
- **Virtualization** - Handle graphs with >1000 nodes efficiently
- **Entity indexing** - Pre-index entity names for faster searching
- **Lazy loading** - Progressive graph rendering for very large datasets

### UX Improvements
- **Highlight search term** - Show matched portion in node labels
- **Preview tooltips** - Display entity details on hover
- **Auto-complete** - Suggest entity names as user types
- **Search history** - Dropdown with recent searches

## Integration Points

This feature integrates with existing functionality:

1. **Create New Node** - Search helps find placement context for new entities
2. **Quick YAML Editor** - Search + single-click for rapid editing workflow
3. **Double-click Editor** - Search + double-click for detailed entity editing
4. **Resizable Sidebar** - Context help displays search shortcuts
5. **Data Source Nodes** - Exclude from search or show with different visual treatment

## Implementation Checklist

- [ ] Add search state variables to ProjectDetailView.vue
- [ ] Implement performSearch function with debouncing
- [ ] Add navigateToMatch and clearSearch functions
- [ ] Create handleSearchKeydown for keyboard shortcuts
- [ ] Add search UI template to graph tools section
- [ ] Define Cytoscape stylesheet classes for search states
- [ ] Add CSS styling for search container and components
- [ ] Update ContextHelp.vue with search shortcuts
- [ ] Test search with graphs of varying sizes
- [ ] Test keyboard navigation through matches
- [ ] Test edge cases (no matches, single match, clearing search)
- [ ] Ensure accessibility (ARIA labels, keyboard navigation)

## Testing Scenarios

1. **Empty search** - Verify no filtering occurs
2. **Single match** - Navigation buttons should not appear
3. **Multiple matches** - Test prev/next cycling behavior
4. **No matches** - Display appropriate feedback
5. **Clear search** - All nodes return to normal state
6. **Large graphs** - Verify performance with 100+ nodes
7. **Keyboard shortcuts** - Test all shortcut combinations
8. **Data source nodes** - Verify proper handling/exclusion

## Dependencies

- **lodash-es** - For debounce function (already in project)
- **Cytoscape.js** - Core graph library (already in project)
- **Vuetify** - UI components (v-text-field, v-btn-group)

## Related Files

- `frontend/src/views/ProjectDetailView.vue` - Main implementation
- `frontend/src/composables/useCytoscape.ts` - Graph instance management
- `frontend/src/components/ContextHelp.vue` - Help text updates
- `frontend/src/types/cytoscape.ts` - Type definitions (if needed)
