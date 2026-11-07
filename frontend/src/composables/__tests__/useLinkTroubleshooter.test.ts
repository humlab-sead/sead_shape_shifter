import { beforeEach, describe, expect, it, vi } from 'vitest'
import { linkTroubleshooterApi } from '@/api/linkTroubleshooter'
import { useLinkTroubleshooter } from '../useLinkTroubleshooter'
import type {
  LinkExperimentContextRequest,
  LinkExperimentContextResponse,
  LinkExperimentTrialResponse,
  LinkTroubleshootComparison,
  LinkTroubleshootDetail,
  LinkTroubleshootTrialSettings,
} from '@/types'

vi.mock('@/api/linkTroubleshooter', () => ({
  linkTroubleshooterApi: {
    open: vi.fn(),
    trial: vi.fn(),
    close: vi.fn(),
  },
}))

const request: LinkExperimentContextRequest = {
  issue_type: 'row_count_mismatch',
  local_entity: 'orders',
  metadata: { fk_index: 0, fk_signature: 'saved-signature', link_pass: 'initial', join_type: 'inner' },
}

function emptyDetail(): LinkTroubleshootDetail {
  return {
    detail_truncated: false,
    findings: { total_count: 0, returned_count: 0, truncated: false, issues: [] },
    unmatched: {
      total_count: 0,
      returned_count: 0,
      row_cap: 100,
      row_cap_reached: false,
      budget_exhausted: false,
      rows: [],
    },
    multiply_matched: null,
  }
}

function completeSettings(overrides: Partial<LinkTroubleshootTrialSettings> = {}): LinkTroubleshootTrialSettings {
  return {
    join_type: { requested: null, source: 'inherited', effective: 'inner' },
    allow_null_keys: { requested: null, source: 'inherited' },
    null_keys_equal: { requested: null, source: 'inherited' },
    resolved_null_policy: { enforce_strict_null_keys: true, prevent_null_key_matches: false },
    ...overrides,
  }
}

function contextResponse(overrides: Partial<LinkExperimentContextResponse> = {}): LinkExperimentContextResponse {
  return {
    context_id: 'context-1',
    status: 'reproduced',
    reason: 'reproduced',
    message: 'The retained link inputs are ready.',
    expires_at: '2026-01-01T12:15:00Z',
    relationship: {
      local_entity: 'orders',
      remote_entity: 'customers',
      fk_index: 0,
      join_type: 'inner',
      link_pass: 'initial',
      constraints: { allow_row_decrease: true },
    },
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
      settings: completeSettings(),
      detail: emptyDetail(),
    },
    ...overrides,
  }
}

function comparison(overrides: Partial<LinkTroubleshootComparison> = {}): LinkTroubleshootComparison {
  return {
    status: 'complete',
    reason: 'complete',
    message: 'Trial completed.',
    settings: completeSettings(),
    totals: { input_a_rows: 3, output_rows: 3, unmatched_a_rows: 1, multiply_matched_a_rows: 0 },
    detail: emptyDetail(),
    ...overrides,
  }
}

function trialResponse(overrides: Partial<LinkExperimentTrialResponse> = {}): LinkExperimentTrialResponse {
  return {
    context_id: 'context-1',
    expires_at: '2026-01-01T12:15:00Z',
    local_keys: ['saved_code'],
    remote_keys: ['saved_value'],
    baseline: contextResponse().baseline,
    trial: comparison(),
    ...overrides,
  }
}

function contextExpiredError(): unknown {
  return {
    response: {
      status: 410,
      data: { detail: { error_type: 'LinkExperimentContextExpired', reason: 'context_expired' } },
    },
  }
}

