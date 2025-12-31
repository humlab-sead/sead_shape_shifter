# Pinia Stores - Usage Guide

Sprint 4.2 deliverable: Three Pinia stores for managing application state.

## Stores Created

### 1. Project Store (`stores/configuration.ts`)

Manages configuration CRUD operations, validation, and backups.

**State:**
- `projects: ConfigMetadata[]` - List of all projects
- `selectedProject: Project | null` - Currently selected project
- `validationResult: ValidationResult | null` - Last validation result
- `backups: BackupInfo[]` - Available§ backups
- `loading: boolean` - Loading state
- `error: string | null` - Error message
- `hasUnsavedChanges: boolean` - Unsaved changes flag

**Getters:**
- `sortedProjects` - Alphabetically sorted configurations
- `configByName(name)` - Find configuration by name
- `hasErrors` - Whether validation has errors
- `hasWarnings` - Whether validation has warnings

**Actions:**
- `fetchProjects()` - Load all projects
- `selectProject(name)` - Load specific project
- `createProject(data)` - Create new project
- `updateProject(name, data)` - Update project
- `deleteProject(name)` - Delete project
- `validateProject(name)` - Validate project
- `fetchBackups(name)` - List backups
- `restoreBackup(name, backupPath)` - Restore from backup
- `markAsChanged()` - Mark as unsaved
- `clearError()` - Clear error state
- `clearValidation()` - Clear validation results
- `reset()` - Reset store

**Usage Example:**
```typescript
import { useProjectStore } from '@/stores'

const projectStore = useProjectStore()

// Fetch all projects
await projectStore.fetchProjects()

// Select a project
await projectStore.selectProject('my-project')

// Create new project
await projectStore.createProject({
  name: 'new-project',
  entities: {},
})

// Update project
await projectStore.updateProject('my-project', {
  entities: updatedEntities,
  options: configOptions,
})

// Validate
await configStore.validateConfiguration('my-config')
console.log(`Errors: ${configStore.errorCount}`)

// Backup operations
await projectStore.fetchBackups('my-project')
await projectStore.restoreBackup('my-project', backupPath)
```

### 2. Entity Store (`stores/entity.ts`)

Manages entity operations within a configuration.

**State:**
- `entities: EntityResponse[]` - List of entities
- `selectedEntity: EntityResponse | null` - Currently selected entity
- `currentConfigName: string | null` - Current configuration name
- `loading: boolean` - Loading state
- `error: string | null` - Error message
- `hasUnsavedChanges: boolean` - Unsaved changes flag

**Getters:**
- `entitiesByType` - Entities grouped by type (data/sql/fixed)
- `entityCount` - Total number of entities
- `sortedEntities` - Alphabetically sorted entities
- `entityByName(name)` - Find entity by name
- `rootEntities` - Entities with no source (root entities)
- `childrenOf(parentName)` - Child entities of parent
- `hasForeignKeys(entityName)` - Whether entity has foreign keys

**Actions:**
- `fetchEntities(configName)` - Load all entities
- `selectEntity(configName, entityName)` - Load specific entity
- `createEntity(configName, data)` - Create new entity
- `updateEntity(configName, entityName, data)` - Update entity
- `deleteEntity(configName, entityName)` - Delete entity
- `markAsChanged()` - Mark as unsaved
- `clearError()` - Clear error state
- `reset()` - Reset store

**Usage Example:**
```typescript
import { useEntityStore } from '@/stores'

const entityStore = useEntityStore()

// Fetch entities for a configuration
await entityStore.fetchEntities('my-config')

// Get entities by type
const dataEntities = entityStore.entitiesByType['data']
const sqlEntities = entityStore.entitiesByType['sql']

// Select an entity
await entityStore.selectEntity('my-config', 'sample')

// Create entity
await entityStore.createEntity('my-config', {
  name: 'new_entity',
  entity_data: {
    type: 'data',
    keys: ['id'],
    columns: ['id', 'name'],
  },
})

// Update entity
await entityStore.updateEntity('my-config', 'new_entity', {
  entity_data: {
    type: 'data',
    keys: ['id', 'code'],
    columns: ['id', 'code', 'name', 'description'],
  },
})

// Check dependencies
const children = entityStore.childrenOf('sample')
const hasFK = entityStore.hasForeignKeys('sample')
```

