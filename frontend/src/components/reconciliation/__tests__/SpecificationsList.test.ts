import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { reactive, toRefs } from 'vue'

import type { ReconciliationManifestResult } from '@/types/reconciliation'
import SpecificationsList from '../SpecificationsList.vue'

vi.mock('pinia', async () => {
  const actual = await vi.importActual<typeof import('pinia')>('pinia')

  return {
    ...actual,
    storeToRefs: (store: object) => toRefs(store),
  }
})

const notificationMocks = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
}))

const apiMocks = vi.hoisted(() => ({
  deleteSpecification: vi.fn(),
  listSpecifications: vi.fn(),
}))

const specification = {
  entity_name: 'site',
  target_field: 'site_code',
  source: null,
  property_mappings: {},
  remote: { service_type: 'site', columns: [] },
  auto_accept_threshold: 0.95,
  review_threshold: 0.7,
  mapping_count: 2,
  property_mapping_count: 0,
}

const validManifestResult = {
  status: 'valid' as const,
  manifest: {
    supportedTypes: [
      { id: 'site', name: 'Site' },
      { id: 'feature_type', name: 'Feature type' },
    ],
    propertiesByType: { site: ['place_name'], feature_type: [] },
  },
}

const reconciliationStore = reactive({
  specifications: [specification],
  loadingSpecs: false,
  specsError: null as string | null,
  loadSpecifications: vi.fn(async () => {}),
  getAvailableFields: vi.fn(async () => ['site_code']),
  deleteSpecification: vi.fn(async () => ({ removedOwnedLinks: 3, removedOwnedApprovals: 2 })),
})

vi.mock('@/stores/reconciliation', () => ({
  useReconciliationStore: () => reconciliationStore,
}))

vi.mock('@/composables/useNotification', () => ({
  useNotification: () => ({
    success: notificationMocks.success,
    error: notificationMocks.error,
  }),
}))

vi.mock('@/api/reconciliation', () => ({
  reconciliationSpecApi: {
    deleteSpecification: apiMocks.deleteSpecification,
    listSpecifications: apiMocks.listSpecifications,
  },
  reconciliationServiceApi: {},
}))

const vuetify = createVuetify({ components, directives })

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock)

async function mountList(manifestResult: ReconciliationManifestResult | null = validManifestResult) {
  const wrapper = mount(SpecificationsList, {
    global: {
      plugins: [vuetify],
      stubs: {
        SpecificationEditor: true,
        VDataTable: {
          props: ['items'],
          template:
            '<div><div v-for="(item, index) in items" :key="index"><slot name="item.status" :item="item" />'
            + '<slot name="item.remote" :item="item" /><slot name="item.actions" :item="item" /></div></div>',
        },
        VDialog: {
          props: ['modelValue'],
          template: '<div v-if="modelValue" data-testid="delete-dialog"><slot /></div>',
        },
        VTooltip: {
          template: '<div><slot name="activator" :props="{}" /><slot /></div>',
        },
        VBtn: {
          emits: ['click'],
          template: '<button v-bind="$attrs" @click="$emit(\'click\', $event)"><slot /></button>',
        },
      },
    },
    props: { projectName: 'test_project', manifestResult },
  })

  await flushPromises()
  return wrapper
}

