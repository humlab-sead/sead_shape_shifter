# Task List Feature Proposal

**Date:** January 15, 2026  
**Status:** Proposal - Simplified Design  
**Effort Estimate:** ~5 days  
**Priority:** High Value / Moderate Effort

---

## Executive Summary

This proposal outlines a **simplified, graph-centric task tracking system** for Shape Shifter entities. The feature provides progress visibility and workflow guidance without enforcing work order, using visual badges on the dependency graph as the primary UI.

**Key simplifications from original spec:**
- 3 statuses instead of 5 (done, todo, ignored)
- Derive blocked/in-progress automatically (don't store)
- Graph visualization only (no separate task list sidebar)
- Use dependency graph for suggested order
- Minimal YAML extension

---

## Value vs Effort Analysis

### Value: HIGH ⭐⭐⭐⭐

**Addresses real UX pain points:**
- Progress visibility for complex projects
- Cognitive load reduction (users don't have to remember what's done)
- Guided workflow without enforcement
- Especially valuable for teams and domain-specific templates

### Effort: MODERATE ⚙️⚙️⚙️

**Original estimate:** 6-8 days  
**Simplified estimate:** ~5 days

- Backend: 2 days (model extension, status derivation logic, API endpoints)
- Frontend: 2 days (UI component, graph integration, status updates)
- Testing: 1 day

### ROI: Excellent ✅

High value for moderate effort makes this worthwhile.

---

## Key Simplifications

### 1. Simplify Status Model (5 → 3 States)

**Problem with original proposal:**
- Too many states: `pending`, `in_progress`, `blocked`, `ignored`, `done`
- Storing derived states creates sync issues

**Simplified model:**

| Status | Meaning | Source |
|--------|---------|--------|
| `todo` | Not complete yet | **Derived** (not marked done) |
| `done` | Validation passed, user confirmed | **Stored** (user action) |
| `ignored` | Explicitly excluded | **Stored** (user action) |

**Derive other signals automatically:**
- **In progress** → Entity exists but not done (derived from entity list)
- **Blocked** → Has validation errors or dependency issues (derived from validation)
- **Pending** → Entity doesn't exist yet (derived from entity list)

**Benefits:**
- Simpler mental model
- No status sync problems
- Less UI clutter
- Faster to implement

---

### 2. Streamline YAML Structure

**Original proposal:**
```yaml
task_list:
  mandatory_entities: [site, location, sample]
  suggested_order: [location, site, sample]
  status:
    done: [location]
    in_progress: [site]
    pending: [sample]
    blocked: []
    ignored: []
```

**Problems:**
- Duplication (entity listed 2-3 times)
- Storing derived state (`pending`, `in_progress`)
- `mandatory_entities` and `suggested_order` overlap

**Simplified proposal (Option A - Minimal):**
```yaml
task_list:
  required_entities: [location, site, sample]
  completed: [location]
  ignored: []
```

**Simplified proposal (Option B - With Order):**
```yaml
task_list:
  entities:
    - name: location
      required: true
      order: 1
    - name: site
      required: true
      order: 2
    - name: sample
      required: false
      order: 3
  
  completed: [location]
  ignored: []
```

**Recommendation:** Start with **Option A** (minimal). Let dependency graph provide suggested order automatically. Add explicit ordering later if users request it.

**Benefits:**
- Single source of truth per entity
- Only store user intent, derive the rest
- Easier to maintain
- More compact

---

### 3. Graph-First UI Approach

**Original proposal suggested 4 UI options:**
- Sidebar
- Overlay
- Entity list enhancement
- Dependency graph

**Recommendation: Graph Integration Only (MVP)**

**Phase 1 - Visual Badges on Dependency Graph:**

Add **status badges to nodes**:
- ✅ Green checkmark = done
- ⚠️ Yellow warning = has validation issues
- 🔴 Red dot = required but missing
- ⚪ Gray = todo (exists but not done)
- 🚫 Strikethrough = ignored

Add **node border styling**:
- Thick border = required entity
- Dashed border = optional

**Phase 2 - If users request:**
- Collapsible sidebar with checklist view
- Filtering controls

**Why graph-first:**
- Users already use graph for navigation
- Non-intrusive (just enhances existing view)
- Visual indicators are faster to scan than a list
- Aligns with other graph-centric UX improvements (#153, #156, #157)

---

### 4. Auto-Derive "Blocked" State

**Don't let users manually mark entities as blocked.**

**Instead, derive blocked status from:**
1. Entity has validation errors
2. Required dependency has validation errors
3. Required dependency doesn't exist yet
4. Preview generation fails

**Show in UI:**
- Tooltip on graph node: "Blocked: Site Type entity has errors"
- Clicking shows validation details
- Link to dependency causing the block

**Benefits:**
- Always accurate (can't be stale)
- Less user maintenance
- More actionable (links to actual problem)

---

### 5. Priority Indicators (Instead of Strict Order)

Rather than enforcing `suggested_order`, show **smart suggestions**.

**Priority algorithm:**
1. **Critical** (🔴 red flag): Required entity missing or has errors
2. **Ready** (🟢 green flag): All dependencies done, validation passes
3. **Waiting** (🟡 yellow): Has incomplete dependencies
4. **Optional** (⚪ gray): Not required, no blockers

**Show in graph:**
- Node badge shows priority level
- Tooltip explains why ("Ready: dependencies complete")
- Filter to show only "Ready" entities

**Benefits:**
- More dynamic than static order
- Adapts to user's actual workflow
- Highlights bottlenecks automatically

---

## Revised Minimal Feature Spec (MVP)

### Backend Changes

**1. Add `TaskList` to project model** (`src/model.py`):
```python
from typing import Optional
from pydantic import BaseModel, Field

class TaskList(BaseModel):
    """Optional task tracking for entities."""
    required_entities: list[str] = Field(
        default_factory=list,
        description="Entities that must be completed"
    )
    completed: list[str] = Field(
        default_factory=list,
        description="Entities marked as done by user"
    )
    ignored: list[str] = Field(
        default_factory=list,
        description="Entities explicitly excluded from project"
    )

class ShapeShiftProject(BaseModel):
    # ... existing fields ...
    task_list: Optional[TaskList] = Field(
        default=None,
        description="Optional task progress tracking"
    )
```

**2. Add computed endpoint** (`backend/app/api/v1/endpoints/tasks.py`):
```python
from fastapi import APIRouter, HTTPException
from backend.app.services.task_service import TaskService

router = APIRouter()

@router.get("/projects/{name}/task-status")
async def get_task_status(name: str):
    """Compute full task status from project + validation state."""
    service = TaskService()
    return await service.compute_status(name)

@router.post("/projects/{name}/tasks/{entity_name}/complete")
async def mark_task_complete(name: str, entity_name: str):
    """Mark entity as done (requires validation pass)."""
    service = TaskService()
    return await service.mark_complete(name, entity_name)

@router.post("/projects/{name}/tasks/{entity_name}/ignore")
async def ignore_task(name: str, entity_name: str):
    """Mark entity as ignored."""
    service = TaskService()
    return await service.mark_ignored(name, entity_name)

@router.delete("/projects/{name}/tasks/{entity_name}")
async def reset_task(name: str, entity_name: str):
    """Remove task status (reset to todo)."""
    service = TaskService()
    return await service.reset_status(name, entity_name)
```

**3. Add service** (`backend/app/services/task_service.py`):
```python
class TaskService:
    async def compute_status(self, project_name: str) -> dict:
        """
        Compute full task status for all entities.
        
        Returns dict mapping entity_name to:
        {
            "status": "done" | "todo" | "ignored",
            "priority": "critical" | "ready" | "waiting" | "optional",
            "required": bool,
            "exists": bool,
            "validation_passed": bool,
            "preview_available": bool,
            "blocked_by": [entity_names],
            "issues": [error_messages],
        }
        """
        pass
    
    async def mark_complete(self, project_name: str, entity_name: str):
        """Mark entity as done (validates first)."""
        pass
    
    async def mark_ignored(self, project_name: str, entity_name: str):
        """Mark entity as ignored."""
        pass
    
    async def reset_status(self, project_name: str, entity_name: str):
        """Reset to todo state."""
        pass
```

**Validation rule:**
- Can only mark `done` if validation passes and preview succeeds

---

### Frontend Changes

**1. New composable** (`frontend/src/composables/useTaskStatus.ts`):
```typescript
export function useTaskStatus(projectName: string) {
  const status = ref<Record<string, EntityTaskStatus>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  async function fetchStatus() {
    // GET /api/v1/projects/{name}/task-status
  }
  
  async function markComplete(entityName: string) {
    // POST /api/v1/projects/{name}/tasks/{entity}/complete
  }
  
  async function markIgnored(entityName: string) {
    // POST /api/v1/projects/{name}/tasks/{entity}/ignore
  }
  
  async function resetStatus(entityName: string) {
    // DELETE /api/v1/projects/{name}/tasks/{entity}
  }
  
  return { status, loading, error, fetchStatus, markComplete, markIgnored, resetStatus }
}
```

**2. Enhance graph node component** (`frontend/src/components/DependencyGraph/GraphNode.vue`):
```vue
<template>
  <div 
    class="graph-node"
    :class="{
      'node--required': isRequired,
      'node--done': status === 'done',
      'node--blocked': priority === 'critical',
      'node--ready': priority === 'ready',
      'node--ignored': status === 'ignored'
    }"
  >
    <!-- Existing node content -->
    
    <!-- Status badge -->
    <v-badge
      :icon="statusIcon"
      :color="statusColor"
      :title="statusTooltip"
    />
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  entityName: string
  // ... other props
}>()

const { status } = useTaskStatus(projectName)

const taskStatus = computed(() => status.value[props.entityName])

const statusIcon = computed(() => {
  switch (taskStatus.value?.status) {
    case 'done': return 'mdi-check-circle'
    case 'ignored': return 'mdi-cancel'
    default: return taskStatus.value?.priority === 'critical' 
      ? 'mdi-alert-circle' 
      : 'mdi-circle-outline'
  }
})

const statusColor = computed(() => {
  if (taskStatus.value?.status === 'done') return 'success'
  if (taskStatus.value?.status === 'ignored') return 'grey'
  switch (taskStatus.value?.priority) {
    case 'critical': return 'error'
    case 'ready': return 'success'
    case 'waiting': return 'warning'
    default: return 'grey'
  }
})

const statusTooltip = computed(() => {
  const task = taskStatus.value
  if (!task) return ''
  
  if (task.status === 'done') return 'Complete'
  if (task.status === 'ignored') return 'Ignored'
  
  if (task.priority === 'critical') {
    return `Critical: ${task.issues.join(', ')}`
  }
  if (task.priority === 'ready') {
    return 'Ready to complete'
  }
  if (task.blocked_by?.length) {
    return `Waiting for: ${task.blocked_by.join(', ')}`
  }
  return 'Not started'
})
</script>
```

**3. Add to graph context menu** (`frontend/src/components/DependencyGraph/GraphContextMenu.vue`):
```vue
<template>
  <v-menu>
    <v-list>
      <!-- Existing items: Open, Preview, Duplicate, Delete -->
      
      <v-divider />
      
      <v-list-item
        v-if="canMarkComplete"
        @click="handleMarkComplete"
        prepend-icon="mdi-check"
      >
        Mark as Done
      </v-list-item>
      
      <v-list-item
        v-if="taskStatus?.status === 'done'"
        @click="handleResetStatus"
        prepend-icon="mdi-undo"
      >
        Reset Status
      </v-list-item>
      
      <v-list-item
        @click="handleIgnore"
        prepend-icon="mdi-cancel"
      >
        {{ taskStatus?.status === 'ignored' ? 'Unignore' : 'Ignore Entity' }}
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
const { status, markComplete, markIgnored, resetStatus } = useTaskStatus(projectName)

const taskStatus = computed(() => status.value[props.entityName])

const canMarkComplete = computed(() => {
  const task = taskStatus.value
  return task?.status !== 'done' 
    && task?.validation_passed 
    && task?.preview_available
})

async function handleMarkComplete() {
  await markComplete(props.entityName)
  // Refresh graph
}

async function handleIgnore() {
  if (taskStatus.value?.status === 'ignored') {
    await resetStatus(props.entityName)
  } else {
    await markIgnored(props.entityName)
  }
  // Refresh graph
}

async function handleResetStatus() {
  await resetStatus(props.entityName)
  // Refresh graph
}
</script>
```

**4. Add graph filtering** (`frontend/src/components/DependencyGraph/DependencyGraphView.vue`):
```vue
<template>
  <div class="dependency-graph-view">
    <v-toolbar density="compact">
      <!-- Existing controls -->
      
      <v-divider vertical />
      
      <v-btn-toggle v-model="statusFilter" multiple>
        <v-btn value="todo" size="small">
          <v-icon>mdi-circle-outline</v-icon> Todo
        </v-btn>
        <v-btn value="ready" size="small">
          <v-icon>mdi-check-circle</v-icon> Ready
        </v-btn>
        <v-btn value="done" size="small">
          <v-icon>mdi-check-circle</v-icon> Done
        </v-btn>
        <v-btn value="blocked" size="small">
          <v-icon>mdi-alert-circle</v-icon> Blocked
        </v-btn>
      </v-btn-toggle>
      
      <v-switch
        v-model="showRequiredOnly"
        label="Required only"
        hide-details
      />
    </v-toolbar>
    
    <GraphCanvas :entities="filteredEntities" />
  </div>
</template>

<script setup lang="ts">
const statusFilter = ref<string[]>([])
const showRequiredOnly = ref(false)

const filteredEntities = computed(() => {
  let entities = props.entities
  
  // Filter by status
  if (statusFilter.value.length > 0) {
    entities = entities.filter(e => {
      const task = status.value[e.name]
      if (statusFilter.value.includes('ready') && task?.priority === 'ready') return true
      if (statusFilter.value.includes('blocked') && task?.priority === 'critical') return true
      if (statusFilter.value.includes(task?.status)) return true
      return false
    })
  }
  
  // Filter by required
  if (showRequiredOnly.value) {
    entities = entities.filter(e => status.value[e.name]?.required)
  }
  
  return entities
})
</script>
```

---

## What NOT to Build (Keep Simple)

To maintain simplicity and avoid scope creep:

❌ Separate task list sidebar (use graph instead)  
❌ Manual "blocked" status (derive it)  
❌ Manual "in_progress" status (derive it)  
❌ Strict suggested_order field (use dependency graph)  
❌ Separate mandatory_entities list (use required flag)  
❌ Overlay/modal task list interface  
❌ Complex task filtering UI beyond graph filters

---

## Implementation Plan

### Stage 1: Core Backend (2 days)

**Tasks:**
- [ ] Add `TaskList` model to `src/model.py`
- [ ] Add `TaskService` in `backend/app/services/task_service.py`
- [ ] Implement status derivation logic (compute priority, blocked_by)
- [ ] Add API endpoints in `backend/app/api/v1/endpoints/tasks.py`
- [ ] Add validation rule: can only mark done if validation passes
- [ ] Unit tests for `TaskService`
- [ ] Integration tests for task endpoints

**Deliverables:**
- API endpoints functional
- Status computation working
- Tests passing

---

### Stage 2: Frontend UI (2 days)

**Tasks:**
- [ ] Create `useTaskStatus` composable
- [ ] Add status badge component
- [ ] Enhance graph node with status badges and styling
- [ ] Add task actions to graph context menu
- [ ] Add graph filtering controls
- [ ] Integrate with existing entity store
- [ ] Handle status updates and graph refresh

**Deliverables:**
- Visual badges on graph nodes
- Right-click actions working
- Filter controls functional

---

### Stage 3: Polish & Documentation (1 day)

**Tasks:**
- [ ] Add visual transitions when marking done
- [ ] Add helpful tooltips explaining blocked status
- [ ] Add keyboard shortcuts (optional)
- [ ] Update user documentation
- [ ] Add migration guide for existing projects
- [ ] E2E tests for complete workflow

**Deliverables:**
- Polished UX
- Documentation complete
- All tests passing

---

**Total Estimate: ~5 days**

---

## Integration with Existing Features

### Synergy with Other UX Improvements:

| Feature | Integration Point |
|---------|------------------|
| **#153 (Custom graph layout)** | Task badges enhance the custom layout |
| **#156 (Add node button)** | Created nodes default to "todo" status |
| **#157 (YAML sidebar)** | Could show task status at top of sidebar |
| **Right-click menu** | Add "Mark as done" and "Ignore entity" options |

### Natural Workflow:

1. User opens project, sees graph with status badges
2. Filters to "Show incomplete required entities"
3. Double-clicks node to edit (existing overlay feature)
4. Saves, auto-validates
5. Right-clicks "Mark as done"
6. Graph updates, next ready entity highlighted

---

## Example YAML

**Minimal project with task tracking:**

```yaml
metadata:
  name: sead-import-2026
  type: shapeshifter-project
  version: 1.0

task_list:
  required_entities:
    - location
    - site
    - sample
  completed:
    - location
  ignored: []

entities:
  location:
    source_data: csv
    # ... entity config ...
  
  site:
    source_data: csv
    depend_on: [location]
    # ... entity config ...
```

**At runtime, computed status would be:**

```json
{
  "location": {
    "status": "done",
    "priority": "ready",
    "required": true,
    "exists": true,
    "validation_passed": true,
    "preview_available": true,
    "blocked_by": [],
    "issues": []
  },
  "site": {
    "status": "todo",
    "priority": "ready",
    "required": true,
    "exists": true,
    "validation_passed": true,
    "preview_available": true,
    "blocked_by": [],
    "issues": []
  },
  "sample": {
    "status": "todo",
    "priority": "waiting",
    "required": true,
    "exists": false,
    "validation_passed": false,
    "preview_available": false,
    "blocked_by": ["site"],
    "issues": ["Entity not created"]
  }
}
```

---

## Future Enhancements (Post-MVP)

**If users request additional features:**

1. **Separate task list sidebar** - Checklist view parallel to graph
2. **Project templates** - Pre-configured task lists for common workflows
3. **Progress statistics** - "3 of 10 entities complete (30%)"
4. **Task history** - Track when entities were completed
5. **Bulk actions** - "Mark all validated entities as done"
6. **Collaboration** - Show who completed which entities
7. **Export task report** - Generate progress report for stakeholders

---

## Success Criteria

**MVP is successful if:**

1. ✅ Users can visually identify entity completion status in graph
2. ✅ Users can mark entities as done/ignored via right-click menu
3. ✅ System prevents marking incomplete entities as done
4. ✅ Users can filter graph by status (ready, blocked, done)
5. ✅ Blocked entities show clear explanation of what's blocking them
6. ✅ No performance degradation on large projects (100+ entities)
7. ✅ Feature is non-intrusive (users can ignore it completely)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| **Performance impact on large graphs** | Compute status only when needed, cache results |
| **Users expect more features** | Start minimal, iterate based on feedback |
| **Confusion about automatic status changes** | Clear tooltips and documentation |
| **Required entities list gets stale** | Make it optional, show warnings if entities removed |

---

## Conclusion

This simplified design delivers **high value with moderate effort** by:

- Reducing status model to 3 states (done, todo, ignored)
- Deriving priority and blocked state automatically
- Using graph as primary UI (no separate list)
- Leveraging existing dependency graph for ordering
- Storing only user intent, deriving everything else

The graph-centric approach aligns with Shape Shifter's existing UX patterns and provides immediate value without disrupting the current workflow.

**Recommendation: Proceed with MVP implementation (~5 days)**
