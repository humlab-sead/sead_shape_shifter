import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest } from '../client'
import { linkTroubleshooterApi } from '../linkTroubleshooter'
import type { LinkTroubleshootRequest, LinkTroubleshootResponse } from '@/types'

vi.mock('../client', () => ({
  apiRequest: vi.fn(),
}))

describe('linkTroubleshooterApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('encodes the project name and forwards the request body', async () => {
    const request: LinkTroubleshootRequest = {
      issue_type: 'row_count_mismatch',
      local_entity: 'orders',
      metadata: { fk_index: 1, fk_signature: 'signature' },
      local_keys: ['trial_code'],
      remote_keys: ['trial_value'],
      page: 2,
      page_size: 25,
      row_filter: 'unmatched',
    }
    const response = {
      status: 'reproduced',
      reason: 'reproduced',
      message: 'Warning reproduced.',
      relationship: null,
      key_options: null,
      configured_keys: null,
      baseline: null,
      trial: null,
    } satisfies LinkTroubleshootResponse
    vi.mocked(apiRequest).mockResolvedValue(response)

    await expect(linkTroubleshooterApi.run('project / one', request)).resolves.toEqual(response)

    expect(apiRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/projects/project%20%2F%20one/link-troubleshooter',
      data: request,
    })
  })
})