### 3. Validation Store (`stores/validation.ts`)

Manages validation results and dependency graph analysis.

**State:**
- `validationResult: ValidationResult | null` - Project validation result
- `entityValidationResults: Map<string, ValidationResult>` - Per-entity validation
- `dependencyGraph: DependencyGraph | null` - Dependency graph
- `circularDependencyCheck: CircularDependencyCheck | null` - Cycle check result
- `loading: boolean` - Loading state
- `error: string | null` - Error message

**Getters:**
- `hasErrors` - Whether validation has errors
- `hasWarnings` - Whether validation has warnings
- `errorCount` - Number of errors
- `warningCount` - Number of warnings
- `errors` - List of errors
- `warnings` - List of warnings
- `allMessages` - All validation messages
- `messagesBySeverity` - Messages grouped by severity
- `messagesByEntity` - Messages grouped by entity
- `hasCircularDependencies` - Whether graph has cycles
- `cycles` - List of circular dependency paths
- `cycleCount` - Number of cycles
- `topologicalOrder` - Processing order
- `isValid` - Overall validity

**Actions:**
- `validateConfiguration(configName)` - Validate entire configuration
- `validateEntity(configName, entityName)` - Validate single entity
- `fetchDependencies(configName)` - Get dependency graph
- `checkCircularDependencies(configName)` - Check for cycles
- `getEntityValidation(entityName)` - Get entity validation result
- `hasEntityErrors(entityName)` - Check entity errors
- `hasEntityWarnings(entityName)` - Check entity warnings
- `clearValidation()` - Clear validation results
- `clearDependencies()` - Clear dependency data
- `clearError()` - Clear error state
- `reset()` - Reset store

**Usage Example:**
```typescript
import { useValidationStore } from '@/stores'

const validationStore = useValidationStore()

// Validate configuration
await validationStore.validateConfiguration('my-config')
console.log(`Valid: ${validationStore.isValid}`)
console.log(`Errors: ${validationStore.errorCount}`)
console.log(`Warnings: ${validationStore.warningCount}`)

// Get validation messages
validationStore.errors.forEach((error) => {
  console.log(`[${error.entity}] ${error.message}`)
})

// Validate single entity
await validationStore.validateEntity('my-config', 'sample')
const entityResult = validationStore.getEntityValidation('sample')

// Get messages grouped by entity
const messagesByEntity = validationStore.messagesByEntity
Object.entries(messagesByEntity).forEach(([entity, messages]) => {
  console.log(`${entity}: ${messages.length} issues`)
})

// Dependency analysis
await validationStore.fetchDependencies('my-config')
console.log(`Processing order: ${validationStore.topologicalOrder}`)

if (validationStore.hasCircularDependencies) {
  validationStore.cycles.forEach((cycle) => {
    console.log(`Cycle: ${cycle.join(' -> ')}`)
  })
}

// Quick cycle check (lighter than full graph)
await validationStore.checkCircularDependencies('my-config')
console.log(`Cycles found: ${validationStore.cycleCount}`)
```

## Integration with API Client

All stores use the API client from Sprint 4.1:

```typescript
import { api } from '@/api'

// Stores internally call:
api.configurations.list()
api.entities.create(configName, data)
api.validation.getDependencies(configName)
```

## Store Export

All stores are exported from `stores/index.ts`:

```typescript
import { useConfigurationStore, useEntityStore, useValidationStore } from '@/stores'

// Use in components
const configStore = useConfigurationStore()
const entityStore = useEntityStore()
const validationStore = useValidationStore()
```

## Next Steps (Sprint 4.3)

Create Vue composables that wrap these stores for use in components:
- `useConfigurations` - Auto-fetch configurations
- `useEntities` - Auto-fetch entities for selected config
- `useValidation` - Reactive validation on changes
- `useDependencies` - Dependency graph visualization data

## Architecture Flow

```
Component
  ↓
Composable (Sprint 4.3)
  ↓
Pinia Store (Sprint 4.2) ← Current
  ↓
API Client (Sprint 4.1)
  ↓
Backend REST API
```
