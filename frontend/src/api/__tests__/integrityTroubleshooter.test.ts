import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest } from '../client'
import { integrityTroubleshooterApi } from '../integrityTroubleshooter'
import type {
  IntegrityTroubleshootPageRequest,
  IntegrityTroubleshootRequest,
  IntegrityTroubleshootResponse,
} from '@/types'

vi.mock('../client', () => ({
  apiRequest: vi.fn(),
}))

function response(): IntegrityTroubleshootResponse {
  return {
    status: 'reproduced',
    reason: 'reproduced',
    message: 'The current full-data unmatched count matches the warning.',
    source: 'current full normalization',
    context_id: 'context-one',
    expires_at: '2026-01-01T00:15:00Z',
    relationship: {
      local_entity: 'orders',
      remote_entity: 'customers',
      fk_index: 0,
      join_type: 'inner',
      constraints: {},
    },
    configured_keys: { local_keys: ['customer_code'], remote_keys: ['code'] },
    recorded_orphan_count: 2,
    current_orphan_count: 2,
    values: {
      page: 1,
      page_size: 50,
      distinct_value_count: 2,
      returned_value_count: 2,
      has_next: false,
      values: [
        { key_values: ['MISSING-A'], local_row_count: 1, token: 'dG9rZW4tYQ==' },
        { key_values: ['MISSING-B'], local_row_count: 1, token: 'dG9rZW4tYg==' },
      ],
    },
    selected: null,
  }
}

describe('integrityTroubleshooterApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('encodes the project name and forwards the first-page request body', async () => {
    const request: IntegrityTroubleshootRequest = {
      issue_type: 'FK_DATA_INTEGRITY',
      local_entity: 'orders',
      metadata: { fk_index: 1, fk_signature: 'signature', orphan_count: 2 },
      page: 1,
    }
    const body = response()
    vi.mocked(apiRequest).mockResolvedValue(body)

    await expect(integrityTroubleshooterApi.inspect('project / one', request)).resolves.toEqual(body)

    expect(apiRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/projects/project%20%2F%20one/integrity-troubleshooter',
      data: request,
    })
  })

  it('forwards a later page unchanged', async () => {
    const request: IntegrityTroubleshootRequest = {
      issue_type: 'FK_DATA_INTEGRITY',
      local_entity: 'orders',
      metadata: { fk_index: 0, fk_signature: 'signature' },
      page: 3,
    }
    vi.mocked(apiRequest).mockResolvedValue(response())

    await integrityTroubleshooterApi.inspect('project-a', request)

    expect(apiRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/projects/project-a/integrity-troubleshooter',
      data: request,
    })
  })

  it('forwards the server-issued value token without converting it', async () => {
    const request: IntegrityTroubleshootRequest = {
      issue_type: 'FK_DATA_INTEGRITY',
      local_entity: 'orders',
      metadata: { fk_index: 0, fk_signature: 'signature' },
      page: 2,
      selected_value_token: 'dG9rZW4tYQ==',
    }
    vi.mocked(apiRequest).mockResolvedValue(response())

    await integrityTroubleshooterApi.inspect('project-a', request)

    expect(apiRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/projects/project-a/integrity-troubleshooter',
      data: request,
    })
  })

  it('encodes the context identifier and forwards a page request', async () => {
    const request: IntegrityTroubleshootPageRequest = {
      page: 2,
      selected_value_token: 'dG9rZW4tYQ==',
      row_offset: 100,
      row_limit: 50,
    }
    vi.mocked(apiRequest).mockResolvedValue(response())

    await integrityTroubleshooterApi.page('project / one', 'context / one', request)

    expect(apiRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/projects/project%20%2F%20one/integrity-troubleshooter/context%20%2F%20one/page',
      data: request,
    })
  })

  it('closes the named inspection context', async () => {
    vi.mocked(apiRequest).mockResolvedValue(undefined)

    await expect(integrityTroubleshooterApi.close('project-a', 'context-one')).resolves.toBeUndefined()

    expect(apiRequest).toHaveBeenCalledWith({
      method: 'DELETE',
      url: '/projects/project-a/integrity-troubleshooter/context-one',
    })
  })
})
