import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  reconciliationSpecApi: {
    listSpecifications: vi.fn(),
    createSpecification: vi.fn(),
    updateSpecification: vi.fn(),
    deleteSpecification: vi.fn(),
    getAvailableFields: vi.fn(),
    getMappingCount: vi.fn(),
  },
  reconciliationServiceApi: {
    getPreview: vi.fn(),
    autoReconcile: vi.fn(),
    updateDecision: vi.fn(),
    deleteDecision: vi.fn(),
    getEntityMapping: vi.fn(),
    putManualMapping: vi.fn(),
    suggestEntities: vi.fn(),
    checkHealth: vi.fn(),
    getManifest: vi.fn(),
    exportToMapping: vi.fn(),
  },
}))

vi.mock('@/api/client', () => ({ apiClient: mocks.apiClient }))
vi.mock('@/api/reconciliation', () => ({
  reconciliationSpecApi: mocks.reconciliationSpecApi,
  reconciliationServiceApi: mocks.reconciliationServiceApi,
}))

import { useReconciliationStore } from '../reconciliation'

describe('reconciliation store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mocks.apiClient.get.mockResolvedValue({ data: { version: '3.0', service_url: '', entities: {} } })
    mocks.reconciliationServiceApi.getPreview.mockResolvedValue([])
    mocks.reconciliationServiceApi.getEntityMapping.mockResolvedValue({
      entity_name: 'site',
      local_key: 'site_code',
      public_id: 'site_id',
      entity_type: 'primary',
      links: {},
    })
  })

  it('keeps preview rows scoped to project, entity, and target', async () => {
    const store = useReconciliationStore()
    const first = [{ local_key_value: 'A', site_name: 'Same', status: 'proposed' as const }]
    const second = [{ local_key_value: 'A', site_code: 'Same', status: 'accepted' as const, target_id: 101 }]
    mocks.reconciliationServiceApi.getPreview.mockResolvedValueOnce(first).mockResolvedValueOnce(second)

    await store.loadPreviewData('project', 'site', 'site_name')
    await store.loadPreviewData('project', 'site', 'site_code')

    expect(store.previewData.project?.site?.site_name).toEqual(first)
    expect(store.previewData.project?.site?.site_code).toEqual(second)
  })

  it('preserves cached preview rows and reports a failed reload', async () => {
    const store = useReconciliationStore()
    const cached = [
      {
        local_key_value: 'A',
        status: 'proposed' as const,
        candidates: [{ id: 'site/101', name: 'Site', score: 82, type: [] }],
      },
    ]
    mocks.reconciliationServiceApi.getPreview.mockResolvedValueOnce(cached).mockRejectedValueOnce(new Error('HTTP 500'))

    await store.loadPreviewData('project', 'site', 'site_name')
    await expect(store.loadPreviewData('project', 'site', 'site_name')).rejects.toThrow('HTTP 500')

    expect(store.previewData.project?.site?.site_name).toEqual(cached)
    expect(store.previewErrors.project?.site?.site_name).toBe('HTTP 500')
  })

  it('submits keyed decisions and reloads the catalog and preview', async () => {
    const store = useReconciliationStore()
    const decision = { local_key_value: 'A', status: 'accepted' as const, target_id: 101 }
    const catalog = { version: '3.0' as const, service_url: '', entities: {} }
    const rows = [{ local_key_value: 'A', status: 'accepted' as const, confidence: 0.82 }]
    mocks.reconciliationServiceApi.updateDecision.mockResolvedValue(catalog)
    mocks.apiClient.get.mockResolvedValue({ data: catalog })
    mocks.reconciliationServiceApi.getPreview.mockResolvedValue(rows)

    await store.updateMapping('project', 'site', 'site_name', decision)

    expect(mocks.reconciliationServiceApi.updateDecision).toHaveBeenCalledWith('project', 'site', 'site_name', decision)
    expect(store.previewData.project?.site?.site_name).toEqual(rows)
    expect(store.reconciliationConfig).toEqual(catalog)
  })

  it('saves a zero-valued manual target and reloads the sidecar', async () => {
    const store = useReconciliationStore()
    const sidecar = {
      entity_name: 'site',
      local_key: 'site_code',
      public_id: 'site_id',
      entity_type: 'primary',
      links: {
        'A/B': {
          target_id: 0,
          source: 'manual',
          created_at: '2026-10-30T00:00:00Z',
          committed_at: '2026-10-30T00:00:00Z',
          created_by: 'user',
        },
      },
    }
    mocks.reconciliationServiceApi.putManualMapping.mockResolvedValue({
      local_key_value: 'A/B',
      link: sidecar.links['A/B'],
    })
    mocks.reconciliationServiceApi.getEntityMapping.mockResolvedValue(sidecar)

    await store.putManualMapping('project', 'site', 'A/B', 0, 'Manual choice')

    expect(mocks.reconciliationServiceApi.putManualMapping).toHaveBeenCalledWith('project', 'site', 'A/B', {
      target_id: 0,
      notes: 'Manual choice',
    })
    expect(mocks.reconciliationServiceApi.getEntityMapping).toHaveBeenCalledWith('project', 'site')
    expect(store.mappingData.project?.site?.links?.['A/B']?.target_id).toBe(0)
  })
})
