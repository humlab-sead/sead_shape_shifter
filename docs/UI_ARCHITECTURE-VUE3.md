# Configuration Editor UI - Software Architecture (Vue 3)

## 1. Executive Summary

This document defines the software architecture for the Shape Shifter Configuration Editor using **Vue 3**, a web-based UI for managing data transformation configurations. The architecture supports the phased rollout described in the requirements document, with Phase 1 focusing on entity CRUD and dependency management.

**Architecture Goals**:
- Leverage existing Python codebase (validation, YAML parsing)
- Modern, responsive web UI using Vue 3 Composition API
- Extensible for future phases (data introspection, schema guidance)
- Simple deployment and maintenance

---

## 2. System Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Browser (Client)                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          Vue 3/TypeScript Frontend                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────────┐   │ │
│  │  │  Entity  │  │  Graph   │  │    Validation      │   │ │
│  │  │  Editor  │  │  View    │  │    Reporter        │   │ │
│  │  └──────────┘  └──────────┘  └────────────────────┘   │ │
│  │  ┌────────────────────────────────────────────────┐   │ │
│  │  │         State Management (Pinia)               │   │ │
│  │  └────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST/JSON API
┌──────────────────────────┴──────────────────────────────────┐
│                    Python Backend (Server)                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                FastAPI Application                      │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────┐  │ │
│  │  │ Configuration│  │  Validation   │  │  Dependency│  │ │
│  │  │   Service    │  │   Service     │  │  Analyzer  │  │ │
│  │  └──────────────┘  └───────────────┘  └────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Existing Shape Shifter Core                   │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │ config_model │  │specifications│  │  normalizer │  │ │
│  │  │   .py        │  │    .py       │  │     .py     │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                  Filesystem / Storage                        │
│         ┌────────────────────────────────────┐                  │
│         │  Configuration Files (.yml)    │                  │
│         │  - arbodat-database.yml        │                  │
│         │  - [other configs]             │                  │
│         │  - [backups]                   │                  │
│         └────────────────────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Architecture Principles

1. **Leverage Existing Code**: Reuse validation specs, config models, and YAML processing
2. **API-First**: Clean separation between frontend and backend via REST API
3. **Progressive Enhancement**: Phase 1 foundation supports future phases without major refactoring
4. **Type Safety**: TypeScript frontend + Pydantic backend for strong typing
5. **Single Responsibility**: Clear service boundaries with focused responsibilities
6. **Stateless API**: RESTful design with no server-side session state

---

## 3. Technology Stack

### 3.1 Frontend Stack

#### Core Framework: **Vue 3 with TypeScript (Composition API)**

**Rationale**:
- **Composition API**: Better code organization and reusability than Options API
- **TypeScript Support**: First-class TypeScript integration
- **Performance**: Faster than Vue 2, comparable to React
- **Developer Experience**: Excellent tooling (Volar, Vue DevTools)
- **Team Skills**: Better Vue.js expertise available
- **Smaller Bundle**: Typically smaller than React equivalents
- **Progressive Framework**: Easy to adopt incrementally

**Why Vue 3 over React**:
- Team has better Vue.js skills
- More intuitive template syntax
- Built-in directives (v-model, v-if, v-for) reduce boilerplate
- Single File Components (.vue) provide better organization
- Less decision fatigue (official router, state management)

#### Build Tool: **Vite**

**Rationale**:
- Created by Vue.js author (Evan You)
- Fast HMR (Hot Module Replacement)
- Optimized production builds
- Official Vue 3 template available
- Native ESM support

#### UI Component Library: **Vuetify 3**

**Rationale**:
- Most mature and comprehensive Vue UI library
- Material Design implementation
- Extensive component library (150+ components)
- Accessibility built-in (WCAG 2.0 compliant)
- Active development and large community
- Excellent documentation and examples
- TypeScript support
- Responsive by default

**Alternatives Considered**:
- **Element Plus**: Good alternative, more compact design
- **Quasar**: More opinionated, includes SSR/mobile features we don't need
- **PrimeVue**: Good but smaller community
- **Naive UI**: Modern but less mature

#### State Management: **Pinia**

**Rationale**:
- **Official Vue 3 state management** (replaces Vuex)
- TypeScript-first design with excellent inference
- Composition API compatible
- Simpler API than Vuex (no mutations)
- DevTools integration
- Modular stores by design
- No string constants for actions/mutations
- SSR support (for future)

**Why Pinia over Vuex**:
- Recommended by Vue team for Vue 3
- Less boilerplate
- Better TypeScript support
- Composition API style

#### Form Management: **VeeValidate 4 + Zod**

**Rationale**:
- **VeeValidate 4**: Most popular Vue form library, Composition API support
- **Zod**: TypeScript-first schema validation, shareable with backend
- Excellent integration between the two
- Handles complex validation rules
- Built-in error messaging
- Minimal re-renders (performance)

**Alternative**: Vuelidate (lighter but less features)

#### Router: **Vue Router 4**

**Rationale**:
- Official Vue 3 router
- TypeScript support
- Composition API helpers (useRouter, useRoute)
- Nested routes support
- Navigation guards for validation

#### Graph Visualization: **Vue Flow**

**Rationale**:
- Official Vue 3 port of ReactFlow
- Same powerful features as ReactFlow
- Vue-native components
- Interactive, customizable nodes/edges
- Layout algorithms (dagre for hierarchical)
- Zoom, pan, selection built-in
- Actively maintained

