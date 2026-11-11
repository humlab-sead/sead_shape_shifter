import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest } from '../client'
import { linkTroubleshooterApi } from '../linkTroubleshooter'
import type { LinkExperimentContextRequest, LinkExperimentContextResponse, LinkExperimentTrialResponse } from '@/types'

vi.mock('../client', () => ({
  apiRequest: vi.fn(),
}))

const contextRequest: LinkExperimentContextRequest = {
  issue_type: 'row_count_mismatch',
  local_entity: 'orders',
  metadata: { fk_index: 1, fk_signature: 'signature' },
}

describe('linkTroubleshooterApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens a context with the encoded project name and warning identity', async () => {
    const response = { context_id: 'context-1' } as LinkExperimentContextResponse
    vi.mocked(apiRequest).mockResolvedValue(response)

    await expect(linkTroubleshooterApi.open('project / one', contextRequest)).resolves.toEqual(response)

    expect(apiRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/projects/project%20%2F%20one/link-experiment-contexts',
      data: contextRequest,
    })
  })

  it('runs a trial against the encoded context without paging fields', async () => {
    const request = {
      local_keys: ['trial_code'],
      remote_keys: ['trial_value'],
      how: 'left' as const,
      allow_null_keys: null,
      null_keys_equal: true,
    }
    const response = { context_id: 'context / one' } as LinkExperimentTrialResponse
    vi.mocked(apiRequest).mockResolvedValue(response)

    await expect(linkTroubleshooterApi.trial('project / one', 'context / one', request)).resolves.toEqual(response)

    expect(apiRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/projects/project%20%2F%20one/link-experiment-contexts/context%20%2F%20one/trials',
      data: request,
    })
    expect(request).not.toHaveProperty('page')
    expect(request).not.toHaveProperty('page_size')
    expect(request).not.toHaveProperty('row_filter')
  })

  it('deletes the owned context', async () => {
    vi.mocked(apiRequest).mockResolvedValue(undefined)

    await linkTroubleshooterApi.close('project / one', 'context / one')

    expect(apiRequest).toHaveBeenCalledWith({
      method: 'DELETE',
      url: '/projects/project%20%2F%20one/link-experiment-contexts/context%20%2F%20one',
    })
  })
})
