# TODO #160 Task List Feature - Stage 2 Integration Guide

## Overview
Stage 2 (Frontend UI) components are complete and ready for integration into ProjectDetailView.

## Completed Components

### 1. Core Infrastructure
- ✅ `useTaskStatus.ts` - Composable for task operations
- ✅ `taskStatus.ts` - Pinia store for centralized state
- ✅ Cytoscape styles - Task status badge styles added

### 2. UI Components
- ✅ `TaskFilterPanel.vue` - Collapsible filter panel with badge counts
- ✅ `TaskCompletionStats.vue` - Progress display with percentage
- ✅ `GraphNodeContextMenu.vue` - Extended with task actions

## Integration Steps for ProjectDetailView.vue

### Step 1: Import Task Components
```typescript
import { useTaskStatusStore } from '@/stores/taskStatus'
import TaskFilterPanel from '@/components/dependencies/TaskFilterPanel.vue'
import TaskCompletionStats from '@/components/dependencies/TaskCompletionStats.vue'
import type { TaskFilter } from '@/components/dependencies/TaskFilterPanel.vue'
```

### Step 2: Initialize Task Store
```typescript
// In setup()
const taskStatusStore = useTaskStatusStore()
const currentFilter = ref<TaskFilter>('all')

// Initialize when project loads
watch(() => props.name, async (newName) => {
  if (newName) {
    await taskStatusStore.initialize(newName)
  }
}, { immediate: true })
```

### Step 3: Add Task Filter Panel to Sidebar
Add to the left sidebar (near NodeLegend):
```vue
<template>
  <v-navigation-drawer>
    <!-- Existing content -->
    
    <!-- Task Filter Panel -->
    <TaskFilterPanel
      v-model="currentFilter"
      :task-status="taskStatusStore.taskStatus"
      class="mb-4"
    />
    
    <NodeLegend ... />
  </v-navigation-drawer>
</template>
```

### Step 4: Add Completion Stats to Toolbar
Add to graph toolbar (near zoom controls):
```vue
<v-toolbar density="compact">
  <!-- Existing toolbar items -->
  
  <!-- Task Completion Stats -->
  <TaskCompletionStats
    :task-status="taskStatusStore.taskStatus"
    show-details
  />
  
  <!-- Zoom controls, etc -->
</v-toolbar>
```

### Step 5: Wire Up Context Menu Actions
Update context menu event handlers:
```typescript
// Add new handlers
async function handleMarkComplete(entityName: string) {
  const success = await taskStatusStore.markComplete(entityName)
  if (success) {
    // Refresh graph to show updated badges
    await refreshGraph()
  }
}

async function handleMarkIgnored(entityName: string) {
  const success = await taskStatusStore.markIgnored(entityName)
  if (success) {
    await refreshGraph()
  }
}

async function handleResetStatus(entityName: string) {
  const success = await taskStatusStore.resetStatus(entityName)
  if (success) {
    await refreshGraph()
  }
}

// Update context menu component
<GraphNodeContextMenu
  v-model="contextMenu.open"
  :x="contextMenu.x"
  :y="contextMenu.y"
  :entity-name="contextMenu.entityName"
  @preview="handlePreviewEntity"
  @duplicate="handleDuplicateEntity"
  @delete="handleDeleteEntity"
  @mark-complete="handleMarkComplete"
  @mark-ignored="handleMarkIgnored"
  @reset-status="handleResetStatus"
/>
```

### Step 6: Apply Task Status to Graph Nodes
Update graph rendering to apply task status classes:
```typescript
function applyTaskStatusToNodes() {
  if (!cy.value || !taskStatusStore.taskStatus) return

  // Apply classes based on task status
  cy.value.nodes().forEach(node => {
    const entityName = node.id()
    const status = taskStatusStore.getEntityStatus(entityName)
    
    if (!status) return

    // Remove existing task classes
    node.removeClass('task-done task-ignored task-blocked task-critical')

    // Apply status-based classes
    if (status.status === 'done') {
      node.addClass('task-done')
    } else if (status.status === 'ignored') {
      node.addClass('task-ignored')
    } else if (status.blocked_by && status.blocked_by.length > 0) {
      node.addClass('task-blocked')
    } else if (status.priority === 'critical') {
      node.addClass('task-critical')
    }
  })
}

// Call after rendering graph
watch(() => taskStatusStore.taskStatus, () => {
  applyTaskStatusToNodes()
}, { deep: true })
```

### Step 7: Filter Graph by Task Status
Update graph filtering logic:
```typescript
function applyTaskFilter() {
  if (!cy.value) return

  if (currentFilter.value === 'all') {
    // Show all nodes
    cy.value.nodes().style('display', 'element')
  } else {
    // Filter by status
    cy.value.nodes().forEach(node => {
      const entityName = node.id()
      const status = taskStatusStore.getEntityStatus(entityName)
      
      let show = false
      switch (currentFilter.value) {
        case 'todo':
          show = status?.status === 'todo'
          break
        case 'done':
          show = status?.status === 'done'
          break
        case 'ignored':
          show = status?.status === 'ignored'
          break
        case 'blocked':
          show = status?.blocked_by && status.blocked_by.length > 0
          break
        case 'critical':
          show = status?.priority === 'critical'
          break
      }
      
      node.style('display', show ? 'element' : 'none')
    })
  }
  
  // Re-fit graph after filtering
  cy.value.fit()
}

watch(currentFilter, applyTaskFilter)
```

## CSS Styles Already Added

The following Cytoscape styles are already configured in `cytoscapeStyles.ts`:
- `.task-done` - Green background with dark green border
- `.task-ignored` - Gray with reduced opacity
- `.task-blocked` - Orange double border
- `.task-critical` - Red thick border

## API Integration

All API calls are handled through the store:
- `taskStatusStore.markComplete(entityName)` → `POST /projects/{name}/tasks/{entity}/complete`
- `taskStatusStore.markIgnored(entityName)` → `POST /projects/{name}/tasks/{entity}/ignore`
- `taskStatusStore.resetStatus(entityName)` → `DELETE /projects/{name}/tasks/{entity}`
- `taskStatusStore.refresh()` → `GET /projects/{name}/tasks`

## Auto-Refresh

Consider adding auto-refresh when entities are validated or previewed:
```typescript
// After validation
await validationStore.validateEntity(entityName)
await taskStatusStore.refresh() // Update task status

// After preview
await shapeshiftService.previewEntity(entityName)
await taskStatusStore.refresh() // Update preview_available status
```

## Error Handling

The store handles errors internally and sets `taskStatusStore.error`:
```vue
<v-alert v-if="taskStatusStore.error" type="error" dismissible>
  {{ taskStatusStore.error }}
</v-alert>
```

## Testing Checklist

Before merging:
1. ✅ Verify task status badges appear on graph nodes
2. ✅ Test context menu actions (mark complete, ignore, reset)
3. ✅ Verify filter panel shows correct counts
4. ✅ Test filter switching (all/todo/done/ignored/blocked/critical)
5. ✅ Verify completion stats update correctly
6. ✅ Test with no task data (null handling)
7. ✅ Test error states (API failures)
8. ✅ Verify graph re-renders after status changes

## Stage 3 Considerations

For future enhancements:
- Bulk operations (mark multiple entities)
- Keyboard shortcuts (Ctrl+D for done, Ctrl+I for ignore)
- Task history/undo
- Export task completion report
- Integration with project templates