**Alternatives**:
- **Cytoscape.js**: Not Vue-specific, more complex API
- **v-network-graph**: Lightweight but fewer features
- **D3.js**: Too low-level, requires significant custom code

#### Code Editor: **Monaco Editor (Vue wrapper)**

**Rationale**:
- Industry-standard editor (VS Code)
- SQL syntax highlighting
- YAML syntax highlighting
- IntelliSense-like features
- Vue wrapper available (monaco-editor-vue3)

**Alternative**: CodeMirror 6 (lighter, but Monaco has better features)

### 3.2 Backend Stack

**Same as React version** - unchanged:
- **Framework**: FastAPI
- **YAML Processing**: ruamel.yaml
- **Validation**: Existing specifications.py + Pydantic
- **API Documentation**: FastAPI's built-in Swagger UI

See React architecture document for detailed backend rationale.

### 3.3 Development & Deployment

#### Package Management:
- **Frontend**: pnpm (faster, more efficient than npm)
- **Backend**: uv (already used in project) or pip

#### Development Environment:
- **Frontend**: Vite dev server (localhost:5173)
- **Backend**: FastAPI with uvicorn (localhost:8000)
- **Proxy**: Vite proxy to backend API

#### Version Control:
- Git (already in use)
- Pre-commit hooks (optional): eslint, prettier, black, mypy

#### Deployment Options:
Same as React version - Vue builds to static files that can be served identically.

---

## 4. Detailed Component Architecture

### 4.1 Frontend Architecture

#### Directory Structure

```
frontend/
├── src/
│   ├── api/                      # API client and types
│   │   ├── client.ts             # Axios wrapper
│   │   ├── config-api.ts         # Configuration endpoints
│   │   ├── validation-api.ts     # Validation endpoints
│   │   └── types.ts              # API request/response types
│   ├── components/               # Reusable components
│   │   ├── common/               # Generic components
│   │   │   ├── AppButton.vue
│   │   │   ├── AppModal.vue
│   │   │   └── ...
│   │   ├── entity/               # Entity-specific components
│   │   │   ├── EntityList.vue
│   │   │   ├── EntityCard.vue
│   │   │   ├── EntityEditor.vue
│   │   │   ├── BasicPropertiesForm.vue
│   │   │   ├── ColumnsForm.vue
│   │   │   ├── DependenciesForm.vue
│   │   │   ├── ForeignKeysForm.vue
│   │   │   └── AdvancedPropertiesForm.vue
│   │   ├── graph/                # Dependency graph components
│   │   │   ├── DependencyGraph.vue
│   │   │   ├── EntityNode.vue
│   │   │   ├── DependencyEdge.vue
│   │   │   └── GraphControls.vue
│   │   └── validation/           # Validation components
│   │       ├── ValidationReport.vue
│   │       ├── ValidationItem.vue
│   │       └── ValidationSummary.vue
│   ├── composables/              # Composition API composables (like hooks)
│   │   ├── useConfiguration.ts   # Configuration operations
│   │   ├── useValidation.ts      # Validation logic
│   │   ├── useEntityEditor.ts    # Entity editing logic
│   │   └── useDependencyGraph.ts # Graph computation
│   ├── layouts/                  # Layout components
│   │   ├── DefaultLayout.vue     # Main app layout
│   │   └── EditorLayout.vue      # Editor-specific layout
│   ├── router/                   # Vue Router configuration
│   │   └── index.ts              # Routes definition
│   ├── stores/                   # Pinia stores
│   │   ├── config.ts             # Configuration store
│   │   ├── ui.ts                 # UI state store
│   │   └── validation.ts         # Validation store
│   ├── types/                    # Shared TypeScript types
│   │   ├── entity.ts             # Entity type definitions
│   │   ├── config.ts             # Configuration types
│   │   └── validation.ts         # Validation types
│   ├── utils/                    # Utility functions
│   │   ├── yaml.ts               # YAML formatting helpers
│   │   ├── graph.ts              # Graph computation utilities
│   │   └── validation.ts         # Client-side validation
│   ├── views/                    # Page components (routed)
│   │   ├── EntitiesView.vue      # Entity list page
│   │   ├── GraphView.vue         # Dependency graph page
│   │   ├── ValidationView.vue    # Validation report page
│   │   └── SettingsView.vue      # Settings page
│   ├── App.vue                   # Root component
│   ├── main.ts                   # Entry point
│   └── vite-env.d.ts             # Vite type declarations
├── public/                       # Static assets
├── index.html                    # HTML entry point
├── package.json
├── tsconfig.json
├── vite.config.ts
├── .eslintrc.cjs
└── README.md
```

#### State Management Design with Pinia

