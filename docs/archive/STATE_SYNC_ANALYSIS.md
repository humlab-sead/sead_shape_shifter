# State Synchronization Analysis & Recommendations

## Problem Description

When editing an entity's YAML and saving:
1. Changes are saved to the project YAML file ✅
2. The entity store is updated with the new data ✅  
3. **BUT** when reopening the entity editor, it shows the OLD state ❌

## Root Cause Analysis

### Current Data Flow

```
User edits YAML → Save → API Update → Store Update → Dialog Closes
                                              ↓
                                        entities[index] = newEntity
                                        selectedEntity = newEntity

User clicks Edit again → EntityListCard finds entity → Opens dialog with entity prop
                                ↓
                            Uses stale entity from entities array
```

### The Problem

**EntityFormDialog watches `props.entity` to populate `formData`:**

```typescript
// EntityFormDialog.vue lines 1610-1623
watch(
  () => props.entity,
  (newEntity) => {
    if (newEntity && props.mode === 'edit') {
      formData.value = buildFormDataFromEntity(newEntity)
    } else if (props.mode === 'create') {
      formData.value = buildDefaultFormData()
    }
  },
  { immediate: true }
)
```

**EntityListCard passes entity from its local `entities` computed:**

```typescript
// EntityListCard.vue line 154
const { entities, loading, error, remove } = useEntities({
  projectName: props.projectName,
  autoFetch: true,
})

// Line 160-167 - Handles external edit requests
watch(
  () => props.entityToEdit,
  (entityName) => {
    if (entityName) {
      const entity = entities.value?.find((e) => e.name === entityName)
      if (entity) {
        handleEditEntity(entity)
      }
    }
  }
)
```

**The Issue:**
- `entities` is computed from `store.sortedEntities`
- When the store updates `entities[index]`, Vue's reactivity SHOULD trigger
- But the `entity` prop passed to EntityFormDialog is a **reference to the old object**
- The watcher sees the same object reference and doesn't re-trigger `buildFormDataFromEntity`

### Reactivity Chain

```
Store Update Flow:
updateEntity() → entities.value[index] = entity
                       ↓
                   Reactive update
                       ↓
           useEntities().entities computed updates
                       ↓
           EntityListCard.entities updates
                       ↓
           ??? formData.value should update ???
                       ↓
           BUT: prop.entity is same object reference
                watch doesn't fire
```

## Why This Happens

1. **Object Identity Problem:**
   - Vue's reactivity tracks object mutations, but watchers use `===` comparison by default
   - When `entities[index] = entity`, the array updates, but the entity **object** is new
   - However, if the watcher already fired with entity A, and we pass entity A again (even modified), it won't re-fire
   
2. **Watch Timing Issue:**
   - The watch on `props.entity` fires `immediate: true` when dialog opens
   - When entity updates in store, the prop updates, but watcher doesn't see it as "new"

3. **Deep Watch Missing:**
   - The watcher should use `{ deep: true }` to detect nested changes
   - OR force re-evaluation when dialog opens

## Recommended Solutions

### Solution 1: Force Fresh Fetch on Dialog Open ⭐ (Most Robust)

**Changes to EntityFormDialog.vue:**

```typescript
// Watch modelValue (dialog open/close) to fetch fresh entity data
watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen && props.mode === 'edit' && props.entity?.name) {
      // Fetch fresh entity data from API
      try {
        const freshEntity = await api.entities.get(props.projectName, props.entity.name)
        formData.value = buildFormDataFromEntity(freshEntity)
        
        // Initialize YAML content from fresh data
        yamlContent.value = formDataToYaml()
      } catch (err) {
        error.value = 'Failed to load entity data'
        console.error(err)
      }
    } else if (props.mode === 'create' && isOpen) {
      formData.value = buildDefaultFormData()
      yamlContent.value = ''
    }
  }
)
```

**Pros:**
- ✅ Always guaranteed to have fresh data from source of truth (YAML file)
- ✅ Simple, explicit, and predictable
- ✅ No reliance on reactive chains
- ✅ Works even if store is stale

**Cons:**
- ⚠️ Extra API call on dialog open (negligible performance cost)
- ⚠️ Requires API import in component

### Solution 2: Deep Watch with Forced Update

**Changes to EntityFormDialog.vue:**

```typescript
// Replace current entity watcher
watch(
  () => props.entity,
  (newEntity) => {
    if (newEntity && props.mode === 'edit') {
      formData.value = buildFormDataFromEntity(newEntity)
    } else if (props.mode === 'create') {
      formData.value = buildDefaultFormData()
    }
  },
  { immediate: true, deep: true }  // Add deep: true
)

// ALSO add a dialog-open watcher to force refresh
watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen && props.mode === 'edit' && props.entity) {
      // Force rebuild even if entity hasn't "changed"
      formData.value = buildFormDataFromEntity(props.entity)
      yamlContent.value = formDataToYaml()
    }
  }
)
```

