# Entity State Management During Editing

## Architecture Overview

Entity state during editing in Shape Shifter follows a **three-layer architecture**:

**1. Frontend State Layer (Pinia Store)**
- [entity.ts](../frontend/src/stores/entity.ts) - Reactive Vue state management
- In-memory cache of entities with change tracking

**2. API Layer**
- [entities.ts](../frontend/src/api/entities.ts) - REST API client
- [entities.py](../backend/app/api/v1/endpoints/entities.py) - FastAPI endpoints

**3. Persistence Layer**
- [config_service.py](../backend/app/services/config_service.py) - File system operations
- YAML configuration files on disk

---

## State Flow During Entity Editing

### 1. **Loading Entities** (Configuration → Frontend)

```
YAML File → ConfigService.load_configuration() 
         → API GET /configurations/{name}/entities 
         → entityStore.fetchEntities() 
         → entities.value (reactive state)
```

**Backend** ([config_service.py](../backend/app/services/config_service.py)):
```python
def load_configuration(self, config_name: str) -> Config:
    config_path = self.get_config_path(config_name)
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(
        name=config_name,
        entities=data.get("entities", {}),
        options=data.get("options", {}),
        metadata=metadata,
    )
```

**Frontend** ([entity.ts](../frontend/src/stores/entity.ts)):
```typescript
async function fetchEntities(configName: string) {
  loading.value = true
  currentConfigName.value = configName
  try {
    entities.value = await api.entities.list(configName)
  } finally {
    loading.value = false
  }
}
```

### 2. **Editing State** (Frontend Only - Optimistic UI)

When a user edits an entity in the UI:

**Entity Store State** ([entity.ts](../frontend/src/stores/entity.ts)):
```typescript
const entities = ref<EntityResponse[]>([])        // All entities
const selectedEntity = ref<EntityResponse | null>(null)  // Currently editing
const hasUnsavedChanges = ref(false)              // Change tracking
```

**Change Tracking**:
```typescript
function markAsChanged() {
  hasUnsavedChanges.value = true
}
```

The edited state is **held in memory only** - no automatic saves occur.

### 3. **Saving Changes** (Frontend → Backend → Disk)

```
User clicks "Save" 
  → entityStore.updateEntity() 
  → API PUT /configurations/{name}/entities/{entity_name}
  → config_service.update_entity_by_name()
  → YAML file updated on disk
  → Updated entity returned
  → Store state synchronized
```

**Backend Persistence** ([config_service.py](../backend/app/services/config_service.py)):
```python
def update_entity_by_name(self, config_name: str, entity_name: str, entity_data: dict):
    config = self.load_configuration(config_name)  # 1. Load current state
    
    if entity_name not in config.entities:
        raise EntityNotFoundError(f"Entity '{entity_name}' not found")
    
    config.entities[entity_name] = entity_data      # 2. Update in-memory
    self.save_configuration(config)                 # 3. Write to YAML
    logger.info(f"Updated entity '{entity_name}'")
```

**Frontend Update** ([entity.ts](../frontend/src/stores/entity.ts)):
```typescript
async function updateEntity(configName: string, entityName: string, data: EntityUpdateRequest) {
  try {
    const entity = await api.entities.update(configName, entityName, data)
    
    // Sync local store with server response
    const index = entities.value.findIndex(e => e.name === entityName)
    if (index !== -1) {
      entities.value[index] = entity
    }
    
    selectedEntity.value = entity
    hasUnsavedChanges.value = false  // Reset change flag
    return entity
  } catch (err) {
    error.value = 'Failed to update entity'
    throw err
  }
}
```

---

## Key State Management Patterns

### **1. Single Source of Truth**
- YAML files on disk are the **authoritative source**
- Backend always loads from disk before modifications
- No in-memory caching on backend (stateless)

### **2. Optimistic UI Updates**
- Frontend displays edited state immediately
- Changes marked but not persisted until explicit save
- `hasUnsavedChanges` flag tracks dirty state

### **3. Atomic Operations**
- Each entity operation is atomic:
  - Load → Modify → Save cycle
  - File locking prevents concurrent writes
- No transaction management needed (single-file updates)

### **4. State Synchronization**
```typescript
// After successful save, store reflects server response
const index = entities.value.findIndex(e => e.name === entityName)
entities.value[index] = serverResponse  // Replace with authoritative data
```

---

## Entity Data Structure