describe('SpecificationsList', () => {
  beforeEach(() => {
    reconciliationStore.specifications = [specification]
    reconciliationStore.loadingSpecs = false
    reconciliationStore.specsError = null
    reconciliationStore.loadSpecifications = vi.fn(async () => {})
    reconciliationStore.getAvailableFields = vi.fn(async () => ['site_code'])
    reconciliationStore.deleteSpecification = vi.fn(async () => ({ removedOwnedLinks: 3, removedOwnedApprovals: 2 }))
    notificationMocks.success.mockReset()
    notificationMocks.error.mockReset()
    apiMocks.deleteSpecification.mockReset()
    apiMocks.listSpecifications.mockReset()
  })

  it('reports the actual number of removed owned links', async () => {
    const wrapper = await mountList()

    await wrapper.get('[data-testid="delete-specification-button"]').trigger('click')
    await wrapper.get('[data-testid="confirm-delete-specification"]').trigger('click')
    await flushPromises()

    expect(reconciliationStore.deleteSpecification).toHaveBeenCalledWith('test_project', 'site', 'site_code', true)
    expect(notificationMocks.success).toHaveBeenCalledWith(
      'Specification deleted. 3 owned mapping link(s) and 2 local-only approval(s) removed.'
    )
    expect(notificationMocks.error).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="delete-dialog"]').exists()).toBe(false)
  })

  it('shows deletion failures without reporting success', async () => {
    reconciliationStore.deleteSpecification = vi.fn().mockRejectedValue({
      response: { data: { detail: 'Mapping sidecar changed; reload and retry.' } },
    })
    const wrapper = await mountList()

    await wrapper.get('[data-testid="delete-specification-button"]').trigger('click')
    await wrapper.get('[data-testid="confirm-delete-specification"]').trigger('click')
    await flushPromises()

    expect(notificationMocks.success).not.toHaveBeenCalled()
    expect(notificationMocks.error).toHaveBeenCalledWith(
      'Failed to delete specification: Mapping sidecar changed; reload and retry.'
    )
    expect(wrapper.find('[data-testid="delete-dialog"]').exists()).toBe(true)
  })

  it('shows unsupported saved types and property IDs instead of marking them valid', async () => {
    reconciliationStore.specifications = [
      {
        ...specification,
        remote: { service_type: 'taxon', columns: [] },
        property_mappings: { old_property: 'site_code' },
      },
    ]

    const wrapper = await mountList()
    await flushPromises()

    expect(wrapper.text()).toContain('taxon (unsupported)')
    expect(wrapper.text()).toContain("Remote type 'taxon' is not supported for reconciliation.")
    expect(wrapper.text()).not.toContain('Valid Configuration')
  })

  it('marks mappings for undeclared properties as unsupported', async () => {
    reconciliationStore.specifications = [
      {
        ...specification,
        property_mappings: { old_property: 'site_code' },
      },
    ]

    const wrapper = await mountList()
    await flushPromises()

    expect(wrapper.text()).toContain('site (unsupported)')
    expect(wrapper.text()).toContain("Property mapping 'old_property' not declared for remote type 'site'.")
  })

  it('shows an unknown status when the manifest cannot be checked', async () => {
    const wrapper = await mountList(null)
    await flushPromises()

    expect(wrapper.text()).toContain('site (unknown)')
    expect(wrapper.text()).toContain('Reconciliation service metadata has not been checked.')
    expect(wrapper.text()).not.toContain('Valid Configuration')
  })
})

describe('reconciliation store deletion result', () => {
  it('returns owned-entry counts and stores the catalog-shaped response', async () => {
    const { useReconciliationStore } = await vi.importActual<typeof import('@/stores/reconciliation')>(
      '@/stores/reconciliation'
    )
    setActivePinia(createPinia())
    const store = useReconciliationStore()
    const updatedCatalog = {
      version: '3.0' as const,
      service_url: 'http://localhost:8000',
      entities: { site: {} },
    }
    apiMocks.deleteSpecification.mockResolvedValue({
      ...updatedCatalog,
      removed_owned_links: 2,
      removed_owned_approvals: 1,
    })
    apiMocks.listSpecifications.mockResolvedValue([])

    const removedEntries = await store.deleteSpecification('test_project', 'site', 'site_code', true)

    expect(removedEntries).toEqual({ removedOwnedLinks: 2, removedOwnedApprovals: 1 })
    expect(store.reconciliationConfig).toEqual(updatedCatalog)
    expect(store.specifications).toEqual([])
  })
})