**Configuration Store**:
```typescript
// stores/config.ts
import { defineStore } from 'pinia'
import type { Entity, ConfigMetadata } from '@/types/config'

export const useConfigStore = defineStore('config', () => {
  // State (using ref for reactive state)
  const entities = ref<Record<string, Entity>>({})
  const metadata = ref<ConfigMetadata | null>(null)
  const isDirty = ref(false)
  const isLoading = ref(false)
  const currentFile = ref<string | null>(null)
  
  // Getters (computed)
  const entityList = computed(() => Object.values(entities.value))
  const entityCount = computed(() => entityList.value.length)
  
  const getEntityById = computed(() => {
    return (id: string) => entities.value[id]
  })
  
  const getEntityDependencies = computed(() => {
    return (id: string) => {
      const entity = entities.value[id]
      if (!entity) return []
      return entity.depends_on
        .map(depId => entities.value[depId])
        .filter(Boolean)
    }
  })
  
  const getEntityDependents = computed(() => {
    return (id: string) => {
      return entityList.value.filter(entity => 
        entity.depends_on.includes(id)
      )
    }
  })
  
  const getTopologicalOrder = computed(() => {
    // Topological sort implementation
    return topologicalSort(entities.value)
  })
  
  // Actions
  async function loadConfiguration(file: string) {
    isLoading.value = true
    try {
      const response = await configApi.loadConfiguration(file)
      entities.value = response.entities
      metadata.value = response.metadata
      currentFile.value = file
      isDirty.value = false
    } finally {
      isLoading.value = false
    }
  }
  
  async function saveConfiguration() {
    if (!currentFile.value) throw new Error('No file loaded')
    await configApi.saveConfiguration(currentFile.value, {
      entities: entities.value,
      metadata: metadata.value
    })
    isDirty.value = false
  }
  
  function addEntity(entity: Entity) {
    if (entities.value[entity.name]) {
      throw new Error(`Entity ${entity.name} already exists`)
    }
    entities.value[entity.name] = entity
    isDirty.value = true
  }
  
  function updateEntity(id: string, updates: Partial<Entity>) {
    if (!entities.value[id]) {
      throw new Error(`Entity ${id} not found`)
    }
    entities.value[id] = { ...entities.value[id], ...updates }
    isDirty.value = true
  }
  
  function deleteEntity(id: string) {
    if (!entities.value[id]) {
      throw new Error(`Entity ${id} not found`)
    }
    delete entities.value[id]
    isDirty.value = true
  }
  
  function reorderEntities(order: string[]) {
    const newEntities: Record<string, Entity> = {}
    order.forEach(id => {
      if (entities.value[id]) {
        newEntities[id] = entities.value[id]
      }
    })
    entities.value = newEntities
    isDirty.value = true
  }
  
  return {
    // State
    entities,
    metadata,
    isDirty,
    isLoading,
    currentFile,
    // Getters
    entityList,
    entityCount,
    getEntityById,
    getEntityDependencies,
    getEntityDependents,
    getTopologicalOrder,
    // Actions
    loadConfiguration,
    saveConfiguration,
    addEntity,
    updateEntity,
    deleteEntity,
    reorderEntities
  }
})
```

**Validation Store**:
```typescript
// stores/validation.ts
import { defineStore } from 'pinia'
import type { ValidationResult } from '@/types/validation'

export const useValidationStore = defineStore('validation', () => {
  // State
  const results = ref<ValidationResult[]>([])
  const isValidating = ref(false)
  const lastValidation = ref<Date | null>(null)
  
  // Getters
  const hasErrors = computed(() => 
    results.value.some(r => r.severity === 'error')
  )
  
  const errorCount = computed(() => 
    results.value.filter(r => r.severity === 'error').length
  )
  
  const warningCount = computed(() => 
    results.value.filter(r => r.severity === 'warning').length
  )
  
  const getEntityErrors = computed(() => {
    return (entityId: string) => 
      results.value.filter(r => r.entity === entityId)
  })
  
  // Actions
  async function validate() {
    isValidating.value = true
    try {
      const response = await validationApi.validate()
      results.value = response.results
      lastValidation.value = new Date()
    } finally {
      isValidating.value = false
    }
  }
  
  function clearValidation() {
    results.value = []
    lastValidation.value = null
  }
  
  return {
    results,
    isValidating,
    lastValidation,
    hasErrors,
    errorCount,
    warningCount,
    getEntityErrors,
    validate,
    clearValidation
  }
})
```

#### Key Component Designs

