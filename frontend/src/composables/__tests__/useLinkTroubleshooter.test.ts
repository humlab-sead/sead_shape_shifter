import { beforeEach, describe, expect, it, vi } from 'vitest'
import { linkTroubleshooterApi } from '@/api/linkTroubleshooter'
import { useLinkTroubleshooter } from '../useLinkTroubleshooter'
import type {
  LinkExceptionRowsPage,
  LinkExperimentContextRequest,
  LinkExperimentContextResponse,
  LinkExperimentTrialResponse,
  LinkTroubleshootComparison,
  LinkTroubleshootDetail,
  LinkTroubleshootExceptionRow,
  LinkTroubleshootTrialSettings,
} from '@/types'

vi.mock('@/api/linkTroubleshooter', () => ({
  linkTroubleshooterApi: {
    open: vi.fn(),
    trial: vi.fn(),
    exceptionRows: vi.fn(),
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

function exceptionRow(position: number, value = 'missing'): LinkTroubleshootExceptionRow {
  return {
    input_position: position,
    key_values: [{ value, truncated: false, original_length: null }],
    remote_match_count: 0,
    output_row_contribution: 0,
  }
}

function rowsPage(overrides: Partial<LinkExceptionRowsPage> = {}): LinkExceptionRowsPage {
  return {
    status: 'available',
    reason: null,
    message: null,
    side: 'baseline',
    group: 'unmatched',
    offset: 0,
    limit: 100,
    total_count: 0,
    browse_cap: 10_000,
    browse_cap_reached: false,
    returned_count: 0,
    rows: [],
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
    vi.mocked(linkTroubleshooterApi.exceptionRows).mockResolvedValue(rowsPage())
    vi.mocked(linkTroubleshooterApi.close).mockResolvedValue(undefined)
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
    expect(state.pageSize.value).toBe(100)
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
    expect(state.trialStale.value).toBe(false)
  })

  it('marks a displayed trial stale and ignores an in-flight trial when controls change', async () => {
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
    expect(state.trial.value).toEqual(comparison())
    expect(state.trialStale.value).toBe(true)

    pending.resolve(trialResponse())
    await running

    expect(state.trial.value).toEqual(comparison())
    expect(state.trialStale.value).toBe(true)
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
    expect(state.pageSize.value).toBe(100)
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

  it('loads one bounded baseline row page when a context opens', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.exceptionRows).mockResolvedValue(
      rowsPage({ total_count: 250, returned_count: 2, rows: [exceptionRow(0, 'A'), exceptionRow(1, 'B')] })
    )
    const state = useLinkTroubleshooter('project-a')

    await state.open(request)
    await Promise.resolve()

    expect(linkTroubleshooterApi.exceptionRows).toHaveBeenCalledWith('project-a', 'context-1', {
      side: 'baseline',
      group: 'unmatched',
      offset: 0,
      limit: 100,
      trial: null,
    })
    expect(state.rows.value.map((row) => row.input_position)).toEqual([0, 1])
    expect(state.rowTotalCount.value).toBe(250)
    expect(state.rowBrowseCap.value).toBe(10_000)
    expect(state.rowBrowseCapReached.value).toBe(false)
    expect(state.rowStatusMessage.value).toBeNull()
  })

  it('requests the next row page when the group or page changes', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)
    await Promise.resolve()
    vi.mocked(linkTroubleshooterApi.exceptionRows).mockClear()

    state.page.value = 3
    await Promise.resolve()

    expect(linkTroubleshooterApi.exceptionRows).toHaveBeenLastCalledWith('project-a', 'context-1', {
      side: 'baseline',
      group: 'unmatched',
      offset: 200,
      limit: 100,
      trial: null,
    })

    state.group.value = 'multiply_matched'
    await Promise.resolve()

    expect(linkTroubleshooterApi.exceptionRows).toHaveBeenLastCalledWith('project-a', 'context-1', {
      side: 'baseline',
      group: 'multiply_matched',
      offset: 200,
      limit: 100,
      trial: null,
    })
  })

  it('browses trial rows with the controls that produced the accepted trial', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.trial).mockResolvedValue(trialResponse())
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)
    await Promise.resolve()

    state.how.value = 'left'
    await state.run()
    await Promise.resolve()
    vi.mocked(linkTroubleshooterApi.exceptionRows).mockClear()

    state.side.value = 'trial'
    await Promise.resolve()

    expect(linkTroubleshooterApi.exceptionRows).toHaveBeenLastCalledWith('project-a', 'context-1', {
      side: 'trial',
      group: 'unmatched',
      offset: 0,
      limit: 100,
      trial: {
        local_keys: ['saved_code'],
        remote_keys: ['saved_value'],
        how: 'left',
        allow_null_keys: null,
        null_keys_equal: null,
      },
    })
  })

  it('shows the backend refusal when affected rows cannot be browsed', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.exceptionRows).mockResolvedValue(
      rowsPage({
        status: 'unavailable',
        reason: 'diagnostic_incomplete',
        message: 'The configured-key diagnostic did not complete, so affected rows are unavailable.',
      })
    )
    const state = useLinkTroubleshooter('project-a')

    await state.open(request)
    await Promise.resolve()

    expect(state.rows.value).toEqual([])
    expect(state.rowStatusMessage.value).toBe(
      'The configured-key diagnostic did not complete, so affected rows are unavailable.'
    )
  })

  it('reopens the original warning when browsing rows hits an expired context', async () => {
    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.exceptionRows)
      .mockRejectedValueOnce(contextExpiredError())
      .mockResolvedValue(rowsPage({ total_count: 1, returned_count: 1, rows: [exceptionRow(0)] }))
    const state = useLinkTroubleshooter('project-a')

    await state.open(request)
    await Promise.resolve()
    await Promise.resolve()

    expect(linkTroubleshooterApi.open).toHaveBeenCalledTimes(2)
    expect(state.context.value?.context_id).toBe('context-1')
    expect(state.refreshed.value).toBe(true)
    expect(state.rows.value).toHaveLength(1)
    expect(state.rowsError.value).toBeNull()
  })

  it('drops loaded rows when the context closes', async () => {    vi.mocked(linkTroubleshooterApi.open).mockResolvedValue(contextResponse())
    vi.mocked(linkTroubleshooterApi.exceptionRows).mockResolvedValue(
      rowsPage({ total_count: 1, returned_count: 1, rows: [exceptionRow(0)] })
    )
    const state = useLinkTroubleshooter('project-a')
    await state.open(request)
    await Promise.resolve()
    expect(state.rows.value).toHaveLength(1)

    await state.close()

    expect(state.rows.value).toEqual([])
    expect(state.rowTotalCount.value).toBe(0)
    expect(state.rowBrowseCapReached.value).toBe(false)
  })
})
