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
    getSelectionCapabilities: vi.fn(),
    searchSelection: vi.fn(),
    browseSelection: vi.fn(),
    saveDecisionBatch: vi.fn(),
  },
}))

vi.mock('@/api/client', () => ({ apiClient: mocks.apiClient }))
vi.mock('@/api/reconciliation', () => ({
  reconciliationSpecApi: mocks.reconciliationSpecApi,
  reconciliationServiceApi: mocks.reconciliationServiceApi,
}))

import { useReconciliationStore } from '../reconciliation'

/** Install an in-memory Storage on the test window, because jsdom exposes none. */
function installMemoryStorage() {
  const entries = new Map<string, string>()
  const storage: Storage = {
    get length() {
      return entries.size
    },
    clear: () => entries.clear(),
    getItem: (key: string) => entries.get(key) ?? null,
    key: (index: number) => Array.from(entries.keys())[index] ?? null,
    removeItem: (key: string) => {
      entries.delete(key)
    },
    setItem: (key: string, value: string) => {
      entries.set(key, value)
    },
  }
  Object.defineProperty(window, 'localStorage', { configurable: true, value: storage })
  return { storage, entries }
}

describe('reconciliation store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    installMemoryStorage()
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

  it('saves staged decisions in one batch and patches only the rows it returned', async () => {
    const store = useReconciliationStore()
    const rows = [
      { local_key_value: 'A', site_name: 'Alpha', status: 'proposed' as const, errors: ['Old reference error'] },
      { local_key_value: 'B', site_name: 'Beta', status: null as null },
      { local_key_value: 'C', site_name: 'Gamma', status: 'accepted' as const, target_id: 9 },
    ]
    store.previewData = { project: { site: { site_name: rows } } }
    mocks.reconciliationServiceApi.saveDecisionBatch.mockResolvedValue({
      saved: [
        {
          local_key_value: 'A',
          status: 'accepted',
          target_id: 101,
          candidate_id: 'https://w3id.org/sead/id/feature_type/101',
          notes: 'Looked right',
          last_modified: '2026-11-20T00:00:00Z',
        },
      ],
      counts: {
        saved: 1,
        accepted: 1,
        local_only: 0,
        specification: { accepted: 2, local_only: 0, proposed: 0, rejected: 0, total: 2 },
      },
    })

    const result = await store.saveDecisionBatch('project', 'site', 'site_name', [
      {
        local_key_value: 'A',
        displayed_values: { site_name: 'Alpha' },
        status: 'accepted',
        target_id: 101,
        candidate_id: 'https://w3id.org/sead/id/feature_type/101',
        notes: 'Looked right',
      },
    ])

    expect(mocks.reconciliationServiceApi.saveDecisionBatch).toHaveBeenCalledTimes(1)
    expect(mocks.reconciliationServiceApi.saveDecisionBatch).toHaveBeenCalledWith('project', 'site', 'site_name', {
      drafts: [
        {
          local_key_value: 'A',
          displayed_values: { site_name: 'Alpha' },
          status: 'accepted',
          target_id: 101,
          candidate_id: 'https://w3id.org/sead/id/feature_type/101',
          notes: 'Looked right',
        },
      ],
    })
    // The preview is patched, never reloaded, and untouched rows keep their state.
    expect(mocks.reconciliationServiceApi.getPreview).not.toHaveBeenCalled()
    const patched = store.previewData.project?.site?.site_name ?? []
    expect(patched[0]).toMatchObject({ status: 'accepted', target_id: 101, errors: [] })
    expect(patched[1]).toEqual(rows[1])
    expect(patched[2]).toEqual(rows[2])
    expect(result.counts.specification.total).toBe(2)
  })

  it('keeps the preview unchanged when the batch is rejected', async () => {
    const store = useReconciliationStore()
    const rows = [{ local_key_value: 'A', site_name: 'Alpha', status: null as null }]
    store.previewData = { project: { site: { site_name: rows } } }
    mocks.reconciliationServiceApi.saveDecisionBatch.mockRejectedValue({
      response: {
        data: { detail: { message: 'rejected', issues: [{ code: 'row_changed', message: 'Column changed' }] } },
      },
    })

    await expect(
      store.saveDecisionBatch('project', 'site', 'site_name', [
        { local_key_value: 'A', displayed_values: { site_name: 'Alpha' }, status: 'local-only' },
      ])
    ).rejects.toBeTruthy()

    expect(store.previewData.project?.site?.site_name).toEqual(rows)
    expect(store.error).toBe('rejected')
  })

  it('compares only the drafted keys against the loaded decision state', () => {
    const store = useReconciliationStore()
    const loaded = {
      A: { status: 'accepted' as const, target_id: 5, candidate_id: 'id/5', notes: null },
      B: { status: 'local-only' as const, target_id: null, candidate_id: null, notes: null },
    }
    const current = {
      A: { status: 'accepted' as const, target_id: 6, candidate_id: 'id/6', notes: null },
      B: { status: 'local-only' as const, target_id: null, candidate_id: null, notes: null },
      C: { status: 'accepted' as const, target_id: 7, candidate_id: 'id/7', notes: null },
    }

    expect(store.changedDecisionKeys(loaded, current, ['A', 'B'])).toEqual(['A'])
    expect(store.changedDecisionKeys(loaded, current, ['C'])).toEqual(['C'])
    expect(store.changedDecisionKeys(loaded, current, ['A', 'B', 'C'])).toEqual(['A', 'C'])
    expect(store.changedDecisionKeys(loaded, current, [])).toEqual([])
  })

  it('reads saved decisions for comparison without replacing the in-memory catalog', async () => {
    const store = useReconciliationStore()
    store.reconciliationConfig = { version: '3.0', service_url: 'http://service', entities: {} } as never
    mocks.apiClient.get.mockResolvedValue({
      data: {
        version: '3.0',
        service_url: '',
        entities: {
          site: {
            site_name: {
              remote: { service_type: 'feature_type' },
              property_mappings: {},
              auto_accept_threshold: 0.95,
              review_threshold: 0.7,
              mapping: [
                {
                  local_key_value: 'A',
                  source_value: 'Alpha',
                  status: 'accepted',
                  target_id: 101,
                  candidate_id: 'https://w3id.org/sead/id/feature_type/101',
                  notes: 'kept',
                  candidates: [],
                },
              ],
            },
          },
        },
      },
    })

    const states = await store.fetchSavedDecisionStates('project', 'site', 'site_name')

    expect(states.A).toEqual({
      status: 'accepted',
      target_id: 101,
      candidate_id: 'https://w3id.org/sead/id/feature_type/101',
      notes: 'kept',
    })
    expect(store.reconciliationConfig).toEqual({ version: '3.0', service_url: 'http://service', entities: {} })
  })

  it('keeps browser drafts scoped, versioned, and separate per specification', () => {
    const store = useReconciliationStore()
    const draft = {
      focusedKey: 'A',
      mode: 'search' as const,
      searchQuery: 'bronze',
      browseText: '',
      browseFieldFilters: {},
      sortField: 'name',
      sortDirection: 'asc' as const,
      rows: { A: { query: 'bronze', notes: 'same label', decision: null, displayedValues: { site_name: 'Same' } } },
    }

    expect(store.saveWorkspaceDraft('project', 'site', 'site_name', draft)).toBe(true)

    expect(store.loadWorkspaceDraft('project', 'site', 'site_name').status).toBe('restored')
    // The same labels and keys in another project or field must not inherit the draft.
    expect(store.loadWorkspaceDraft('other-project', 'site', 'site_name').status).toBe('empty')
    expect(store.loadWorkspaceDraft('project', 'site', 'site_code').status).toBe('empty')
  })

  it('clears an outdated or malformed draft instead of applying it', () => {
    const store = useReconciliationStore()
    localStorage.setItem(
      'shapeshifter.reconciliation.workspace',
      JSON.stringify({ version: 0, scopes: { [JSON.stringify(['project', 'site', 'site_name'])]: {} } })
    )

    expect(store.loadWorkspaceDraft('project', 'site', 'site_name').status).toBe('invalid')
    expect(localStorage.getItem('shapeshifter.reconciliation.workspace')).toBeNull()

    localStorage.setItem(
      'shapeshifter.reconciliation.workspace',
      JSON.stringify({
        version: 1,
        scopes: { [JSON.stringify(['project', 'site', 'site_name'])]: { mode: 'search', rows: 'not-an-object' } },
      })
    )

    expect(store.loadWorkspaceDraft('project', 'site', 'site_name').status).toBe('invalid')
    expect(store.loadWorkspaceDraft('project', 'site', 'site_name').status).toBe('empty')
  })

  it('reports a browser storage failure instead of pretending the draft is durable', () => {
    const store = useReconciliationStore()
    const setItem = vi.spyOn(window.localStorage, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError')
    })
    try {
      expect(
        store.saveWorkspaceDraft('project', 'site', 'site_name', {
          focusedKey: null,
          mode: 'search',
          searchQuery: '',
          browseText: '',
          browseFieldFilters: {},
          sortField: 'name',
          sortDirection: 'asc',
          rows: {},
        })
      ).toBe(false)
    } finally {
      setItem.mockRestore()
    }
  })

  it('invalidates cached mapping data after a successful reconciliation export', async () => {
    const store = useReconciliationStore()
    store.mappingData = {
      project: {
        site: {
          entity_name: 'site',
          local_key: 'site_code',
          public_id: 'site_id',
          entity_type: 'primary',
          links: {},
        },
      },
    }
    const result = {
      exported: 1,
      removed: 0,
      exported_local_only_approvals: 0,
      removed_local_only_approvals: 0,
      skipped_manual: 0,
      entity: 'site',
      field: 'site_code',
      outcomes: [{ local_key_value: 'A', outcome: 'verified' as const }],
    }
    mocks.reconciliationServiceApi.exportToMapping.mockResolvedValue(result)

    await expect(store.exportToMapping('project', 'site', 'site_code')).resolves.toEqual(result)

    expect(mocks.reconciliationServiceApi.exportToMapping).toHaveBeenCalledWith('project', 'site', 'site_code')
    expect(store.mappingData.project?.site).toBeUndefined()
  })
})
