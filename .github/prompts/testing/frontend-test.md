# Frontend Testing Prompt

Write tests for Vue 3 components, stores, and composables.

## Prompt Template

```
Create tests for {COMPONENT} in the frontend:

### Test Structure

File: `frontend/tests/{component}.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import {ComponentName} from '@/components/{ComponentName}.vue'
import { use{Store}Store } from '@/stores/{store}'

describe('{ComponentName}', () => {
  beforeEach(() => {
    // Create fresh Pinia instance
    setActivePinia(createPinia())
  })

  it('renders correctly', () => {
    const wrapper = mount({ComponentName}, {
      props: {
        // props
      }
    })
    
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.text()).toContain('Expected text')
  })

  it('handles user interaction', async () => {
    const wrapper = mount({ComponentName})
    
    // Simulate user action
    await wrapper.find('button').trigger('click')
    
    // Assert state change
    expect(wrapper.emitted('event-name')).toBeTruthy()
  })

  it('displays error state', async () => {
    const wrapper = mount({ComponentName}, {
      props: {
        error: 'Test error message'
      }
    })
    
    expect(wrapper.find('.error').text()).toContain('Test error')
  })
})
```

### Testing Patterns by Component Type

#### 1. Vue Component Tests

```typescript
import { mount, flushPromises } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'

describe('DataSourceEditor', () => {
  it('renders form fields from schema', async () => {
    const wrapper = mount(DataSourceEditor, {
      global: {
        plugins: [vuetify]
      },
      props: {
        schema: {
          fields: [
            { name: 'host', type: 'string', required: true }
          ]
        }
      }
    })
    
    await flushPromises()
    
    expect(wrapper.find('[name="host"]').exists()).toBe(true)
    expect(wrapper.find('label').text()).toContain('Host')
  })

  it('validates required fields', async () => {
    const wrapper = mount(DataSourceEditor)
    
    // Submit without filling required field
    await wrapper.find('form').trigger('submit')
    
    expect(wrapper.find('.error-message').exists()).toBe(true)
  })

  it('emits save event with form data', async () => {
    const wrapper = mount(DataSourceEditor)
    
    await wrapper.find('[name="host"]').setValue('localhost')
    await wrapper.find('form').trigger('submit')
    
    const emitted = wrapper.emitted('save')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toEqual({ host: 'localhost' })
  })
})
```

#### 2. Pinia Store Tests

```typescript
import { setActivePinia, createPinia } from 'pinia'
import { useProjectStore } from '@/stores/project'
import { apiClient } from '@/api/client'
import { vi } from 'vitest'

vi.mock('@/api/client')

describe('useProjectStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads projects from API', async () => {
    const mockProjects = [
      { name: 'project1', entities: {} },
      { name: 'project2', entities: {} }
    ]
    
    vi.mocked(apiClient.get).mockResolvedValue({
      data: mockProjects
    })
    
    const store = useProjectStore()
    await store.fetchProjects()
    
    expect(store.projects).toHaveLength(2)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('handles API error', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(
      new Error('Network error')
    )
    
    const store = useProjectStore()
    await store.fetchProjects()
    
    expect(store.error).toBe('Network error')
    expect(store.loading).toBe(false)
    expect(store.projects).toEqual([])
  })

  it('saves project', async () => {
    const project = { name: 'test', entities: {} }
    
    vi.mocked(apiClient.post).mockResolvedValue({
      data: project
    })
    
    const store = useProjectStore()
    await store.saveProject(project)
    
    expect(apiClient.post).toHaveBeenCalledWith(
      '/api/v1/projects',
      project
    )
  })
})
```

#### 3. Composable Tests

```typescript
import { describe, it, expect, vi } from 'vitest'
import { useValidation } from '@/composables/useValidation'
import { useProjectStore } from '@/stores/project'

vi.mock('@/stores/project')

describe('useValidation', () => {
  it('validates project on mount', async () => {
    const mockStore = {
      currentProject: { name: 'test' },
      loading: false
    }
    vi.mocked(useProjectStore).mockReturnValue(mockStore as any)
    
    const { validate, errors, isValid } = useValidation()
    
    await validate()
    
    expect(isValid.value).toBeDefined()
    expect(errors.value).toBeInstanceOf(Array)
  })

  it('tracks validation changes', async () => {
    const { validate, hasChanges } = useValidation()
    
    expect(hasChanges.value).toBe(false)
    
    // Simulate change
    await validate()
    
    expect(hasChanges.value).toBe(true)
  })
})
```

#### 4. API Client Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient } from '@/api/client'
import axios from 'axios'

vi.mock('axios')

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('makes GET request with base URL', async () => {
    const mockData = { data: 'test' }
    vi.mocked(axios.get).mockResolvedValue({ data: mockData })
    
    const result = await apiClient.get('/endpoint')
    
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/endpoint'),
      expect.any(Object)
    )
    expect(result.data).toEqual(mockData)
  })

  it('handles 401 error with redirect', async () => {
    vi.mocked(axios.get).mockRejectedValue({
      response: { status: 401 }
    })
    
    const mockPush = vi.fn()
    vi.mock('vue-router', () => ({
      useRouter: () => ({ push: mockPush })
    }))
    
    try {
      await apiClient.get('/protected')
    } catch (e) {
      expect(mockPush).toHaveBeenCalledWith('/login')
    }
  })
})
```

### Run Tests
```bash
# All frontend tests
cd frontend
pnpm test

# Watch mode
pnpm test:watch

# Coverage
pnpm test:coverage

# UI mode
pnpm test:ui

# Specific test file
pnpm test src/components/DataSourceEditor.test.ts
```

### Code Coverage Target
- Components: 80%+ coverage
- Stores: 90%+ coverage (critical state management)
- Composables: 85%+ coverage
- Utils: 95%+ coverage

### Testing Best Practices
✅ Use `createPinia()` for fresh store state per test
✅ Mock API calls with `vi.mock()`
✅ Flush promises with `flushPromises()` for async operations
✅ Test user interactions, not implementation details
✅ Test loading/error states
✅ Use `vi.clearAllMocks()` in beforeEach
❌ Don't test Vuetify internal behavior
❌ Don't test library code (Vue Router, Pinia internals)
```

## Example Usage

```
Create tests for the EntityEditor component in the frontend:

Component: EntityEditor.vue
Features: Form rendering, validation, save/cancel
Props: entity, schema
Events: save, cancel
Store: useEntityStore

[... follow test structure ...]
```

## Related Documentation
- [Frontend Architecture](../../AGENTS.md#frontend-architecture-frontendsrc)
- [Vue 3 Patterns](../../AGENTS.md#vue-3-patterns)
- [Pinia Store Pattern](../../AGENTS.md#pinia-store-pattern)