**Pros:**
- ✅ No extra API calls
- ✅ Works with existing store architecture

**Cons:**
- ⚠️ Deep watchers can be expensive
- ⚠️ Still relies on store reactivity chain
- ⚠️ Could trigger multiple times unnecessarily

### Solution 3: Use Entity Name as Key

**Changes to EntityListCard.vue:**

```vue
<entity-form-dialog
  :key="`edit-${selectedEntity?.name}-${editTrigger}`"
  v-model="showFormDialog"
  :project-name="projectName"
  :entity="selectedEntity"
  :mode="dialogMode"
  @saved="handleEntitySaved"
/>
```

```typescript
const editTrigger = ref(0)

function handleEditEntity(entity: EntityResponse) {
  selectedEntity.value = entity
  dialogMode.value = 'edit'
  editTrigger.value++  // Force component recreation
  showFormDialog.value = true
}
```

**Pros:**
- ✅ Forces complete component recreation with fresh props
- ✅ Simple to implement

**Cons:**
- ⚠️ Destroys and recreates entire component (expensive)
- ⚠️ Loses any temporary state (not an issue here)
- ⚠️ Overkill for this problem

### Solution 4: Store Version Tracking

**Changes to entity.ts store:**

```typescript
const entityVersions = ref<Record<string, number>>({})

async function updateEntity(projectName: string, entityName: string, data: EntityUpdateRequest) {
  // ... existing code ...
  
  // Increment version to force reactivity
  entityVersions.value[entityName] = (entityVersions.value[entityName] || 0) + 1
  
  return entity
}
```

**Changes to EntityFormDialog:**

```typescript
const entityVersion = computed(() => {
  if (!props.entity?.name) return 0
  return entityStore.entityVersions[props.entity.name] || 0
})

watch(
  entityVersion,
  () => {
    if (props.mode === 'edit' && props.entity) {
      formData.value = buildFormDataFromEntity(props.entity)
      yamlContent.value = formDataToYaml()
    }
  }
)
```

**Pros:**
- ✅ Explicit version tracking
- ✅ No API calls
- ✅ Lightweight

**Cons:**
- ⚠️ Adds complexity to store
- ⚠️ Extra state to maintain

## Recommendation: Solution 1 (Fresh Fetch)

**Rationale:**
1. **Robustness**: Always gets data from source of truth (YAML file via API)
2. **Simplicity**: Clear, explicit, easy to understand
3. **Performance**: One API call on dialog open is negligible
4. **Reliability**: No dependency on complex reactive chains
5. **Future-proof**: Works even if store caching changes

**Implementation Priority:**
1. Add fresh fetch on dialog open (Solution 1)
2. Remove duplicate entity watcher logic  
3. Add loading state during fetch
4. Add error handling

## Additional Improvements

### 1. Consolidate Watchers

Current code has THREE watchers that rebuild formData:
- Line 1610: `watch(() => props.entity, ...)`
- Line 1623: `watch(() => props.modelValue, ...)`  (partial rebuild)

Should consolidate into ONE authoritative watcher on dialog open.

### 2. Add Loading State

```typescript
const initializing = ref(false)

watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen && props.mode === 'edit' && props.entity?.name) {
      initializing.value = true
      try {
        const freshEntity = await api.entities.get(props.projectName, props.entity.name)
        formData.value = buildFormDataFromEntity(freshEntity)
        yamlContent.value = formDataToYaml()
      } catch (err) {
        error.value = 'Failed to load entity data'
      } finally {
        initializing.value = false
      }
    }
  }
)
```

### 3. Prevent Editing During Load

```vue
<v-form ref="formRef" v-model="formValid" :disabled="initializing">
```

## Testing Plan

1. **Test: Edit entity YAML, save, reopen**
   - Edit entity via YAML tab
   - Save changes
   - Close dialog
   - Reopen entity
   - Verify: Form shows updated data
   - Verify: YAML tab shows updated data

2. **Test: Edit entity form, save, reopen**
   - Edit entity via form fields
   - Save changes
   - Close dialog
   - Reopen entity
   - Verify: Form shows updated data

3. **Test: Multiple sequential edits**
   - Edit entity A, save
   - Edit entity B, save
   - Reopen entity A
   - Verify: Shows entity A's data (not entity B)

4. **Test: Error handling**
   - Simulate API error during fetch
   - Verify: Error message shown
   - Verify: Dialog doesn't show corrupted data

## Conclusion

The current state synchronization relies on Vue's reactivity propagating through:
- Store → Composable → Component → Prop → Watcher

This chain is fragile. **Fetching fresh data on dialog open** is more robust and aligns with the principle that the YAML file is the source of truth.

**Cost**: One extra API GET request per entity edit (~10-50ms)  
**Benefit**: Guaranteed data consistency, simpler code, fewer bugs
