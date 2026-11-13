import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ingesterApi } from '../ingester'
import type {
  IngestRequest,
  IngestResponse,
  ProjectIngesterRequest,
  ValidateRequest,
  ValidateResponse,
} from '@/types/ingester'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import { apiClient } from '../client'

const projectRequest: ProjectIngesterRequest = {
  project_name: 'pilot_bugs',
  submission_context: {
    submission_name: 'pilot_bugs_bugs',
    timestamp: '2026-10-19T12:00',
    datatype: 'bugs',
    identifier: 'PILOT_BUGS',
  },
  deploy_strategy: 'copy_csv',
}

describe('ingesterApi project routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('posts strict project requests to the fixed validation route', async () => {
    const result: ValidateResponse = { is_valid: true, errors: [], warnings: [], infos: [] }
    vi.mocked(apiClient.post).mockResolvedValue({ data: result })

    await expect(ingesterApi.validateProject(projectRequest)).resolves.toEqual(result)
    expect(apiClient.post).toHaveBeenCalledWith('/ingesters/sead_change_request/from-project/validate', projectRequest)
  })

  it('posts strict project requests to the fixed ingestion route', async () => {
    const result: IngestResponse = {
      success: true,
      records_processed: 2,
      message: 'Bundle created',
      output_expectation_results: [],
    }
    vi.mocked(apiClient.post).mockResolvedValue({ data: result })

    await expect(ingesterApi.ingestProject(projectRequest)).resolves.toEqual(result)
    expect(apiClient.post).toHaveBeenCalledWith('/ingesters/sead_change_request/from-project/ingest', projectRequest)
  })

  it('preserves output expectation results on failed project ingestion responses', async () => {
    const result: IngestResponse = {
      success: false,
      records_processed: 0,
      message: 'Output expectation checks failed; no tables were ingested.',
      error_details: 'Expected 2 rows but measured 3.',
      output_expectation_results: [
        {
          name: 'site-count',
          entity: 'site',
          metric: 'row_count',
          group_value: null,
          measured_value: 3,
          expected_limit: { equals: 2 },
          status: 'fail',
          failure_reason: 'Expected 2 rows but measured 3.',
        },
        {
          name: 'site-group',
          entity: 'site',
          metric: 'grouped_row_count',
          group_value: true,
          measured_value: 1,
          expected_limit: { equals: 1 },
          status: 'pass',
          failure_reason: null,
        },
      ],
    }
    vi.mocked(apiClient.post).mockResolvedValue({ data: result })

    const response = await ingesterApi.ingestProject(projectRequest)

    expect(response.success).toBe(false)
    expect(response.output_expectation_results.map((item) => item.status)).toEqual(['fail', 'pass'])
    expect(response.output_expectation_results.map((item) => item.group_value)).toEqual([null, true])
    expect(apiClient.post).toHaveBeenCalledWith('/ingesters/sead_change_request/from-project/ingest', projectRequest)
  })

  it('leaves existing file routes and request bodies unchanged', async () => {
    const validateRequest: ValidateRequest = { source: 'input.xlsx' }
    const ingestRequest: IngestRequest = {
      source: 'input.xlsx',
      submission_name: 'test',
      data_types: 'bugs',
    }
    vi.mocked(apiClient.post)
      .mockResolvedValueOnce({ data: { is_valid: true } })
      .mockResolvedValueOnce({
        data: { success: true, records_processed: 1, message: 'Imported' },
      })

    await ingesterApi.validate('sead_change_request', validateRequest)
    await ingesterApi.ingest('sead_change_request', ingestRequest)

    expect(apiClient.post).toHaveBeenNthCalledWith(1, '/ingesters/sead_change_request/validate', validateRequest)
    expect(apiClient.post).toHaveBeenNthCalledWith(2, '/ingesters/sead_change_request/ingest', ingestRequest)
  })
})