**EntityEditor.vue Component**:
```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useConfigStore } from '@/stores/config'
import type { Entity } from '@/types/entity'

interface Props {
  entityId?: string  // undefined for new entity
}

const props = defineProps<Props>()
const emit = defineEmits<{
  save: [entity: Entity]
  cancel: []
}>()

const configStore = useConfigStore()
const currentTab = ref(0)

// Define validation schema with Zod
const entitySchema = z.object({
  name: z.string().regex(/^[a-z][a-z0-9_]*$/, 'Must be snake_case'),
  type: z.enum(['data', 'sql', 'fixed']),
  source: z.string().nullable(),
  surrogate_id: z.string().regex(/.*_id$/, 'Must end with _id').optional(),
  keys: z.array(z.string()),
  columns: z.array(z.string()),
  depends_on: z.array(z.string()),
  // ... more fields
})

// VeeValidate form
const { handleSubmit, values, errors, defineField } = useForm({
  validationSchema: toTypedSchema(entitySchema),
  initialValues: props.entityId 
    ? configStore.getEntityById(props.entityId) 
    : getDefaultEntity()
})

// Define fields
const [name] = defineField('name')
const [type] = defineField('type')
const [source] = defineField('source')
// ... more fields

const onSubmit = handleSubmit((values) => {
  emit('save', values as Entity)
})

function getDefaultEntity(): Partial<Entity> {
  return {
    type: 'data',
    source: null,
    keys: [],
    columns: [],
    depends_on: []
  }
}
</script>

<template>
  <v-card>
    <v-card-title>
      {{ entityId ? 'Edit Entity' : 'New Entity' }}
    </v-card-title>
    
    <v-card-text>
      <v-form @submit.prevent="onSubmit">
        <v-tabs v-model="currentTab">
          <v-tab value="basic">Basic</v-tab>
          <v-tab value="columns">Columns</v-tab>
          <v-tab value="dependencies">Dependencies</v-tab>
          <v-tab value="foreign-keys">Foreign Keys</v-tab>
          <v-tab value="advanced">Advanced</v-tab>
        </v-tabs>
        
        <v-window v-model="currentTab" class="mt-4">
          <v-window-item value="basic">
            <BasicPropertiesForm 
              v-model:name="name"
              v-model:type="type"
              v-model:source="source"
              :errors="errors"
            />
          </v-window-item>
          
          <v-window-item value="columns">
            <ColumnsForm />
          </v-window-item>
          
          <v-window-item value="dependencies">
            <DependenciesForm />
          </v-window-item>
          
          <v-window-item value="foreign-keys">
            <ForeignKeysForm />
          </v-window-item>
          
          <v-window-item value="advanced">
            <AdvancedPropertiesForm />
          </v-window-item>
        </v-window>
        
        <v-card-actions class="mt-4">
          <v-spacer />
          <v-btn @click="emit('cancel')">Cancel</v-btn>
          <v-btn color="primary" type="submit">Save</v-btn>
        </v-card-actions>
      </v-form>
    </v-card-text>
  </v-card>
</template>
```

**DependencyGraph.vue Component**:
```vue
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background, Controls, MiniMap } from '@vue-flow/additional-components'
import type { Node, Edge } from '@vue-flow/core'
import { useConfigStore } from '@/stores/config'
import { computeGraphLayout } from '@/utils/graph'

interface Props {
  selectedEntityId?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  entityClick: [entityId: string]
  dependencyChange: [entityId: string, dependencies: string[]]
}>()

const configStore = useConfigStore()
const { fitView } = useVueFlow()

const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])

// Compute graph layout when entities change
watch(
  () => configStore.entities,
  () => {
    const layout = computeGraphLayout(configStore.entityList)
    nodes.value = layout.nodes
    edges.value = layout.edges
    
    // Fit view after layout
    nextTick(() => fitView())
  },
  { immediate: true, deep: true }
)

// Highlight selected entity
const nodeClass = computed(() => {
  return (node: Node) => {
    return node.id === props.selectedEntityId ? 'selected' : ''
  }
})

function onNodeClick(event: MouseEvent, node: Node) {
  emit('entityClick', node.id)
}

function onNodeContextMenu(event: MouseEvent, node: Node) {
  event.preventDefault()
  // Show context menu
}
</script>

<template>
  <VueFlow
    v-model:nodes="nodes"
    v-model:edges="edges"
    :node-class="nodeClass"
    @node-click="onNodeClick"
    @node-context-menu="onNodeContextMenu"
    fit-view-on-init
  >
    <Background />
    <Controls />
    <MiniMap />
    
    <template #node-custom="{ data }">
      <EntityNode :entity="data.entity" />
    </template>
  </VueFlow>
</template>

<style scoped>
.vue-flow {
  height: 100%;
}

:deep(.selected) {
  stroke: var(--v-theme-primary);
  stroke-width: 3px;
}
</style>
```

**EntityList.vue Component**:
```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useConfigStore } from '@/stores/config'
import { useValidationStore } from '@/stores/validation'

const configStore = useConfigStore()
const validationStore = useValidationStore()

const search = ref('')
const selectedType = ref<string | null>(null)
const sortBy = ref<string>('name')

const headers = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Type', key: 'type', sortable: true },
  { title: 'Source', key: 'source', sortable: true },
  { title: 'Dependencies', key: 'depends_on', sortable: false },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false }
]

const filteredEntities = computed(() => {
  let entities = configStore.entityList
  
  // Filter by search
  if (search.value) {
    const searchLower = search.value.toLowerCase()
    entities = entities.filter(e => 
      e.name.toLowerCase().includes(searchLower)
    )
  }
  
  // Filter by type
  if (selectedType.value) {
    entities = entities.filter(e => e.type === selectedType.value)
  }
  
  return entities
})

function getEntityStatus(entityId: string) {
  const errors = validationStore.getEntityErrors(entityId)
  if (errors.some(e => e.severity === 'error')) return 'error'
  if (errors.some(e => e.severity === 'warning')) return 'warning'
  return 'valid'
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'error': return 'mdi-alert-circle'
    case 'warning': return 'mdi-alert'
    case 'valid': return 'mdi-check-circle'
    default: return 'mdi-help-circle'
  }
}

function getStatusColor(status: string) {
  switch (status) {
    case 'error': return 'error'
    case 'warning': return 'warning'
    case 'valid': return 'success'
    default: return 'grey'
  }
}

function editEntity(entity: Entity) {
  // Open editor
}

function deleteEntity(entity: Entity) {
  // Show confirmation dialog
}

function duplicateEntity(entity: Entity) {
  // Duplicate entity
}
</script>

<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <span>Entities</span>
            <v-spacer />
            <v-text-field
              v-model="search"
              prepend-inner-icon="mdi-magnify"
              label="Search entities"
              single-line
              hide-details
              density="compact"
              class="mr-4"
              style="max-width: 300px"
            />
            <v-select
              v-model="selectedType"
              :items="['data', 'sql', 'fixed']"
              label="Filter by type"
              clearable
              density="compact"
              hide-details
              style="max-width: 150px"
              class="mr-4"
            />
            <v-btn color="primary" prepend-icon="mdi-plus">
              New Entity
            </v-btn>
          </v-card-title>
          
          <v-data-table
            :headers="headers"
            :items="filteredEntities"
            :search="search"
            item-value="name"
          >
            <template #item.type="{ item }">
              <v-chip :color="getTypeColor(item.type)" size="small">
                {{ item.type }}
              </v-chip>
            </template>
            
            <template #item.depends_on="{ item }">
              <v-chip-group>
                <v-chip
                  v-for="dep in item.depends_on"
                  :key="dep"
                  size="x-small"
                >
                  {{ dep }}
                </v-chip>
              </v-chip-group>
            </template>
            
            <template #item.status="{ item }">
              <v-icon
                :icon="getStatusIcon(getEntityStatus(item.name))"
                :color="getStatusColor(getEntityStatus(item.name))"
              />
            </template>
            
            <template #item.actions="{ item }">
              <v-btn
                icon="mdi-pencil"
                size="small"
                variant="text"
                @click="editEntity(item)"
              />
              <v-btn
                icon="mdi-content-copy"
                size="small"
                variant="text"
                @click="duplicateEntity(item)"
              />
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                @click="deleteEntity(item)"
              />
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
```

