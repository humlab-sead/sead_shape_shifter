import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({
  getMyPermissions: vi.fn(),
}))

vi.mock('@/api/permissions', () => ({ permissionsApi: { getMyPermissions: mocks.getMyPermissions } }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ name: 'home', params: {} }),
}))
vi.mock('@/composables/useWhatsNew', async () => {
  const { ref } = await import('vue')
  return {
    useWhatsNew: () => ({
      latestNote: ref(null),
      latestVersion: ref(null),
      loadLatestNote: () => Promise.resolve(null),
    }),
  }
})

import App from '../App.vue'

let wrapper: VueWrapper

async function mountApp(canReadLogs: boolean) {
  mocks.getMyPermissions.mockResolvedValue({ can_read_logs: canReadLogs })
  wrapper = mount(App, {
    attachTo: document.body,
    global: {
      plugins: [createVuetify({ components, directives })],
      stubs: {
        ContextHelp: true,
        RouterView: true,
        LogViewerOverlay: {
          props: ['modelValue'],
          template: '<div data-testid="log-viewer" :data-open="String(modelValue)" />',
        },
      },
    },
  })
  await flushPromises()
}

function press(key: string, shiftKey = false) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key, ctrlKey: true, shiftKey }))
  return flushPromises()
}

describe('App log access', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => undefined, removeItem: () => undefined })
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
  })

  afterEach(() => {
    wrapper?.unmount()
    document.body.innerHTML = ''
    vi.unstubAllGlobals()
  })

  it('offers no way to open the logs to a user who cannot read them', async () => {
    await mountApp(false)

    await press('L', true)
    await press('k')

    expect(wrapper.find('[data-testid="open-logs-button"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="log-viewer"]').exists()).toBe(false)
    expect(document.body.textContent).toContain('Go to Projects')
    expect(document.body.textContent).not.toContain('Open Log Viewer')
  })

  it('offers the button, shortcut, and command to a user who can read the logs', async () => {
    await mountApp(true)
    expect(wrapper.find('[data-testid="open-logs-button"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="log-viewer"]').attributes('data-open')).toBe('false')

    await press('L', true)
    await press('k')

    expect(wrapper.find('[data-testid="log-viewer"]').attributes('data-open')).toBe('true')
    expect(document.body.textContent).toContain('Open Log Viewer')
  })
})