function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void; reject: (error: unknown) => void } {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

describe('useLinkTroubleshooter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens a context and initializes controls from the retained settings', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    const state = useLinkTroubleshooter('project / one')

    await state.open(request)

    expect(linkTroubleshooterApi.open).toHaveBeenCalledWith('project / one', request)
    expect(state.context.value?.context_id).toBe('context-1')
    expect(state.localKeys.value).toEqual(['saved_code'])
    expect(state.remoteKeys.value).toEqual(['saved_value'])
    expect(state.how.value).toBe('inner')
    expect(state.allowNullKeys.value).toBeNull()
    expect(state.nullKeysEqual.value).toBeNull()
    expect(state.page.value).toBe(1)
    expect(state.pageSize.value).toBe(50)
    expect(state.group.value).toBe('unmatched')
    expect(state.side.value).toBe('baseline')
  })

  it('initializes controls from explicit constraints when an incomplete baseline has no settings', async () => {
    const base = contextResponse()
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(
      contextResponse({
        relationship: { ...base.relationship!, constraints: { allow_null_keys: true, null_keys_equal: false } },
        baseline: {
          ...base.baseline!,
          settings: null,
          diagnostic_status: 'incomplete',
          diagnostic_reason: 'row_limit_exceeded',
          input_a_rows: null,
          output_rows: null,
          unmatched_a_rows: null,
          multiply_matched_a_rows: null,
        },
      })
    )
    const state = useLinkTroubleshooter('project-a')

    await state.open(request)

    expect(state.how.value).toBe('inner')
    expect(state.allowNullKeys.value).toBe(true)
    expect(state.nullKeysEqual.value).toBe(false)
    expect(state.context.value?.baseline?.unmatched_a_rows).toBeNull()
  })

  it('runs a trial only on request with the current controls', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.trial).mockResolvedValue(trialResponse())
    const state = useLinkTroubleshooter('project-a')

    await state.open(request)
    expect(linkTroubleshooterApi.trial).not.toHaveBeenCalled()

    state.how.value = 'left'
    state.allowNullKeys.value = true
    state.nullKeysEqual.value = false
    const result = await state.run()

    expect(linkTroubleshooterApi.trial).toHaveBeenCalledWith('project-a', 'context-1', {
      local_keys: ['saved_code'],
      remote_keys: ['saved_value'],
      how: 'left',
      allow_null_keys: true,
      null_keys_equal: false,
    })
    expect(result).toEqual(comparison())
    expect(state.trial.value).toEqual(comparison())
  })

  it('clears a displayed trial and ignores an in-flight trial when controls change', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.trial).mockResolvedValueOnce(trialResponse())
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)
    await state.run()
    expect(state.trial.value).not.toBeNull()

    const pending = deferred<LinkExperimentTrialResponse>()
    vi.mocked(linkTroubleshooterApi.trial).mockReturnValueOnce(pending.promise)
    const running = state.run()
    state.localKeys.value = ['trial_code']
    expect(state.trial.value).toBeNull()

    pending.resolve(trialResponse())
    await running

    expect(state.trial.value).toBeNull()
    expect(state.loading.value).toBe(false)
  })

  it('ignores an older trial response that resolves after a newer one', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    const older = deferred<LinkExperimentTrialResponse>()
    const newer = deferred<LinkExperimentTrialResponse>()
    vi.mocked(linkTroubleshooterApi.trial).mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise)
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)

    const firstRun = state.run()
    const secondRun = state.run()
    newer.resolve(trialResponse({ trial: comparison({ message: 'newer' }) }))
    await secondRun
    older.resolve(trialResponse({ trial: comparison({ message: 'older' }) }))
    await firstRun

    expect(state.trial.value?.message).toBe('newer')
  })

  it('reopens the original warning after expiry without rerunning the expired trial', async () => {
    vi.mocked(linkTroubleshooterApi.open)
      .mockResolvedValueOnce(contextResponse())
      .mockResolvedValueOnce(contextResponse({ context_id: 'context-2' }))
    vi.mocked(linkTroubleshooterApi.trial).mockRejectedValueOnce(contextExpiredError())
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)

    await state.run()

    expect(linkTroubleshooterApi.open).toHaveBeenCalledTimes(2)
    expect(linkTroubleshooterApi.open).toHaveBeenNthCalledWith(2, 'project-a', request)
    expect(linkTroubleshooterApi.trial).toHaveBeenCalledTimes(1)
    expect(state.context.value?.context_id).toBe('context-2')
    expect(state.trial.value).toBeNull()
    expect(state.refreshed.value).toBe(true)
    expect(state.error.value).toBeNull()
  })

  it('shows an explicit failed reproduction instead of a stale comparison', async () => {
    const base = contextResponse()
    vi.mocked(linkTroubleshooterApi.open)
      .mockResolvedValueOnce(base)
      .mockResolvedValueOnce(
        contextResponse({
          context_id: null,
          status: 'not_reproduced',
          reason: 'warning_changed',
          message: 'The warning did not reproduce.',
          expires_at: null,
          baseline: null,
        })
      )
    vi.mocked(linkTroubleshooterApi.trial).mockRejectedValueOnce(contextExpiredError())
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)

    await state.run()

    expect(state.context.value?.status).toBe('not_reproduced')
    expect(state.context.value?.context_id).toBeNull()
    expect(state.trial.value).toBeNull()
    expect(state.refreshed.value).toBe(true)
    expect(state.error.value).toBeNull()
  })

  it('shows a non-expiry trial failure without reopening the context', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.trial).mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 404, data: { detail: 'Resource not found' } },
    })
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)

    await state.run()

    expect(state.error.value?.message).toBe('Resource not found')
    expect(linkTroubleshooterApi.open).toHaveBeenCalledTimes(1)
    expect(state.refreshed.value).toBe(false)
  })

  it('resets to the retained baseline and original controls without a request', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.trial).mockResolvedValue(trialResponse())
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)
    await state.run()

    state.how.value = 'left'
    state.allowNullKeys.value = true
    state.page.value = 3
    state.pageSize.value = 100
    state.group.value = 'multiply_matched'
    state.side.value = 'trial'

    state.reset()

    expect(state.trial.value).toBeNull()
    expect(state.error.value).toBeNull()
    expect(state.localKeys.value).toEqual(['saved_code'])
    expect(state.remoteKeys.value).toEqual(['saved_value'])
    expect(state.how.value).toBe('inner')
    expect(state.allowNullKeys.value).toBeNull()
    expect(state.nullKeysEqual.value).toBeNull()
    expect(state.page.value).toBe(1)
    expect(state.pageSize.value).toBe(50)
    expect(state.group.value).toBe('unmatched')
    expect(state.side.value).toBe('baseline')
    expect(state.context.value?.context_id).toBe('context-1')
    expect(linkTroubleshooterApi.open).toHaveBeenCalledTimes(1)
    expect(linkTroubleshooterApi.trial).toHaveBeenCalledTimes(1)
  })

  it('keeps an incomplete baseline through reset', async () => {
    const base = contextResponse()
    const incomplete = contextResponse({
      baseline: {
        ...base.baseline!,
        settings: null,
        diagnostic_status: 'incomplete',
        input_a_rows: null,
        output_rows: null,
        unmatched_a_rows: null,
        multiply_matched_a_rows: null,
      },
    })
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(incomplete)
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)

    state.how.value = 'left'
    state.reset()

    expect(state.context.value?.baseline?.diagnostic_status).toBe('incomplete')
    expect(state.context.value?.baseline?.unmatched_a_rows).toBeNull()
    expect(state.how.value).toBe('inner')
  })

  it('clears state and deletes its owned context on close', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.close).mockResolvedValue(undefined)
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)

    await state.close()

    expect(linkTroubleshooterApi.close).toHaveBeenCalledWith('project-a', 'context-1')
    expect(state.context.value).toBeNull()
    expect(state.trial.value).toBeNull()
    expect(state.localKeys.value).toEqual([])
    expect(state.how.value).toBeNull()
    expect(state.refreshed.value).toBe(false)
    expect(state.error.value).toBeNull()
  })

  it('reports a cleanup failure without masking a newer context', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    const cleanup = deferred<void>()
    vi.mocked(linkTroubleshooterApi.close).mockReturnValueOnce(cleanup.promise)
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)

    const closing = state.close()
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValueOnce(contextResponse({ context_id: 'context-2' }))
    await state.open(request)
    cleanup.reject(new Error('cleanup failed'))
    await closing

    expect(state.context.value?.context_id).toBe('context-2')
    expect(state.error.value).toBeNull()
  })

  it('closes a superseded context when a different warning opens', async () => {
    vi.mocked(linkTroubleshooterApi.open)
      .mockResolvedValueOnce(contextResponse({ context_id: 'context-1' }))
      .mockResolvedValueOnce(contextResponse({ context_id: 'context-2' }))
    vi.mocked(linkTroubleshooterApi.close).mockResolvedValue(undefined)
    const state = useLinkTroubleshooter('project-a')

    await state.open(request)
    await state.open({ ...request, metadata: { ...request.metadata, fk_index: 1 } })
    await Promise.resolve()

    expect(linkTroubleshooterApi.close).toHaveBeenCalledWith('project-a', 'context-1')
    expect(state.context.value?.context_id).toBe('context-2')
  })

  it('prevents a trial without an owned context', async () => {
    const state = useLinkTroubleshooter('project-a')

    expect(await state.run()).toBeNull()
    expect(linkTroubleshooterApi.trial).not.toHaveBeenCalled()
  })
})
