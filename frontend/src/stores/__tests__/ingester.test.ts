import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { ingesterApi } from '@/api/ingester'
import { useIngesterStore } from '../ingester'
import type { IngestResponse, ProjectIngesterRequest, ValidateResponse } from '@/types/ingester'

vi.mock('@/api/ingester', () => ({
  ingesterApi: {
    listIngesters: vi.fn(),
    validate: vi.fn(),
    ingest: vi.fn(),
    validateProject: vi.fn(),
    ingestProject: vi.fn(),
  },
}))

const projectRequest: ProjectIngesterRequest = {
  project_name: 'pilot_bugs',
  submission_context: {
    submission_name: 'pilot_bugs_bugs',
    timestamp: '2026-10-19T12:00',
    datatype: 'bugs',
    identifier: 'PILOT_BUGS',
  },
}

const validResult: ValidateResponse = { is_valid: true, errors: [], warnings: [], infos: [] }
const ingestedResult: IngestResponse = { success: true, records_processed: 2, message: 'Bundle created' }
let nextRunId = 0

function requestWithRunId(runId: string, request = projectRequest): ProjectIngesterRequest {
  return {
    ...request,
    submission_context: {
      ...request.submission_context,
      run_id: runId,
    },
  }
}

describe('useIngesterStore project actions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    nextRunId = 0
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => `attempt-${++nextRunId}`) })
  })

  it('stores project validation results and clears previous state', async () => {
    const store = useIngesterStore()
    store.ingesters = [
      { key: 'sead_change_request', name: 'SEAD Change Request', description: '', version: '', supported_formats: [] },
    ]
    store.selectIngester('sead_change_request')
    store.error = 'Old error'
    store.validationResult = { is_valid: false, errors: ['Old result'], warnings: [], infos: [] }
    vi.mocked(ingesterApi.validateProject).mockResolvedValue(validResult)

    await store.validateProject(projectRequest)

    expect(ingesterApi.validateProject).toHaveBeenCalledWith(requestWithRunId('attempt-1'))
    expect(store.validationResult).toEqual(validResult)
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('stores project validation API errors and clears loading state', async () => {
    const store = useIngesterStore()
    store.ingesters = [
      { key: 'sead_change_request', name: 'SEAD Change Request', description: '', version: '', supported_formats: [] },
    ]
    store.selectIngester('sead_change_request')
    vi.mocked(ingesterApi.validateProject).mockRejectedValue({ response: { data: { detail: 'Project denied' } } })
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await store.validateProject(projectRequest)

    expect(store.validationResult).toBeNull()
    expect(store.error).toBe('Project denied')
    expect(store.loading).toBe(false)
  })

  it('stores project ingestion results and clears previous state', async () => {
    const store = useIngesterStore()
    store.ingesters = [
      { key: 'sead_change_request', name: 'SEAD Change Request', description: '', version: '', supported_formats: [] },
    ]
    store.selectIngester('sead_change_request')
    store.error = 'Old error'
    store.ingestionResult = { success: false, records_processed: 0, message: 'Old result' }
    vi.mocked(ingesterApi.ingestProject).mockResolvedValue(ingestedResult)

    await store.ingestProject(projectRequest)

    expect(ingesterApi.ingestProject).toHaveBeenCalledWith(requestWithRunId('attempt-1'))
    expect(store.ingestionResult).toEqual(ingestedResult)
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('stores project ingestion API errors and clears loading state', async () => {
    const store = useIngesterStore()
    store.ingesters = [
      { key: 'sead_change_request', name: 'SEAD Change Request', description: '', version: '', supported_formats: [] },
    ]
    store.selectIngester('sead_change_request')
    vi.mocked(ingesterApi.ingestProject).mockRejectedValue(new Error('Request failed'))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await store.ingestProject(projectRequest)

    expect(store.ingestionResult).toBeNull()
    expect(store.error).toBe('Request failed')
    expect(store.loading).toBe(false)
  })

  it('reuses attempt IDs through validation and retries, then resets after success or identity change', async () => {
    const store = useIngesterStore()
    store.ingesters = [
      { key: 'sead_change_request', name: 'SEAD Change Request', description: '', version: '', supported_formats: [] },
    ]
    store.selectIngester('sead_change_request')
    vi.mocked(ingesterApi.validateProject).mockResolvedValue(validResult)
    vi.mocked(ingesterApi.ingestProject)
      .mockResolvedValueOnce({ success: false, records_processed: 0, message: 'Binding Set confirmation incomplete' })
      .mockRejectedValueOnce(new Error('Temporary connection failure'))
      .mockResolvedValueOnce(ingestedResult)
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await store.validateProject(projectRequest)
    await store.ingestProject(projectRequest)
    await store.ingestProject(projectRequest)
    await store.ingestProject(projectRequest)

    expect(ingesterApi.validateProject).toHaveBeenCalledWith(requestWithRunId('attempt-1'))
    expect(ingesterApi.ingestProject).toHaveBeenNthCalledWith(1, requestWithRunId('attempt-1'))
    expect(ingesterApi.ingestProject).toHaveBeenNthCalledWith(2, requestWithRunId('attempt-1'))
    expect(ingesterApi.ingestProject).toHaveBeenNthCalledWith(3, requestWithRunId('attempt-1'))

    const changedIdentityRequest: ProjectIngesterRequest = {
      ...projectRequest,
      submission_context: { ...projectRequest.submission_context, identifier: 'PILOT_BUGS_2' },
    }
    vi.mocked(ingesterApi.validateProject).mockClear()
    await store.validateProject(changedIdentityRequest)
    expect(ingesterApi.validateProject).toHaveBeenCalledWith(requestWithRunId('attempt-2', changedIdentityRequest))

    vi.mocked(ingesterApi.validateProject).mockClear()
    await store.validateProject(projectRequest)
    expect(ingesterApi.validateProject).toHaveBeenCalledWith(requestWithRunId('attempt-3'))
  })

  it('starts a new project attempt when explicitly reset', async () => {
    const store = useIngesterStore()
    store.ingesters = [
      { key: 'sead_change_request', name: 'SEAD Change Request', description: '', version: '', supported_formats: [] },
    ]
    store.selectIngester('sead_change_request')
    vi.mocked(ingesterApi.validateProject).mockResolvedValue(validResult)

    await store.validateProject(projectRequest)
    store.resetProjectAttempt()
    await store.validateProject(projectRequest)

    expect(ingesterApi.validateProject).toHaveBeenNthCalledWith(1, requestWithRunId('attempt-1'))
    expect(ingesterApi.validateProject).toHaveBeenNthCalledWith(2, requestWithRunId('attempt-2'))
  })

  it('keeps file actions on the existing ingester methods', async () => {
    const store = useIngesterStore()
    store.ingesters = [
      { key: 'example_ingester', name: 'Example Ingester', description: '', version: '', supported_formats: ['xlsx'] },
    ]
    store.selectIngester('example_ingester')
    vi.mocked(ingesterApi.validate).mockResolvedValue(validResult)
    vi.mocked(ingesterApi.ingest).mockResolvedValue(ingestedResult)

    await store.validate({ source: 'input.xlsx' })
    await store.ingest({ source: 'input.xlsx', submission_name: 'test', data_types: 'bugs' })

    expect(ingesterApi.validate).toHaveBeenCalledWith('example_ingester', { source: 'input.xlsx' })
    expect(ingesterApi.ingest).toHaveBeenCalledWith('example_ingester', {
      source: 'input.xlsx',
      submission_name: 'test',
      data_types: 'bugs',
    })
    expect(ingesterApi.validateProject).not.toHaveBeenCalled()
    expect(ingesterApi.ingestProject).not.toHaveBeenCalled()
  })

  it('does not run project actions when Change Request is not selected', async () => {
    const store = useIngesterStore()
    store.ingesters = [
      { key: 'example_ingester', name: 'Example Ingester', description: '', version: '', supported_formats: ['xlsx'] },
    ]
    store.selectIngester('example_ingester')

    await store.validateProject(projectRequest)
    await store.ingestProject(projectRequest)

    expect(store.error).toBe('SEAD Change Request must be selected')
    expect(ingesterApi.validateProject).not.toHaveBeenCalled()
    expect(ingesterApi.ingestProject).not.toHaveBeenCalled()
  })
})
