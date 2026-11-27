import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const apiMocks = vi.hoisted(() => ({
  getLogs: vi.fn(),
  downloadLogs: vi.fn(),
  getHealth: vi.fn(),
}))

vi.mock('@/api', () => ({
  api: {
    logs: { getLogs: apiMocks.getLogs, downloadLogs: apiMocks.downloadLogs },
    health: { getHealth: apiMocks.getHealth },
  },
}))

import SettingsView from '../SettingsView.vue'
import { usePermissionsStore } from '@/stores/permissions'

function mountSettings() {
  return mount(SettingsView, {
    global: { plugins: [createVuetify({ components, directives })] },
  })
}

function tabNames(wrapper: ReturnType<typeof mountSettings>) {
  return wrapper.findAll('[role="tab"]').map((tab) => tab.text())
}

describe('SettingsView log access', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

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
    apiMocks.getHealth.mockResolvedValue({ version: '1.0.0' })
    apiMocks.getLogs.mockResolvedValue({ lines: [], total: 0 })
  })

  it('has no Logs tab and requests no logs for a user who cannot read them', async () => {
    const wrapper = mountSettings()
    await flushPromises()

    expect(tabNames(wrapper)).toEqual(['General'])
    expect(apiMocks.getLogs).not.toHaveBeenCalled()
  })

  it('shows the Logs tab and loads logs for a user who can read them', async () => {
    usePermissionsStore().canReadLogs = true
    const wrapper = mountSettings()
    await flushPromises()

    expect(tabNames(wrapper)).toEqual(['General', 'Logs'])
    expect(apiMocks.getLogs).toHaveBeenCalledTimes(1)
  })

  it('loads logs when the permission arrives after the page has opened', async () => {
    const wrapper = mountSettings()
    await flushPromises()

    usePermissionsStore().canReadLogs = true
    await flushPromises()

    expect(tabNames(wrapper)).toEqual(['General', 'Logs'])
    expect(apiMocks.getLogs).toHaveBeenCalledTimes(1)
  })
})