#### Composables (Vue's equivalent of React Hooks)

**useConfiguration.ts**:
```typescript
// composables/useConfiguration.ts
import { ref, computed } from 'vue'
import { useConfigStore } from '@/stores/config'
import { useValidationStore } from '@/stores/validation'
import type { Entity } from '@/types/entity'

export function useConfiguration() {
  const configStore = useConfigStore()
  const validationStore = useValidationStore()
  
  const isLoading = computed(() => configStore.isLoading)
  const isDirty = computed(() => configStore.isDirty)
  
  async function loadConfiguration(file: string) {
    await configStore.loadConfiguration(file)
    await validationStore.validate()
  }
  
  async function saveConfiguration() {
    // Validate before saving
    await validationStore.validate()
    
    if (validationStore.hasErrors) {
      throw new Error('Cannot save configuration with errors')
    }
    
    await configStore.saveConfiguration()
  }
  
  function createEntity(entity: Entity) {
    configStore.addEntity(entity)
    // Trigger validation
    validationStore.validate()
  }
  
  function updateEntity(id: string, updates: Partial<Entity>) {
    configStore.updateEntity(id, updates)
    validationStore.validate()
  }
  
  function deleteEntity(id: string) {
    // Check for dependents
    const dependents = configStore.getEntityDependents(id)
    if (dependents.length > 0) {
      throw new Error(
        `Cannot delete ${id}: ${dependents.length} entities depend on it`
      )
    }
    
    configStore.deleteEntity(id)
    validationStore.validate()
  }
  
  return {
    isLoading,
    isDirty,
    loadConfiguration,
    saveConfiguration,
    createEntity,
    updateEntity,
    deleteEntity
  }
}
```

**useEntityEditor.ts**:
```typescript
// composables/useEntityEditor.ts
import { ref, computed } from 'vue'
import { useConfigStore } from '@/stores/config'
import type { Entity } from '@/types/entity'

export function useEntityEditor(entityId?: string) {
  const configStore = useConfigStore()
  
  const entity = computed(() => 
    entityId ? configStore.getEntityById(entityId) : null
  )
  
  const isNewEntity = computed(() => !entityId)
  
  const availableSources = computed(() => {
    // Get entities that can be used as sources
    return configStore.entityList
      .filter(e => e.name !== entityId)
      .map(e => e.name)
  })
  
  const availableDependencies = computed(() => {
    // Get entities that can be dependencies (excluding self and circular deps)
    return configStore.entityList
      .filter(e => e.name !== entityId)
      .map(e => e.name)
  })
  
  function validateDependency(depId: string): boolean {
    if (!entityId) return true // New entity, no circular check needed
    
    // Check if adding this dependency would create a cycle
    return !wouldCreateCycle(entityId, depId)
  }
  
  function wouldCreateCycle(fromId: string, toId: string): boolean {
    // BFS to detect cycle
    const visited = new Set<string>()
    const queue = [toId]
    
    while (queue.length > 0) {
      const current = queue.shift()!
      if (current === fromId) return true
      if (visited.has(current)) continue
      
      visited.add(current)
      const entity = configStore.getEntityById(current)
      if (entity) {
        queue.push(...entity.depends_on)
      }
    }
    
    return false
  }
  
  return {
    entity,
    isNewEntity,
    availableSources,
    availableDependencies,
    validateDependency
  }
}
```

### 4.2 Backend Architecture

**Backend architecture is identical to the React version** - see [UI_ARCHITECTURE.md](./UI_ARCHITECTURE.md) section 4.2 for complete details.

Key points:
- FastAPI framework
- Service layer (ConfigurationService, ValidationService, DependencyService, YamlService)
- Pydantic models for API contracts
- Integration with existing `src/` code

