import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { nextTick, reactive, toRefs } from 'vue'
import type { ExportToMappingOutcome } from '@/types'

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
    version: '3.0',
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
  previewData: { test_project: { site: { site_code: [] as any[] } } },
  previewErrors: {},
  mappingData: { test_project: { site: null } },
  mappingErrors: {},
  mappingLoading: {},
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
  loadMappingData: vi.fn(async () => {}),
  putManualMapping: vi.fn(async () => ({})),
  saveEntityResolutionCatalogRaw: vi.fn(async () => {}),
  exportToMapping: vi.fn(async () => ({
    exported: 2,
    removed: 1,
    exported_local_only_approvals: 1,
    removed_local_only_approvals: 2,
    skipped_manual: 1,
    entity: 'site',
    field: 'site_code',
    outcomes: [] as ExportToMappingOutcome[],
  })),
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

async function mountView() {
  const wrapper = mount(ReconciliationView, {
    global: {
      plugins: [vuetify],
      stubs: {
        ReconciliationGrid: { template: '<div data-testid="reconciliation-grid" />' },
        SpecificationsList: {
          template:
            "<button data-testid=\"open-reconcile\" @click=\"$emit('reconcile', 'site', 'site_code')\">Open</button>",
        },
        YamlEditor: {
          props: ['mode'],
          template: '<div data-testid="yaml-editor" :data-mode="mode" />',
        },
        VTabs: { template: '<div data-testid="tabs"><slot /></div>' },
        VTab: { template: '<button type="button"><slot /></button>' },
        VWindow: { template: '<div data-testid="window"><slot /></div>' },
        VWindowItem: { template: '<div><slot /></div>' },
        VDialog: {
          props: ['modelValue'],
          template: '<div v-if="modelValue" data-testid="dialog-content"><slot /></div>',
        },
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
    reconciliationStore.previewData = { test_project: { site: { site_code: [] } } }
    reconciliationStore.previewErrors = {}
    reconciliationStore.autoReconcile = vi.fn()
    reconciliationStore.mappingData = { test_project: { site: null } }
    reconciliationStore.mappingErrors = {}
    reconciliationStore.mappingLoading = {}
    reconciliationStore.loadMappingData = vi.fn(async () => {})
    reconciliationStore.exportToMapping = vi.fn(async () => ({
      exported: 2,
      removed: 1,
      exported_local_only_approvals: 1,
      removed_local_only_approvals: 2,
      skipped_manual: 1,
      entity: 'site',
      field: 'site_code',
      outcomes: [] as ExportToMappingOutcome[],
    }))
    reconciliationStore.putManualMapping = vi.fn(async () => ({}))
  })

  it('uses reconciliation YAML intelligence for the catalog editor', async () => {
    const wrapper = await mountView()

    expect(wrapper.get('[data-testid="yaml-editor"]').attributes('data-mode')).toBe('reconciliation')
  })

  it('exports accepted links and local-only approvals with separate counts', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    const exportButton = wrapper.get('[data-testid="export-to-mapping-button"]')

    await exportButton.trigger('click')
    await flushPromises()

    expect(exportButton.attributes('disabled')).toBeUndefined()
    expect(reconciliationStore.exportToMapping).toHaveBeenCalledWith('test_project', 'site', 'site_code')
    expect(reconciliationStore.loadMappingData).toHaveBeenCalledWith('test_project', 'site')
    expect(wrapper.text()).toContain(
      '2 link(s) exported; 1 stale link(s) removed; 1 local-only approval(s) exported; '
      + '2 stale local-only approval(s) removed; 1 protected link(s) skipped.'
    )
  })

  it('reports per-key rejected and unverified export outcomes', async () => {
    reconciliationStore.exportToMapping = vi.fn(async () => ({
      exported: 1,
      removed: 1,
      exported_local_only_approvals: 0,
      removed_local_only_approvals: 0,
      skipped_manual: 0,
      entity: 'site',
      field: 'site_code',
      outcomes: [
        { local_key_value: 'A', outcome: 'not_found' as const, reason: 'Candidate is absent.' },
        { local_key_value: 'B', outcome: 'unverified' as const, reason: 'Authority Service is offline.' },
      ],
    }))
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await wrapper.get('[data-testid="export-to-mapping-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Not exported: A: Candidate is absent.')
    expect(wrapper.text()).toContain('Unverified: B: Authority Service is offline.')
  })

  it('reports successful export when refreshing mapping status fails', async () => {
    reconciliationStore.loadMappingData = vi.fn().mockRejectedValue(new Error('Mapping refresh unavailable'))
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await wrapper.get('[data-testid="export-to-mapping-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Export succeeded, but mapping status could not be refreshed')
    expect(wrapper.text()).toContain('Mapping refresh unavailable')
  })

  it('reports an export conflict without showing a successful result', async () => {
    reconciliationStore.exportToMapping = vi.fn().mockRejectedValue({
      response: { data: { detail: { message: 'Another specification owns this key' } } },
    })
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await wrapper.get('[data-testid="export-to-mapping-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Reconciliation export failed: Another specification owns this key')
    expect(wrapper.text()).not.toContain('link(s) exported')
  })

  it('saves a manual sidecar link for an explicit encoded key and accepts target ID zero', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()
    await wrapper.get('[data-testid="manual-link-open"]').trigger('click')
    await nextTick()

    await wrapper.get('[data-testid="manual-link-key"] input').setValue('A/B')
    await wrapper.get('[data-testid="manual-link-target-id"] input').setValue('0')
    await wrapper.get('[data-testid="manual-link-submit"]').trigger('click')
    await nextTick()
    await nextTick()

    expect(reconciliationStore.putManualMapping).toHaveBeenCalledWith('test_project', 'site', 'A/B', 0, undefined)
    expect(wrapper.text()).toContain('Manual link saved')
  })

  it('shows a preview load failure instead of treating it as an empty result', async () => {
    reconciliationStore.previewErrors = { test_project: { site: { site_code: 'Preview service unavailable' } } }
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    expect(wrapper.get('[data-testid="preview-error"]').text()).toContain('Preview service unavailable')
    expect(wrapper.text()).not.toContain('No Preview Rows')
  })

  it('shows candidate-search failures without a success result', async () => {
    reconciliationStore.autoReconcile = vi.fn().mockRejectedValue(new Error('Matching service unavailable'))
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await wrapper.get('[data-testid="find-candidates-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="matching-error"]').text()).toContain('Matching service unavailable')
    expect(wrapper.find('[data-testid="matching-result"]').exists()).toBe(false)
  })

  it('reports candidate-search counts and row-specific matching errors', async () => {
    reconciliationStore.autoReconcile = vi.fn().mockResolvedValue({
      proposed: 1,
      unmatched: 2,
      total: 4,
      candidates: {},
      errors: [{ row_index: 2, local_key_value: 'A', message: 'Missing required key' }],
    })
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await wrapper.get('[data-testid="find-candidates-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="matching-result"]').text()).toContain('considered 4 rows')
    expect(wrapper.get('[data-testid="matching-result"]').text()).toContain('found no candidates for 2 rows')
    expect(wrapper.get('[data-testid="matching-result"]').text()).toContain('Row 3 (A): Missing required key')
  })
})
