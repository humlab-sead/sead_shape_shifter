---
description: "Use when writing or changing Vitest tests for Vue components, Pinia stores, composables or frontend API modules."
applyTo: "frontend/src/**/__tests__/**,frontend/vitest.config.ts,frontend/vitest.setup.ts"
---
# Frontend Tests (Vitest)

- Put unit and component tests in a `__tests__/` directory beside the code, named `<Name>.test.ts`.
- `frontend/tests/e2e/` holds Playwright tests, which are currently skipped. Vitest excludes them.
- The environment is jsdom. Shared browser stand-ins are in `frontend/vitest.setup.ts`.
- Run one file with `pnpm test:run <path>` from `frontend/`. Run all with `make frontend-test`; coverage with `make frontend-coverage`. Use `pnpm`, not npm or yarn.

## Components

There is no global test setup for Vuetify. Create it in the test:

```typescript
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { flushPromises, mount } from '@vue/test-utils'

const wrapper = mount(MyComponent, {
  global: { plugins: [createVuetify({ components, directives })] },
})
await flushPromises()
```

- Select elements by text or `data-testid`, not by Vuetify class names.
- Stub large child components, including the Monaco editors.
- Wait with `flushPromises()` before checking the DOM after async work.

## Stores

- Call `setActivePinia(createPinia())` and `vi.clearAllMocks()` in `beforeEach`.
- Mock the API module the store imports, for example `vi.mock('@/api/sessions', ...)`, and test the real store actions. Do not mock the action under test.
- Test success and failure, including the loading and error state.
- If a component test replaces a store with a plain `reactive` object, `storeToRefs()` also needs a mock (see `components/reconciliation/__tests__/ReconciliationView.test.ts`).

## API Modules and Composables

- For API modules, mock `../client` and check the method, URL and payload passed to `apiRequest`.
- Call a composable directly. Mount a host component only when it uses lifecycle hooks or injection.
- Restore real timers after using `vi.useFakeTimers()`.
- Never make real HTTP requests.