---

## 5. Data Flow & Interactions

### 5.1 Load Configuration Flow

```
User → Vue Component → Pinia Store → API → Backend → Filesystem
                                                        │
1. Click "Load Configuration"                           │
   │                                                    │
2. Select file (using composable)                      │
   │                                                    │
3. configStore.loadConfiguration(file)                 │
   │                                                    │
4. POST /api/v1/configurations/load                    │
   │                                                    │
5. YamlService.load(file_path)─────────────────────────┘
   │
6. Parse entities with ruamel.yaml
   │
7. Return Configuration object
   │
8. Update Pinia store (reactive)
   │
9. Components auto re-render
   │
10. Trigger validation (async)
    │
11. Display entities + validation results
```

### 5.2 Create Entity Flow (Vue)

```
User → Vue Component → VeeValidate → Pinia Store → API → Backend
                                                              │
1. Click "New Entity"                                         │
   │                                                          │
2. Open EntityEditor modal                                   │
   │                                                          │
3. Fill form (v-model bindings)                              │
   │                                                          │
4. Client-side validation (VeeValidate + Zod)                │
   │                                                          │
5. Submit form (@submit handler)                             │
   │                                                          │
6. configStore.addEntity(entity)                             │
   │                                                          │
7. POST /api/v1/configurations/{name}/entities               │
   │                                                          │
8. ConfigurationService.add_entity()─────────────────────────┘
   │
9. Validate unique name, circular deps
   │
10. Add to entities dict
    │
11. Return updated Configuration
    │
12. Pinia store updates (reactive)
    │
13. Components auto re-render
    │
14. Trigger validation (async)
```

### 5.3 Vue-Specific Reactive Flow

Vue's reactivity system provides automatic updates:

```
Pinia Store Change → Computed Properties Update → Template Re-renders
        ↓
   Watchers Triggered
        ↓
   Side Effects Execute
```

Example:
```typescript
// In component
const entityCount = computed(() => configStore.entityCount)

// When store changes:
configStore.addEntity(newEntity)
// entityCount automatically updates
// Template shows new count
// No manual subscription needed!
```

---

## 6. Phase 2 & 3 Architecture Extensions

**Phase 2 and 3 extensions are identical to React version** - Vue components will be different but the architecture, APIs, and backend services remain the same.

Key additions for Phase 2:
- Data source introspection components (Vue SFCs)
- Schema browser (v-treeview component)
- Sample data preview (v-data-table)

Key additions for Phase 3:
- Schema guidance components
- Recommendation engine integration
- Template library

See [UI_ARCHITECTURE.md](./UI_ARCHITECTURE.md) section 6 for complete details.

---

## 7. Deployment Architecture

**Deployment is identical to React version** - Vue builds to static HTML/CSS/JS that can be served the same way:

1. **Development**: Vite dev server + FastAPI
2. **Production**: Docker with nginx or single container
3. **Desktop**: PyWebView wrapper

See [UI_ARCHITECTURE.md](./UI_ARCHITECTURE.md) section 7 for complete details.

---

## 8. Vue-Specific Advantages

### 8.1 Developer Experience Benefits

**Template Syntax vs JSX**:
```vue
<!-- Vue: Clear, HTML-like -->
<v-text-field
  v-model="entityName"
  label="Entity Name"
  :error-messages="errors.name"
  :rules="[rules.required, rules.snakeCase]"
/>

<!-- React equivalent would be more verbose JSX -->
```

**Built-in Directives**:
- `v-model`: Two-way binding (simpler than React controlled components)
- `v-if` / `v-show`: Conditional rendering
- `v-for`: List rendering with automatic key handling
- `v-bind` / `v-on`: Shorthand `:` and `@`

**Single File Components**:
```vue
<script setup lang="ts">
// Logic here
</script>

<template>
  <!-- Template here -->
</template>

<style scoped>
/* Scoped styles here */
</style>
```

### 8.2 Performance Advantages

**Smaller Bundle Size**:
- Vue 3 runtime: ~34KB gzipped
- React + ReactDOM: ~42KB gzipped
- Vue's compiler optimizations reduce runtime overhead

**Finer-Grained Reactivity**:
- Vue tracks dependencies at property level
- React re-renders entire component tree (unless optimized)
- Less manual optimization needed (useMemo, useCallback)

**Automatic Dependency Tracking**:
```typescript
// Vue automatically tracks dependencies
const fullName = computed(() => {
  return `${firstName.value} ${lastName.value}`
})
// Updates automatically when firstName or lastName changes

// React requires explicit dependencies
const fullName = useMemo(() => {
  return `${firstName} ${lastName}`
}, [firstName, lastName]) // Must list dependencies
```

### 8.3 Learning Curve

**Easier for New Developers**:
- Template syntax is more intuitive (similar to HTML)
- Less JavaScript knowledge required for templates
- Official router and state management (less decision fatigue)
- Composition API provides clear organization

**Better for Domain Specialists**:
- Templates are more readable for non-developers
- Clear separation of concerns (template, script, style)
- Less magic than React hooks

---

## 9. Vue 3 Composition API Benefits

### 9.1 Code Organization

