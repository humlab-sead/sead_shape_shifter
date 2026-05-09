---
agent: agent
description: Write tests for Vue 3 components, Pinia stores, and composables in the Shape Shifter frontend
---

Create tests for `{COMPONENT}` in the frontend.

**File**: `frontend/tests/{component}.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import {ComponentName} from '@/components/{ComponentName}.vue'
import { use{Store}Store } from '@/stores/{store}'

describe('{ComponentName}', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders correctly', () => {
    const wrapper = mount({ComponentName}, { props: { /* props */ } })
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.text()).toContain('Expected text')
  })

  it('handles user interaction', async () => {
    const wrapper = mount({ComponentName})
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('event-name')).toBeTruthy()
  })

  it('displays error state', async () => {
    const wrapper = mount({ComponentName}, { props: { error: 'Test error' } })
    expect(wrapper.find('.error').text()).toContain('Test error')
  })
})
```

### Component with Vuetify

```typescript
import vuetify from '@/plugins/vuetify'

const wrapper = mount(DataSourceEditor, {
  global: { plugins: [vuetify] },
  props: { schema: { fields: [{ name: 'host', type: 'string', required: true }] } },
})
await flushPromises()
expect(wrapper.find('[name="host"]').exists()).toBe(true)
```

### Pinia Store Tests

```typescript
import { setActivePinia, createPinia } from 'pinia'
import { useProjectStore } from '@/stores/project'

describe('projectStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('loads projects', async () => {
    const store = useProjectStore()
    vi.spyOn(store, 'fetchProjects').mockResolvedValue([{ name: 'test' }])
    await store.fetchProjects()
    expect(store.projects).toHaveLength(1)
  })
})
```

### Composable Tests

```typescript
import { use{Composable} } from '@/composables/use{Composable}'

describe('use{Composable}', () => {
  it('returns expected values', () => {
    const { value, method } = use{Composable}()
    expect(value.value).toBe(expectedDefault)
  })
})
```

### Rules
- Always call `setActivePinia(createPinia())` in `beforeEach`
- Use `flushPromises()` after async operations before asserting DOM
- Use `vi.spyOn` to mock API calls; avoid real HTTP requests
- Use `defineProps<T>()` / `defineEmits<T>()` in components for type safety
- Run with `make frontend-test` or `pnpm vitest`

## Related Documentation
- [frontend.instructions.md](../instructions/frontend.instructions.md)
- [TESTING.md](../../docs/TESTING.md)
