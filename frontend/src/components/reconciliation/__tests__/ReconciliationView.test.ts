import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { nextTick, reactive, toRefs } from 'vue'

import ReconciliationView from '../ReconciliationView.vue'

vi.mock('pinia', async () => {
  const actual = await vi.importActual<typeof import('pinia')>('pinia')

  return {
    ...actual,
    storeToRefs: (store: object) => toRefs(store),
  }
})

const reconciliationStore = reactive({
  reconciliationConfig: {
    version: '2.0',
    service_url: 'http://localhost:8000',
    entities: {
      site: {
        site_code: {
          source: null,
          property_mappings: {},
          remote: { service_type: 'site', columns: [] },
          auto_accept_threshold: 0.95,
          review_threshold: 0.7,
          mapping: [],
        },
      },
    },
  },
  loading: false,
  reconcilableEntities: ['site'],
  previewData: { site: [] as any[] },
  specifications: [
    {
      entity_name: 'site',
      target_field: 'site_code',
      source: null,
      property_mappings: {},
      remote: { service_type: 'site', columns: [] },
      auto_accept_threshold: 0.95,
      review_threshold: 0.7,
      mapping_count: 2,
      property_mapping_count: 0,
    },
  ],
  getEntityTargets: vi.fn((entityName: string) => {
    if (entityName === 'site') {
      return ['site_code']
    }
    return []
  }),
  autoReconcile: vi.fn(),
  updateMapping: vi.fn(),
  saveEntityResolutionCatalog: vi.fn(),
  checkServiceHealth: vi.fn(async () => ({ status: 'online', service_name: 'reconciliation' })),
  getServiceManifest: vi.fn(async () => ({ defaultTypes: [{ id: 'site' }] })),
  loadEntityResolutionCatalog: vi.fn(async () => {}),
  loadSpecifications: vi.fn(async () => {}),
  loadPreviewData: vi.fn(async () => {}),
  saveEntityResolutionCatalogRaw: vi.fn(async () => {}),
  exportToMapping: vi.fn(async () => ({ exported: 2, skipped_manual: 1, entity: 'site', field: 'site_code' })),
})

vi.mock('@/stores/reconciliation', () => ({
  useReconciliationStore: () => reconciliationStore,
}))

vi.mock('js-yaml', () => ({
  default: {
    dump: vi.fn(() => 'version: 2.0'),
  },
}))

const vuetify = createVuetify({ components, directives })

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock)

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })

  return { promise, resolve, reject }
}

async function mountView() {
  const wrapper = mount(ReconciliationView, {
    global: {
      plugins: [vuetify],
      stubs: {
        ReconciliationGrid: { template: '<div data-testid="reconciliation-grid" />' },
        SpecificationsList: {
          template: '<button data-testid="open-reconcile" @click="$emit(\'reconcile\', \'site\', \'site_code\')">Open</button>',
        },
        YamlEditor: { template: '<div data-testid="yaml-editor" />' },
        VTabs: { template: '<div data-testid="tabs"><slot /></div>' },
        VTab: { template: '<button type="button"><slot /></button>' },
        VWindow: { template: '<div data-testid="window"><slot /></div>' },
        VWindowItem: { template: '<div><slot /></div>' },
        VSnackbar: {
          props: ['modelValue'],
          template: '<div v-if="modelValue" data-testid="snackbar"><slot /><slot name="actions" /></div>',
        },
      },
    },
    props: {
      projectName: 'test_project',
    },
  })

  await nextTick()
  await nextTick()
  return wrapper
}

describe('ReconciliationView', () => {
  beforeEach(() => {
    reconciliationStore.loading = false
    reconciliationStore.previewData = { site: [] }
    reconciliationStore.exportToMapping = vi.fn(async () => ({ exported: 2, skipped_manual: 1, entity: 'site', field: 'site_code' }))
  })

  it('exports reconciliation links and shows the result counts', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    const exportButton = wrapper.get('[data-testid="export-to-mapping-button"]')

    await exportButton.trigger('click')
    await nextTick()

    expect(reconciliationStore.exportToMapping).toHaveBeenCalledWith('test_project', 'site', 'site_code')
    expect(wrapper.text()).toContain('Exported 2 links to mapping. Skipped 1 existing manual links.')
    expect(exportButton.exists()).toBe(true)
  })

  it('disables the export button while exporting and shows an error on failure', async () => {
    const pending = deferred<{ exported: number; skipped_manual: number; entity: string; field: string }>()
    reconciliationStore.exportToMapping = vi.fn(() => pending.promise)

    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    const exportButton = wrapper.get('[data-testid="export-to-mapping-button"]')

    await exportButton.trigger('click')
    await nextTick()

    expect(exportButton.attributes('disabled')).toBeDefined()

    pending.reject(new Error('Request failed'))
    try {
      await pending.promise
    } catch {
      // Expected rejection for this test.
    }
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Failed to export to mapping: Request failed')
  })
})