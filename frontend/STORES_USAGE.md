# Pinia Stores - Usage Guide

Sprint 4.2 deliverable: Three Pinia stores for managing application state.

## Stores Created

### 1. Project Store (`stores/project.ts`)

Manages project CRUD operations, validation, and backups.

**State:**
- `projects: ProjectMetadata[]` - List of all projects
- `selectedProject: Project | null` - Currently selected project
- `validationResult: ValidationResult | null` - Last validation result
- `backups: BackupInfo[]` - Available§ backups
- `loading: boolean` - Loading state
- `error: string | null` - Error message
- `hasUnsavedChanges: boolean` - Unsaved changes flag

**Getters:**
- `sortedProjects` - Alphabetically sorted projects
- `projectByName(name)` - Find project by name
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
  options: projectOptions,
})

// Validate
await projectStore.validateProject('my-project')
console.log(`Errors: ${projectStore.errorCount}`)

// Backup operations
await projectStore.fetchBackups('my-project')
await projectStore.restoreBackup('my-project', backupPath)
```

### 2. Entity Store (`stores/entity.ts`)

Manages entity operations within a project.

**State:**
- `entities: EntityResponse[]` - List of entities
- `selectedEntity: EntityResponse | null` - Currently selected entity
- `currentProjectName: string | null` - Current project name
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
- `fetchEntities(projectName)` - Load all entities
- `selectEntity(projectName, entityName)` - Load specific entity
- `createEntity(projectName, data)` - Create new entity
- `updateEntity(projectName, entityName, data)` - Update entity
- `deleteEntity(projectName, entityName)` - Delete entity
- `markAsChanged()` - Mark as unsaved
- `clearError()` - Clear error state
- `reset()` - Reset store

**Usage Example:**
```typescript
import { useEntityStore } from '@/stores'

const entityStore = useEntityStore()

// Fetch entities for a project
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
- `validateProject(projectName)` - Validate entire project
- `validateEntity(projectName, entityName)` - Validate single entity
- `fetchDependencies(projectName)` - Get dependency graph
- `checkCircularDependencies(projectName)` - Check for cycles
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

// Validate project
await validationStore.validateProject('my-config')
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
api.projects.list()
api.entities.create(projectName, data)
api.validation.getDependencies(projectName)
```

## Store Export

All stores are exported from `stores/index.ts`:

```typescript
import { useProjectStore, useEntityStore, useValidationStore } from '@/stores'

// Use in components
const projectStore = useProjectStore()
const entityStore = useEntityStore()
const validationStore = useValidationStore()
```

## Next Steps (Sprint 4.3)

Create Vue composables that wrap these stores for use in components:
- `useProjects` - Auto-fetch projects
- `useEntities` - Auto-fetch entities for selected project
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