**Before (Options API)**:
```vue
<script>
export default {
  data() {
    return {
      entities: [],
      isLoading: false
    }
  },
  computed: {
    entityCount() {
      return this.entities.length
    }
  },
  methods: {
    async loadEntities() {
      this.isLoading = true
      // ...
    }
  },
  mounted() {
    this.loadEntities()
  }
}
</script>
```

**After (Composition API)**:
```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const entities = ref<Entity[]>([])
const isLoading = ref(false)

const entityCount = computed(() => entities.value.length)

async function loadEntities() {
  isLoading.value = true
  // ...
}

onMounted(() => {
  loadEntities()
})
</script>
```

Benefits:
- Related code stays together
- Better TypeScript inference
- Easier to extract into composables
- No `this` context issues

### 9.2 Composables vs React Hooks

**Vue Composables** have advantages:
- Can call conditionally (unlike React hooks)
- No dependency arrays to maintain
- Automatic cleanup (onUnmounted)
- Better IDE support (Vue Language Features)

Example:
```typescript
// Composable can be called anywhere, even conditionally
if (shouldTrackConfig) {
  const { isDirty } = useConfiguration()
}

// React hooks have strict rules:
// - Must call at top level
// - Cannot call conditionally
// - Must maintain dependency arrays
```

---

## 10. Technology Stack Comparison: Vue vs React

| Aspect | Vue 3 | React | Winner |
|--------|-------|-------|--------|
| **Bundle Size** | ~34KB | ~42KB | Vue |
| **Learning Curve** | Easier | Steeper | Vue |
| **Template Syntax** | HTML-like | JSX | Vue (for your team) |
| **State Management** | Pinia (official) | Redux/Zustand | Tie |
| **Router** | Vue Router (official) | React Router | Tie |
| **Form Handling** | VeeValidate | React Hook Form | Tie |
| **TypeScript Support** | Excellent | Excellent | Tie |
| **Component Libraries** | Vuetify, Element Plus | MUI, Ant Design | React (more options) |
| **Job Market** | Smaller | Larger | React |
| **Your Team Skills** | Better | Weaker | **Vue** |
| **Ecosystem Size** | Good | Larger | React |
| **Performance** | Excellent | Excellent | Tie |
| **Developer Experience** | Excellent | Good | Vue (for your team) |

**Recommendation**: **Use Vue 3** given your team's stronger Vue skills and the comparable capabilities for this project.

---

## 11. Testing Strategy

### 11.1 Frontend Testing (Vue)

**Unit Tests** (Vitest + Vue Test Utils):
```typescript
import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import EntityEditor from '@/components/entity/EntityEditor.vue'

describe('EntityEditor', () => {
  it('renders form fields', () => {
    const wrapper = mount(EntityEditor)
    expect(wrapper.find('input[name="name"]').exists()).toBe(true)
  })
  
  it('validates entity name format', async () => {
    const wrapper = mount(EntityEditor)
    await wrapper.find('input[name="name"]').setValue('InvalidName')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.text()).toContain('Must be snake_case')
  })
})
```

**Component Tests**:
```typescript
import { createPinia, setActivePinia } from 'pinia'
import { useConfigStore } from '@/stores/config'

describe('ConfigStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  
  it('adds entity', () => {
    const store = useConfigStore()
    const entity = { name: 'test', type: 'data' }
    store.addEntity(entity)
    expect(store.entities['test']).toEqual(entity)
  })
})
```

**E2E Tests** (Playwright):
Same as React version - tests user flows at browser level.

### 11.2 Backend Testing

**Same as React version** - see [UI_ARCHITECTURE.md](./UI_ARCHITECTURE.md) section 9.2.

---

## 12. Development Workflow

### 12.1 Initial Setup

**Backend** (same as React version):
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn app.main:app --reload
```

**Frontend** (Vue-specific):
```bash
# Create Vue 3 project with TypeScript
npm create vite@latest frontend -- --template vue-ts

cd frontend
pnpm install

# Install dependencies
pnpm add vue-router@4 pinia vee-validate zod @vee-validate/zod
pnpm add vuetify @vue-flow/core @vue-flow/additional-components
pnpm add axios
pnpm add -D @types/node @vue/test-utils vitest

# Configure Vuetify
# (see Vuetify docs for setup)

# Start dev server
pnpm dev
```

### 12.2 Project Structure Setup

```bash
# Create directory structure
mkdir -p src/{api,components/{common,entity,graph,validation},composables,layouts,router,stores,types,utils,views}

# Create example files
touch src/stores/config.ts
touch src/stores/validation.ts
touch src/composables/useConfiguration.ts
touch src/router/index.ts
```

### 12.3 Code Quality Tools

**Frontend (Vue)**:
```bash
# ESLint with Vue plugin
pnpm add -D eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser
pnpm add -D eslint-plugin-vue

# Prettier
pnpm add -D prettier eslint-config-prettier eslint-plugin-prettier

# Vue Tsc for type checking
pnpm add -D vue-tsc
```

**ESLint Config** (`.eslintrc.cjs`):
```javascript
module.exports = {
  extends: [
    'plugin:vue/vue3-recommended',
    '@vue/typescript/recommended',
    'prettier'
  ],
  rules: {
    'vue/multi-word-component-names': 'off',
    '@typescript-eslint/no-explicit-any': 'warn'
  }
}
```

**Package Scripts**:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:e2e": "playwright test",
    "lint": "eslint . --ext .vue,.ts,.tsx",
    "lint:fix": "eslint . --ext .vue,.ts,.tsx --fix",
    "format": "prettier --write \"src/**/*.{vue,ts,tsx,json}\""
  }
}
```

