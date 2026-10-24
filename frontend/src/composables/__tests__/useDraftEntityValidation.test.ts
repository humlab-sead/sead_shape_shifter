import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import type { ValidationResult } from '@/types'
import { validationApi } from '@/api/validation'
import { useDraftEntityValidation } from '../useDraftEntityValidation'
import type { DraftEntityValidationContext } from '../useDraftEntityValidation'

vi.mock('@/api/validation', () => ({
  validationApi: {
    validateEntityDraft: vi.fn(),
  },
}))

const validResult: ValidationResult = {
  is_valid: true,
  errors: [],
  warnings: [],
  info: [],
  error_count: 0,
  warning_count: 0,
}

function makeContext(overrides: Partial<DraftEntityValidationContext> = {}): DraftEntityValidationContext {
  return {
    projectName: 'project',
    entityName: 'sample',
    entityDraft: { type: 'entity', keys: ['sample_id'], columns: ['sample_id'] },
    ...overrides,
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

describe('useDraftEntityValidation', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('debounces the exact request and sends a copied raw draft', async () => {
    vi.mocked(validationApi.validateEntityDraft).mockResolvedValue(validResult)
    const scope = effectScope()
    const validation = scope.run(() => useDraftEntityValidation())!
    const context = makeContext()
    validation.setContext(context)
    validation.validateDraft(context)
    ;(context.entityDraft.keys as string[]).push('later_edit')

    await vi.advanceTimersByTimeAsync(300)

    expect(validationApi.validateEntityDraft).toHaveBeenCalledWith('project', 'sample', {
      entity_draft: { type: 'entity', keys: ['sample_id'], columns: ['sample_id'] },
    })
    expect(validation.result.value).toEqual(validResult)
    scope.stop()
  })

  it('discards delayed success and error results after a draft or entity change', async () => {
    const delayedSuccess = deferred<ValidationResult>()
    vi.mocked(validationApi.validateEntityDraft).mockReturnValueOnce(delayedSuccess.promise)
    const scope = effectScope()
    const validation = scope.run(() => useDraftEntityValidation())!
    const firstContext = makeContext()
    validation.setContext(firstContext)
    validation.validateDraft(firstContext)
    await vi.advanceTimersByTimeAsync(300)

    const changedContext = makeContext({ entityName: 'renamed', entityDraft: { type: 'entity', keys: ['new'] } })
    validation.setContext(changedContext)
    delayedSuccess.resolve(validResult)
    await Promise.resolve()
    await Promise.resolve()
    expect(validation.result.value).toBeNull()

    const delayedError = deferred<ValidationResult>()
    vi.mocked(validationApi.validateEntityDraft).mockReturnValueOnce(delayedError.promise)
    validation.validateDraft(changedContext)
    await vi.advanceTimersByTimeAsync(300)
    validation.setContext(makeContext({ entityDraft: { type: 'entity', keys: ['latest'] } }))
    delayedError.reject(new Error('read denied'))
    await Promise.resolve()
    await Promise.resolve()
    expect(validation.error.value).toBeNull()
    expect(validation.result.value).toBeNull()
    scope.stop()
  })

  it('invalidates pending requests when the dialog closes or the composable is disposed', async () => {
    const delayed = deferred<ValidationResult>()
    vi.mocked(validationApi.validateEntityDraft).mockReturnValue(delayed.promise)
    const scope = effectScope()
    const validation = scope.run(() => useDraftEntityValidation())!
    const context = makeContext({ originalEntityName: 'saved_name' })
    validation.setContext(context)
    validation.validateDraft(context)
    await vi.advanceTimersByTimeAsync(300)
    expect(validationApi.validateEntityDraft).toHaveBeenCalledWith('project', 'sample', {
      entity_draft: { type: 'entity', keys: ['sample_id'], columns: ['sample_id'] },
      original_entity_name: 'saved_name',
    })

    validation.invalidate()
    delayed.resolve(validResult)
    await Promise.resolve()
    await Promise.resolve()
    expect(validation.result.value).toBeNull()

    validation.validateDraft(context)
    scope.stop()
    await vi.advanceTimersByTimeAsync(300)
    expect(validationApi.validateEntityDraft).toHaveBeenCalledTimes(1)
  })

  it('does not make a request without an open project and entity context', async () => {
    const scope = effectScope()
    const validation = scope.run(() => useDraftEntityValidation())!
    validation.validateDraft(null)
    await vi.advanceTimersByTimeAsync(300)
    expect(validationApi.validateEntityDraft).not.toHaveBeenCalled()
    scope.stop()
  })
})
