# Shape Shifter Configuration Editor - Developer Guide

Technical documentation for developers working on the frontend.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [State Management](#state-management)
3. [API Integration](#api-integration)
4. [Component Structure](#component-structure)
5. [Composables](#composables)
6. [Adding Features](#adding-features)
7. [Testing](#testing)
8. [Deployment](#deployment)

## Architecture Overview

### Technology Stack

- **Vue 3.5+**: Composition API with `<script setup>`
- **TypeScript 5.6**: Strict mode enabled
- **Vuetify 3.7**: Material Design components
- **Pinia 2.3**: State management
- **Vue Router 4.5**: Client-side routing
- **Axios 1.7**: HTTP client
- **Vite 6.0**: Build tool and dev server

### Design Patterns

**Composition API Pattern**
```typescript
<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const count = ref(0)
const doubled = computed(() => count.value * 2)

watch(count, (newVal) => {
  console.log(`Count changed to ${newVal}`)
})
</script>
```

**Composable Pattern**
```typescript
export function useFeature(options: Options) {
  const state = ref<State>()
  const loading = ref(false)
  
  async function fetch() {
    loading.value = true
    // ... fetch logic
    loading.value = false
  }
  
  return { state, loading, fetch }
}
```

**Store Pattern**
```typescript
export const useFeatureStore = defineStore('feature', () => {
  const items = ref<Item[]>([])
  
  async function fetchItems() {
    items.value = await api.getItems()
  }
  
  return { items, fetchItems }
})
```

## State Management

### Pinia Stores

Located in `src/stores/`, each store manages a specific domain:

#### Configuration Store

```typescript
// src/stores/configuration.ts
export const useConfigurationStore = defineStore('configuration', () => {
  const configurations = ref<Configuration[]>([])
  const currentConfiguration = ref<Configuration | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  async function fetchAll() { /* ... */ }
  async function create(config: CreateConfigRequest) { /* ... */ }
  async function update(name: string, data: UpdateConfigRequest) { /* ... */ }
  async function remove(name: string) { /* ... */ }
  
  return {
    configurations,
    currentConfiguration,
    loading,
    error,
    fetchAll,
    create,
    update,
    remove,
  }
})
```

**When to use:**
- Global state needed across multiple views
- Caching API responses
- Complex state mutations

#### Entity Store

Manages entity CRUD within configurations.

**Key features:**
- Per-configuration entity lists
- CRUD operations
- Relationship tracking

#### Validation Store

Manages validation results and dependency graphs.

**Key features:**
- Validation state caching
- Dependency graph data
- Circular dependency detection

### Store Best Practices

1. **Keep stores focused**: One domain per store
2. **Use computed for derived state**: Don't duplicate data
3. **Handle errors gracefully**: Set error state, don't throw
4. **Reset state when needed**: Clear on logout/navigation
5. **Use async/await**: Consistent promise handling

## API Integration

### API Client Structure

```typescript
// src/api/client.ts
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8012',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use((config) => {
  // Add auth token, logging, etc.
  return config
})

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle errors globally
    return Promise.reject(error)
  }
)
```

### API Module Pattern

```typescript
// src/api/configurations.ts
export const configurationsApi = {
  async getAll(): Promise<Configuration[]> {
    const { data } = await apiClient.get('/configurations')
    return data
  },
  
  async getOne(name: string): Promise<Configuration> {
    const { data } = await apiClient.get(`/configurations/${name}`)
    return data
  },
  
  async create(config: CreateConfigRequest): Promise<Configuration> {
    const { data } = await apiClient.post('/configurations', config)
    return data
  },
  
  // ... more methods
}
```

### Error Handling

```typescript
try {
  const result = await api.someMethod()
  return result
} catch (err) {
  if (axios.isAxiosError(err)) {
    const message = err.response?.data?.detail || err.message
    throw new Error(message)
  }
  throw err
}
```

## Component Structure

### Component Organization

```
src/components/
├── common/              # Reusable UI components
│   ├── EmptyState.vue
│   ├── LoadingSkeleton.vue
│   └── ErrorAlert.vue
├── configurations/      # Configuration-specific
│   ├── CreateProjectDialog.vue
│   └── DeleteConfirmationDialog.vue
├── entities/           # Entity management
│   ├── EntityListCard.vue
│   ├── EntityFormDialog.vue
│   ├── ForeignKeyEditor.vue
│   └── AdvancedEntityConfig.vue
├── dependencies/       # Dependency visualization
│   └── CircularDependencyAlert.vue
└── validation/        # Validation display
    ├── ValidationPanel.vue
    └── ValidationMessageList.vue
```

### Component Template

```vue
<template>
  <v-card>
    <v-card-title>{{ title }}</v-card-title>
    <v-card-text>
      <!-- Content -->
    </v-card-text>
    <v-card-actions>
      <!-- Actions -->
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  title: string
  modelValue: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'submit', data: FormData): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Local state
const loading = ref(false)

// Computed
const isValid = computed(() => {
  // validation logic
  return true
})

// Methods
async function handleSubmit() {
  loading.value = true
  try {
    // submit logic
    emit('submit', data)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Component-specific styles */
</style>
```

### Props & Emits Best Practices

1. **Type your interfaces**: Use TypeScript interfaces
2. **Use v-model**: For two-way binding with `modelValue` prop
3. **Emit events, don't mutate props**: Follow one-way data flow
4. **Document complex props**: Add JSDoc comments
5. **Use sensible defaults**: With `withDefaults()`

## Composables

### Composable Structure

```typescript
// src/composables/useFeature.ts
export interface UseFeatureOptions {
  autoFetch?: boolean
  configName?: string
}

export function useFeature(options: UseFeatureOptions = {}) {
  const { autoFetch = false, configName } = options
  const store = useFeatureStore()
  
  // Local reactive state
  const localState = ref()
  
  // Computed from store
  const items = computed(() => store.items)
  const loading = computed(() => store.loading)
  const error = computed(() => store.error)
  
  // Methods
  async function fetch() {
    await store.fetchItems(configName)
  }
  
  async function create(data: CreateRequest) {
    return await store.create(data)
  }
  
  // Auto-fetch on mount
  if (autoFetch && configName) {
    onMounted(() => fetch())
  }
  
  // Watch for changes
  watch(() => configName, async (newName) => {
    if (newName && autoFetch) {
      await fetch()
    }
  })
  
  return {
    // State
    items,
    loading,
    error,
    // Actions
    fetch,
    create,
    // Helpers
    // ...
  }
}
```

### Existing Composables

#### useConfigurations

```typescript
const {
  configurations,
  currentConfiguration,
  loading,
  error,
  hasUnsavedChanges,
  fetch,
  create,
  update,
  remove,
  validate,
  getBackups,
  restoreBackup,
} = useConfigurations({ autoFetch: true })
```

#### useEntities

```typescript
const {
  entities,
  entityCount,
  loading,
  error,
  fetch,
  create,
  update,
  remove,
  getByName,
} = useEntities({ 
  configName: 'my-config',
  autoFetch: true 
})
```

#### useDependencies

```typescript
const {
  graphData,
  hasCircularDependencies,
  cycles,
  statistics,
  loading,
  error,
  fetch,
  getDependenciesOf,
  getDependentsOf,
  isInCycle,
} = useDependencies({ 
  configName: 'my-config',
  autoFetch: true 
})
```

## Adding Features

### 1. Add API Method

```typescript
// src/api/myFeature.ts
export const myFeatureApi = {
  async doSomething(params: Params): Promise<Result> {
    const { data } = await apiClient.post('/endpoint', params)
    return data
  },
}
```

### 2. Create Store

```typescript
// src/stores/myFeature.ts
export const useMyFeatureStore = defineStore('myFeature', () => {
  const state = ref<State>()
  
  async function doSomething(params: Params) {
    state.value = await myFeatureApi.doSomething(params)
  }
  
  return { state, doSomething }
})
```

### 3. Create Composable

```typescript
// src/composables/useMyFeature.ts
export function useMyFeature(options = {}) {
  const store = useMyFeatureStore()
  
  const state = computed(() => store.state)
  
  return { state, doSomething: store.doSomething }
}
```

### 4. Create Component

```vue
<!-- src/components/myFeature/MyFeatureComponent.vue -->
<template>
  <v-card>
    <v-card-text>
      {{ state }}
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { useMyFeature } from '@/composables'

const { state, doSomething } = useMyFeature()
</script>
```

### 5. Add Route

```typescript
// src/router/index.ts
{
  path: '/my-feature',
  name: 'my-feature',
  component: () => import('@/views/MyFeatureView.vue'),
  meta: { title: 'My Feature' },
}
```

## Testing

### Unit Tests (Coming Soon)

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import MyComponent from '@/components/MyComponent.vue'

describe('MyComponent', () => {
  it('renders correctly', () => {
    const wrapper = mount(MyComponent, {
      props: { title: 'Test' },
    })
    expect(wrapper.text()).toContain('Test')
  })
  
  it('emits event on click', async () => {
    const wrapper = mount(MyComponent)
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('action')).toBeTruthy()
  })
})
```

### E2E Tests (Coming Soon)

```typescript
import { test, expect } from '@playwright/test'

test('create configuration', async ({ page }) => {
  await page.goto('/')
  await page.click('text=Configurations')
  await page.click('text=New Configuration')
  await page.fill('input[name="name"]', 'test-config')
  await page.click('text=Create')
  await expect(page.locator('text=test-config')).toBeVisible()
})
```

## Deployment

### Environment Variables

```bash
# .env.production
VITE_API_BASE_URL=https://api.example.com
```

### Build Configuration

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'vuetify': ['vuetify'],
        },
      },
    },
  },
})
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

```nginx
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }

  location /api {
    proxy_pass http://backend:8012;
  }
}
```

## Code Style Guide

### TypeScript

- Use `interface` for object shapes
- Use `type` for unions and intersections
- Prefer `const` over `let`
- Use optional chaining: `obj?.prop`
- Use nullish coalescing: `value ?? default`

### Vue

- Use `<script setup>` syntax
- Use Composition API
- Destructure props and emits
- Keep components under 300 lines
- Extract reusable logic to composables

### Naming

- **Components**: PascalCase (e.g., `MyComponent.vue`)
- **Composables**: camelCase with `use` prefix (e.g., `useMyFeature.ts`)
- **Files**: kebab-case (e.g., `my-feature.ts`)
- **Props**: camelCase in script, kebab-case in template
- **Events**: kebab-case (e.g., `@item-selected`)

## Performance Tips

1. **Lazy load routes**: Use dynamic imports
2. **Virtual scrolling**: For large lists
3. **Computed caching**: Use `computed()` for derived state
4. **Debounce inputs**: For search and filters
5. **Code splitting**: Separate vendor bundles

## Security

1. **Sanitize user input**: Especially for YAML/SQL
2. **Use HTTPS**: In production
3. **Set CORS properly**: On backend
4. **Validate on backend**: Don't trust frontend validation
5. **Handle errors gracefully**: Don't expose sensitive info

## Resources

- [Vue 3 Documentation](https://vuejs.org/)
- [Vuetify 3 Documentation](https://vuetifyjs.com/)
- [Pinia Documentation](https://pinia.vuejs.org/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Documentation](https://vitejs.dev/)