---

## 13. Vite Configuration

**vite.config.ts**:
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: true })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

---

## 14. Example Application Entry Point

**main.ts**:
```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// Pinia store
const pinia = createPinia()
app.use(pinia)

// Vuetify
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light'
  }
})
app.use(vuetify)

// Router
app.use(router)

app.mount('#app')
```

**App.vue**:
```vue
<script setup lang="ts">
import { useRoute } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const route = useRoute()
</script>

<template>
  <v-app>
    <DefaultLayout>
      <router-view />
    </DefaultLayout>
  </v-app>
</template>
```

**router/index.ts**:
```typescript
import { createRouter, createWebHistory } from 'vue-router'
import EntitiesView from '@/views/EntitiesView.vue'
import GraphView from '@/views/GraphView.vue'
import ValidationView from '@/views/ValidationView.vue'
import SettingsView from '@/views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/entities'
    },
    {
      path: '/entities',
      name: 'entities',
      component: EntitiesView
    },
    {
      path: '/graph',
      name: 'graph',
      component: GraphView
    },
    {
      path: '/validation',
      name: 'validation',
      component: ValidationView
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView
    }
  ]
})

export default router
```

---

## 15. Key Vue 3 Packages

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "vuetify": "^3.5.0",
    "@mdi/font": "^7.4.0",
    
    "@vue-flow/core": "^1.33.0",
    "@vue-flow/additional-components": "^1.3.0",
    
    "vee-validate": "^4.12.0",
    "@vee-validate/zod": "^4.12.0",
    "zod": "^3.22.0",
    
    "monaco-editor-vue3": "^0.1.0",
    "axios": "^1.6.0",
    
    "dagre": "^0.8.5"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "@vue/test-utils": "^2.4.0",
    "vite": "^5.0.0",
    "vite-plugin-vuetify": "^2.0.0",
    "vitest": "^1.2.0",
    "vue-tsc": "^1.8.0",
    
    "@playwright/test": "^1.41.0",
    
    "@typescript-eslint/eslint-plugin": "^6.19.0",
    "@typescript-eslint/parser": "^6.19.0",
    "eslint": "^8.56.0",
    "eslint-plugin-vue": "^9.20.0",
    "eslint-config-prettier": "^9.1.0",
    "prettier": "^3.2.0",
    
    "typescript": "^5.3.0"
  }
}
```

---

## 16. Project Timeline (Same as React)

**Week 1-2**: Foundation (project setup, API design, basic CRUD)  
**Week 3-4**: Entity management (editor, validation)  
**Week 5-6**: Dependencies (graph visualization, editor)  
**Week 7-8**: Configuration operations (load/save, backups, validation UI)  
**Week 9**: Polish & testing

**Total: ~9 weeks** for MVP (1 developer)

---

## 17. Migration from React Version

If you started with React and want to migrate:

### 17.1 Component Migration Pattern

**React**:
```jsx
function EntityEditor({ entityId, onSave }) {
  const [name, setName] = useState('')
  
  useEffect(() => {
    // Load entity
  }, [entityId])
  
  return <form>...</form>
}
```

**Vue**:
```vue
<script setup lang="ts">
const props = defineProps<{ entityId?: string }>()
const emit = defineEmits<{ save: [entity: Entity] }>()

const name = ref('')

watch(() => props.entityId, () => {
  // Load entity
})
</script>

<template>
  <form>...</form>
</template>
```

### 17.2 State Migration

**React (Zustand)**:
```typescript
const useStore = create((set) => ({
  entities: {},
  addEntity: (entity) => set((state) => ({
    entities: { ...state.entities, [entity.name]: entity }
  }))
}))
```

**Vue (Pinia)**:
```typescript
export const useStore = defineStore('config', () => {
  const entities = ref<Record<string, Entity>>({})
  
  function addEntity(entity: Entity) {
    entities.value[entity.name] = entity
  }
  
  return { entities, addEntity }
})
```

---

## 18. Conclusion

This Vue 3 architecture provides all the benefits of the React version while leveraging your team's stronger Vue.js skills:

### Key Strengths:
1. **Team Expertise**: Leverages existing Vue.js knowledge
2. **Modern Stack**: Vue 3 Composition API + TypeScript
3. **Better DX**: Template syntax, automatic reactivity, less boilerplate
4. **Smaller Bundle**: ~20% smaller than React equivalent
5. **Official Ecosystem**: Pinia, Vue Router are officially maintained
6. **Same Backend**: FastAPI backend remains unchanged
7. **Extensible**: Ready for Phase 2/3 enhancements

### Recommended Next Steps:
1. Set up Vite + Vue 3 + TypeScript project
2. Install Vuetify and Pinia
3. Create basic layout and routing
4. Implement entity list view (read-only)
5. Connect to FastAPI backend
6. Build entity editor with VeeValidate
7. Add Vue Flow dependency graph
8. Integrate validation

The Vue 3 version is the better choice for your project given your team's skills and will deliver the same functionality with better developer experience.

---

**Document Version**: 1.0  
**Date**: December 12, 2025  
**Author**: System Architect  
**Status**: Proposal for Review
