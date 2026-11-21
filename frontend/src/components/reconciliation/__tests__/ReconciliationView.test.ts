import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { nextTick, reactive, toRefs } from 'vue'
import type { ExportToMappingOutcome } from '@/types'
import type { MappingEntityResponse } from '@/types/reconciliation'

import ReconciliationView from '../ReconciliationView.vue'

vi.mock('pinia', async () => {
  const actual = await vi.importActual<typeof import('pinia')>('pinia')

  return {
    ...actual,
    storeToRefs: (store: object) => toRefs(store),
  }
})

const serviceManifest = {
  defaultTypes: [
    { id: 'site', name: 'Site' },
    { id: 'taxon', name: 'Taxon' },
    { id: 'feature_type', name: 'Feature type' },
  ],
  reconciliation: { supportedTypes: ['site', 'feature_type'] },
  extend: { property_settings: [{ name: 'place_name', entity_types: ['site'] }] },
}

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
  mappingData: { test_project: { site: null as MappingEntityResponse | null } },
  mappingErrors: {},
  mappingLoading: {},
  specifications: [
    {
      entity_name: 'site',
      has_business_keys: true,
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
  getServiceManifest: vi.fn(async () => serviceManifest),
  loadEntityResolutionCatalog: vi.fn(async () => {}),
  loadSpecifications: vi.fn(async () => {}),
  loadPreviewData: vi.fn(async () => {}),
  loadMappingData: vi.fn(async () => {}),
  deleteReviewDecision: vi.fn(async () => {}),
  deleteMappingEntry: vi.fn(async () => ({ deleted_link: true, deleted_local_only_approval: false })),
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
        ReconciliationGrid: {
          props: ['previewData'],
          template:
            '<button data-testid="open-remove-saved-entry" @click="$emit(\'remove-saved-entry\', previewData[0])">Remove saved row data</button>',
        },
        SpecificationsList: {
          template:
            "<div><button data-testid=\"open-reconcile\" @click=\"$emit('reconcile', 'site', 'site_code')\">Open</button>" +
            "<button data-testid=\"open-review\" @click=\"$emit('review', 'site', 'site_code')\">Review</button></div>",
        },
        ReconciliationWorkspace: {
          props: ['previewRows', 'selectionDescriptor', 'serviceType'],
          template:
            '<div data-testid="workspace-stub"><button data-testid="workspace-stub-fallback" @click="$emit(\'fallback\')">Fallback</button></div>',
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
  await flushPromises()
  return wrapper
}

describe('ReconciliationView', () => {
  beforeEach(() => {
    reconciliationStore.loading = false
    reconciliationStore.previewData = { test_project: { site: { site_code: [] } } }
    reconciliationStore.previewErrors = {}
    reconciliationStore.specifications = [
      {
        entity_name: 'site',
        has_business_keys: true,
        target_field: 'site_code',
        source: null,
        property_mappings: {},
        remote: { service_type: 'site', columns: [] },
        auto_accept_threshold: 0.95,
        review_threshold: 0.7,
        mapping_count: 2,
        property_mapping_count: 0,
      },
    ]
    reconciliationStore.autoReconcile = vi.fn()
    reconciliationStore.getServiceManifest = vi.fn(async () => serviceManifest)
    reconciliationStore.reconciliationConfig.entities.site.site_code.remote.service_type = 'site'
    reconciliationStore.reconciliationConfig.entities.site.site_code.property_mappings = {}
    reconciliationStore.mappingData = { test_project: { site: null } }
    reconciliationStore.mappingErrors = {}
    reconciliationStore.mappingLoading = {}
    reconciliationStore.loadMappingData = vi.fn(async () => {})
    reconciliationStore.loadPreviewData = vi.fn(async () => {})
    reconciliationStore.loadEntityResolutionCatalog = vi.fn(async () => {})
    reconciliationStore.deleteReviewDecision = vi.fn(async () => {})
    reconciliationStore.deleteMappingEntry = vi.fn(async () => ({
      deleted_link: true,
      deleted_local_only_approval: false,
    }))
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

  it('opens the reconciliation help dialog from the review tab', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()
    const helpButton = wrapper.get('[data-testid="reconciliation-help-button"]')
    expect(helpButton.find('.mdi-help-circle-outline').exists()).toBe(true)
    await helpButton.trigger('click')
    await nextTick()

    expect(wrapper.get('[data-testid="reconciliation-help-dialog"]').text()).toContain('Quick workflow')
    expect(wrapper.get('[data-testid="reconciliation-help-dialog"]').text()).toContain(
      'Accepting a candidate does not change the current ID until you use Export to Mapping.'
    )
  })

  it('allows dismissing the export guidance and candidate search summary', async () => {
    reconciliationStore.autoReconcile = vi.fn().mockResolvedValue({
      proposed: 3,
      unmatched: 1,
      total: 4,
      candidates: {},
      errors: [],
    })
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    const exportGuidance = wrapper.get('[data-testid="reconciliation-export-info"]')
    await exportGuidance.get('button').trigger('click')
    expect(wrapper.find('[data-testid="reconciliation-export-info"]').exists()).toBe(false)

    await wrapper.get('[data-testid="find-candidates-button"]').trigger('click')
    await flushPromises()
    const searchSummary = wrapper.get('[data-testid="matching-result"]')
    await searchSummary.get('button').trigger('click')
    expect(wrapper.find('[data-testid="matching-result"]').exists()).toBe(false)

    await wrapper.get('[data-testid="find-candidates-button"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="matching-result"]').exists()).toBe(true)
  })

  it('exports accepted links and new-row approvals with separate counts', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    const exportButton = wrapper.get('[data-testid="export-to-mapping-button"]')

    await exportButton.trigger('click')
    await flushPromises()

    expect(exportButton.attributes('disabled')).toBeUndefined()
    expect(reconciliationStore.exportToMapping).toHaveBeenCalledWith('test_project', 'site', 'site_code')
    expect(reconciliationStore.loadMappingData).toHaveBeenCalledWith('test_project', 'site', 'site_code')
    expect(wrapper.text()).toContain(
      '2 link(s) exported; 1 stale link(s) removed; 1 New-row approval recorded; ' +
        '2 stale New-row approvals removed; 1 protected link(s) skipped.'
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

  it.each(['0', '-1'])('rejects non-positive manual target ID %s', async (targetId) => {
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()
    await wrapper.get('[data-testid="manual-link-open"]').trigger('click')
    await nextTick()

    await wrapper.get('[data-testid="manual-link-key"] input').setValue('A/B')
    await wrapper.get('[data-testid="manual-link-target-id"] input').setValue(targetId)
    await wrapper.get('[data-testid="manual-link-submit"]').trigger('click')
    await nextTick()

    expect(reconciliationStore.putManualMapping).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="manual-link-error"]').text()).toContain('positive whole-number target ID')
  })

  it('saves a manual sidecar link for an explicit encoded key and positive target ID', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()
    await wrapper.get('[data-testid="manual-link-open"]').trigger('click')
    await nextTick()

    await wrapper.get('[data-testid="manual-link-key"] input').setValue('A/B')
    await wrapper.get('[data-testid="manual-link-target-id"] input').setValue('12')
    await wrapper.get('[data-testid="manual-link-submit"]').trigger('click')
    await flushPromises()

    expect(reconciliationStore.putManualMapping).toHaveBeenCalledWith(
      'test_project',
      'site',
      'A/B',
      12,
      undefined,
      'site_code'
    )
    expect(wrapper.text()).toContain('Manual link saved')
  })

  it('shows the saved records and clears only the selected review decision', async () => {
    reconciliationStore.previewData = {
      test_project: {
        site: {
          site_code: [
            {
              local_key_value: 'A',
              site_code: 'Same',
              status: 'accepted',
              target_id: 101,
              candidate_id: 'https://w3id.org/sead/id/site/101',
            },
          ],
        },
      },
    }
    reconciliationStore.mappingData = {
      test_project: {
        site: {
          entity_name: 'site',
          local_key: 'site_code',
          public_id: 'site_id',
          entity_type: 'primary',
          protection_target_field: 'site_code',
          links: {
            A: {
              target_id: 101,
              source: 'reconciliation',
              created_at: '2026-10-30T00:00:00Z',
              committed_at: '2026-10-30T00:00:00Z',
              owner: { entity_name: 'site', target_field: 'site_code' },
              created_by: 'reconciliation',
              protected: false,
            },
          },
          local_only_approvals: {},
        },
      },
    }
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await wrapper.get('[data-testid="open-remove-saved-entry"]').trigger('click')
    await nextTick()

    expect(wrapper.get('[data-testid="remove-decision-details"]').text()).toContain('accepted')
    expect(wrapper.get('[data-testid="remove-decision-details"]').text()).toContain('Target ID 101')
    expect(wrapper.get('[data-testid="remove-sidecar-details"]').text()).toContain('source reconciliation')
    expect(wrapper.get('[data-testid="remove-sidecar-details"]').text()).toContain('site.site_code')
    expect(wrapper.get('[data-testid="delete-sidecar-entry"]').attributes('disabled')).toBeUndefined()

    await wrapper.get('[data-testid="clear-review-decision"]').trigger('click')
    await flushPromises()

    expect(reconciliationStore.deleteReviewDecision).toHaveBeenCalledWith('test_project', 'site', 'site_code', 'A')
    expect(reconciliationStore.deleteMappingEntry).not.toHaveBeenCalled()
    expect(reconciliationStore.loadPreviewData).toHaveBeenCalledWith('test_project', 'site', 'site_code')
    expect(wrapper.text()).toContain('Review decision cleared; sidecar mapping unchanged.')
  })

  it('requires explicit confirmation before deleting a protected sidecar entry', async () => {
    reconciliationStore.previewData = {
      test_project: {
        site: { site_code: [{ local_key_value: 'A', site_code: 'Same', status: 'accepted', target_id: 101 }] },
      },
    }
    reconciliationStore.mappingData = {
      test_project: {
        site: {
          entity_name: 'site',
          local_key: 'site_code',
          public_id: 'site_id',
          entity_type: 'primary',
          protection_target_field: 'site_code',
          links: {
            A: {
              target_id: 99,
              source: 'manual',
              created_at: '2026-10-30T00:00:00Z',
              committed_at: '2026-10-30T00:00:00Z',
              created_by: 'user',
              protected: true,
            },
          },
          local_only_approvals: {},
        },
      },
    }
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await wrapper.get('[data-testid="open-remove-saved-entry"]').trigger('click')
    await nextTick()

    expect(wrapper.get('[data-testid="delete-sidecar-entry"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="confirm-protected-sidecar"] input[type="checkbox"]').setValue(true)
    await nextTick()
    expect(wrapper.get('[data-testid="delete-sidecar-entry"]').attributes('disabled')).toBeUndefined()

    await wrapper.get('[data-testid="delete-sidecar-entry"]').trigger('click')
    await flushPromises()

    expect(reconciliationStore.deleteMappingEntry).toHaveBeenCalledWith('test_project', 'site', 'A', 'site_code', true)
    expect(reconciliationStore.deleteReviewDecision).not.toHaveBeenCalled()
    expect(reconciliationStore.loadMappingData).toHaveBeenCalledWith('test_project', 'site', 'site_code')
  })

  it('reports partial failure when Clear both removes only the decision', async () => {
    reconciliationStore.previewData = {
      test_project: {
        site: { site_code: [{ local_key_value: 'A', site_code: 'Same', status: 'accepted', target_id: 101 }] },
      },
    }
    reconciliationStore.mappingData = {
      test_project: {
        site: {
          entity_name: 'site',
          local_key: 'site_code',
          public_id: 'site_id',
          entity_type: 'primary',
          protection_target_field: 'site_code',
          links: {
            A: {
              target_id: 101,
              source: 'reconciliation',
              created_at: '2026-10-30T00:00:00Z',
              committed_at: '2026-10-30T00:00:00Z',
              owner: { entity_name: 'site', target_field: 'site_code' },
              created_by: 'reconciliation',
              protected: false,
            },
          },
          local_only_approvals: {},
        },
      },
    }
    reconciliationStore.deleteMappingEntry = vi.fn().mockRejectedValue(new Error('Sidecar changed'))
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await wrapper.get('[data-testid="open-remove-saved-entry"]').trigger('click')
    await nextTick()
    await wrapper.get('[data-testid="clear-both-entries"]').trigger('click')
    await flushPromises()

    expect(reconciliationStore.deleteReviewDecision).toHaveBeenCalledWith('test_project', 'site', 'site_code', 'A')
    expect(reconciliationStore.deleteMappingEntry).toHaveBeenCalledWith('test_project', 'site', 'A', 'site_code', false)
    expect(wrapper.text()).toContain('Review decision cleared; sidecar mapping remains.')
    expect(wrapper.text()).toContain('Sidecar mapping remains: Sidecar changed')
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

  it('blocks saved mappings that the current manifest does not declare', async () => {
    reconciliationStore.reconciliationConfig.entities.site.site_code.property_mappings = { old_property: 'site_name' }
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    expect(wrapper.get('[data-testid="matching-blocked"]').text()).toContain(
      "Property mapping 'old_property' not declared for remote type 'site'."
    )
    expect(wrapper.get('[data-testid="find-candidates-button"]').attributes('disabled')).toBeDefined()
    expect(reconciliationStore.autoReconcile).not.toHaveBeenCalled()
  })

  it('warns and avoids reconciliation requests for entities without business keys', async () => {
    reconciliationStore.specifications[0]!.has_business_keys = false
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    expect(wrapper.get('[data-testid="matching-blocked"]').text()).toContain(
      "Entity 'site' has no business keys configured."
    )
    expect(wrapper.get('[data-testid="find-candidates-button"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-testid="manual-link-open"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-testid="preview-error"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="mapping-error"]').exists()).toBe(false)
    expect(reconciliationStore.loadPreviewData).not.toHaveBeenCalled()
    expect(reconciliationStore.loadMappingData).not.toHaveBeenCalled()
    expect(reconciliationStore.autoReconcile).not.toHaveBeenCalled()
  })

  it('blocks candidate search when the manifest request fails', async () => {
    reconciliationStore.getServiceManifest = vi.fn().mockRejectedValue(new Error('Manifest unavailable'))
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    expect(wrapper.get('[data-testid="matching-blocked"]').text()).toContain('Manifest unavailable')
    expect(wrapper.get('[data-testid="find-candidates-button"]').attributes('disabled')).toBeDefined()
    expect(reconciliationStore.autoReconcile).not.toHaveBeenCalled()
  })

  it('allows candidate search for a supported zero-property type', async () => {
    reconciliationStore.reconciliationConfig.entities.site.site_code.remote.service_type = 'feature_type'
    reconciliationStore.reconciliationConfig.entities.site.site_code.property_mappings = {}
    reconciliationStore.autoReconcile = vi.fn().mockResolvedValue({
      proposed: 0,
      unmatched: 0,
      total: 0,
      candidates: {},
      errors: [],
    })
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()
    const button = wrapper.get('[data-testid="find-candidates-button"]')
    expect(button.attributes('disabled')).toBeUndefined()
    await button.trigger('click')
    await flushPromises()

    expect(reconciliationStore.autoReconcile).toHaveBeenCalledWith('test_project', 'site', 'site_code', 0.95, 0.7)
  })

  it('does not load the preview until the review tab is opened', async () => {
    reconciliationStore.loadPreviewData = vi.fn(async () => {})
    const wrapper = await mountView()

    expect(reconciliationStore.loadPreviewData).not.toHaveBeenCalled()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await flushPromises()

    expect(reconciliationStore.loadPreviewData).toHaveBeenCalledWith('test_project', 'site', 'site_code')
  })

  it('loads the preview once when the review tab is reopened', async () => {
    reconciliationStore.loadPreviewData = vi.fn(async () => {})
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await flushPromises()

    expect(reconciliationStore.loadPreviewData).toHaveBeenCalledTimes(1)
  })

  it('shows a loading state instead of the empty state while the preview request is in flight', async () => {
    let resolvePreview: (() => void) | undefined
    reconciliationStore.loadPreviewData = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolvePreview = resolve
        })
    )
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    expect(wrapper.find('[data-testid="preview-loading"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('No Preview Rows')

    resolvePreview?.()
    await flushPromises()

    expect(wrapper.find('[data-testid="preview-loading"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('No Preview Rows')
  })

  it('opens the review workspace without running Find Candidates', async () => {
    reconciliationStore.previewData = {
      test_project: {
        site: { site_code: [{ local_key_value: 'A', site_code: 'Same', status: null, errors: [] }] },
      },
    }
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-review"]').trigger('click')
    await nextTick()

    expect(wrapper.find('[data-testid="workspace-stub"]').exists()).toBe(true)
    expect(reconciliationStore.autoReconcile).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="find-candidates-button"]').exists()).toBe(true)
  })

  it('returns to the review grid when the workspace falls back', async () => {
    reconciliationStore.previewData = {
      test_project: {
        site: { site_code: [{ local_key_value: 'A', site_code: 'Same', status: null, errors: [] }] },
      },
    }
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-review"]').trigger('click')
    await nextTick()
    expect(wrapper.find('[data-testid="workspace-stub"]').exists()).toBe(true)

    await wrapper.get('[data-testid="workspace-stub-fallback"]').trigger('click')
    await nextTick()

    expect(wrapper.find('[data-testid="workspace-stub"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="open-remove-saved-entry"]').exists()).toBe(true)
  })

  it('states that accepted exports are verified and saving is separate from exporting', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-testid="open-reconcile"]').trigger('click')
    await nextTick()

    const guidance = wrapper.get('[data-testid="reconciliation-export-info"]').text()
    expect(guidance).toContain('Accepted links are written only after that check succeeds')
    expect(guidance).toContain('Saving a decision does not export a link')
    expect(guidance).not.toContain('remain unverified until you export again')
    expect(wrapper.find('[data-testid="export-to-mapping-button"]').exists()).toBe(true)
  })
})