**Frontend Type** ([entities.ts](../frontend/src/api/entities.ts)):
```typescript
interface EntityResponse {
  name: string
  entity_data: Record<string, unknown>  // Flexible entity config
}
```

**Backend Model** ([entities.py](../backend/app/api/v1/endpoints/entities.py)):
```python
class EntityResponse(BaseModel):
    name: str
    entity_data: dict[str, Any]  # Maps to YAML entity config
```

**YAML Structure**:
```yaml
entities:
  sample_type:
    name: sample_type
    type: sql
    data_source: sead
    query: SELECT * FROM sample_type
    surrogate_id: sample_type_id
    keys: [sample_type_name]
    columns: [sample_type_id, sample_type_name, description]
```

---

## Change Tracking & Validation

### **Unsaved Changes Warning**
```typescript
const hasUnsavedChanges = computed(() => store.hasUnsavedChanges)

// Component can check before navigation
if (hasUnsavedChanges.value) {
  confirm("You have unsaved changes. Discard?")
}
```

### **Validation Integration**
The entity store works alongside [validation.ts](../frontend/src/stores/validation.ts) store:

```typescript
// After entity save, trigger validation
await entityStore.updateEntity(config, name, data)
await validationStore.validateEntity(config, name)
```

---

## Error Handling

**Backend Errors** ([config_service.py](../backend/app/services/config_service.py)):
```python
class ConfigurationNotFoundError(Exception): pass
class EntityNotFoundError(Exception): pass
class EntityAlreadyExistsError(Exception): pass
```

**Frontend Error State** ([entity.ts](../frontend/src/stores/entity.ts)):
```typescript
const error = ref<string | null>(null)

// Displayed in UI components
<v-alert v-if="error" type="error">{{ error }}</v-alert>
```

---

## Composable Pattern

The `useEntities` composable ([useEntities.ts](../frontend/src/composables/useEntities.ts)) provides a clean API wrapper:

```typescript
export function useEntities(options: UseEntitiesOptions) {
  const store = useEntityStore()
  
  // Auto-fetch on mount if enabled
  onMounted(async () => {
    if (autoFetch && !initialized.value) {
      await fetch()
    }
  })
  
  return {
    // State
    entities,
    selectedEntity,
    hasUnsavedChanges,
    // Actions
    fetch,
    select,
    create,
    update,
    remove,
    markAsChanged,
  }
}
```

**Usage in Components**:
```vue
<script setup lang="ts">
const { entities, update, hasUnsavedChanges } = useEntities({
  configName: computed(() => configStore.currentConfigName || ''),
  autoFetch: true
})

async function saveEntity() {
  await update(entityName, updatedData)
  // State automatically synchronized
}
</script>
```

---

## Best Practices

1. **Always check `hasUnsavedChanges` before navigation**
   - Prevents data loss from accidental navigation
   - Prompt user to save or discard changes

2. **Validate after save** to ensure data integrity
   ```typescript
   await entityStore.updateEntity(config, name, data)
   await validationStore.validateEntity(config, name)
   ```

3. **Handle network failures** gracefully
   - Show error messages to users
   - Implement retry logic for transient failures
   - Keep local state until successful save

4. **Use the composable** (`useEntities`) for consistent patterns
   - Encapsulates common operations
   - Provides lifecycle management
   - Reduces boilerplate in components

5. **Clear error state** after user acknowledges
   ```typescript
   entityStore.clearError()
   ```

6. **Refresh entity list** after modifications
   ```typescript
   await refetchEntities()
   ```

---

## Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User loads configuration                                  │
│    GET /configurations/{name}/entities                       │
│    └─→ entities.value populated                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. User selects entity for editing                          │
│    selectedEntity.value = entity                             │
│    hasUnsavedChanges.value = false                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. User makes changes in form                                │
│    @input → markAsChanged()                                  │
│    hasUnsavedChanges.value = true                           │
│    (changes held in memory only)                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. User clicks "Save"                                        │
│    PUT /configurations/{name}/entities/{entity_name}         │
│    Backend: load → modify → save YAML                       │
│    Frontend: sync store with response                        │
│    hasUnsavedChanges.value = false                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Optional: Trigger validation                             │
│    POST /configurations/{name}/validate                      │
│    Display validation results                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [BACKEND_API.md](BACKEND_API.md) - REST API endpoint reference
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) - Entity configuration syntax
- [SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md) - Overall architecture

The architecture ensures data consistency while providing responsive UI through optimistic updates and explicit save actions.
