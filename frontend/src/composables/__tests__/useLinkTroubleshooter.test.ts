import { beforeEach, describe, expect, it, vi } from 'vitest'
import { linkTroubleshooterApi } from '@/api/linkTroubleshooter'
import { useLinkTroubleshooter } from '../useLinkTroubleshooter'
import type { LinkTroubleshootRequest, LinkTroubleshootResponse } from '@/types'

vi.mock('@/api/linkTroubleshooter', () => ({
  linkTroubleshooterApi: {
    run: vi.fn(),
  },
}))

const request: LinkTroubleshootRequest = {
  issue_type: 'row_count_mismatch',
  local_entity: 'orders',
  metadata: { fk_index: 0, fk_signature: 'saved-signature', link_pass: 'initial', join_type: 'inner' },
}

function response(): LinkTroubleshootResponse {
  return {
    status: 'reproduced',
    reason: 'reproduced',
    message: 'The warning was reproduced.',
    relationship: null,
    key_options: { local: ['saved_code', 'trial_code'], remote: ['saved_value', 'trial_value'] },
    configured_keys: { local_keys: ['saved_code'], remote_keys: ['saved_value'] },
    baseline: {
      input_a_rows: 3,
      output_rows: 2,
      unmatched_a_rows: 1,
      multiply_matched_a_rows: 0,
      diagnostic_status: 'complete',
      diagnostic_reason: null,
      diagnostic_message: null,
      issues: [],
    },
    trial: null,
  }
}

describe('useLinkTroubleshooter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens with configured keys and sends current keys and paging on run', async () => {
    const result = response()
    vi.mocked(linkTroubleshooterApi.run).mockResolvedValue(result)
    const state = useLinkTroubleshooter('project / one')

    await state.open(request)

    expect(linkTroubleshooterApi.run).toHaveBeenNthCalledWith(1, 'project / one', request)
    expect(state.result.value).toEqual(result)
    expect(state.localKeys.value).toEqual(['saved_code'])
    expect(state.remoteKeys.value).toEqual(['saved_value'])

    state.localKeys.value = ['trial_code']
    state.remoteKeys.value = ['trial_value']
    state.page.value = 2
    state.pageSize.value = 25
    state.rowFilter.value = 'unmatched'
    await state.run()

    expect(linkTroubleshooterApi.run).toHaveBeenNthCalledWith(2, 'project / one', {
      ...request,
      local_keys: ['trial_code'],
      remote_keys: ['trial_value'],
      page: 2,
      page_size: 25,
      row_filter: 'unmatched',
    })
    expect(state.result.value).toEqual(result)
  })

  it('clears prior results and formats request failures', async () => {
    vi.mocked(linkTroubleshooterApi.run)
      .mockResolvedValueOnce(response())
      .mockRejectedValueOnce(new Error('Request failed'))
    const state = useLinkTroubleshooter('project-a')

    await state.open(request)
    expect(state.result.value).not.toBeNull()
    await state.run()

    expect(state.error.value?.message).toBe('Request failed')
    expect(state.result.value).toBeNull()
    expect(state.loading.value).toBe(false)
  })

  it('resets all request state and prevents runs without an open warning', async () => {
    vi.mocked(linkTroubleshooterApi.run).mockResolvedValue(response())
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)
    state.localKeys.value = ['trial_code']
    state.remoteKeys.value = ['trial_value']
    state.page.value = 3
    state.pageSize.value = 100
    state.rowFilter.value = 'multiply_matched'

    state.reset()

    expect(state.result.value).toBeNull()
    expect(state.error.value).toBeNull()
    expect(state.localKeys.value).toEqual([])
    expect(state.remoteKeys.value).toEqual([])
    expect(state.page.value).toBe(1)
    expect(state.pageSize.value).toBe(50)
    expect(state.rowFilter.value).toBe('all')
    expect(await state.run()).toBeNull()
    expect(linkTroubleshooterApi.run).toHaveBeenCalledTimes(1)
  })
})
