import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import type { ColumnReferenceResolveResponse } from '@/api/entities'

const apiMocks = vi.hoisted(() => ({
  complete: vi.fn(),
  resolve: vi.fn(),
}))

vi.mock('@/api/entities', () => ({
  entitiesApi: {
    completeColumnReferences: apiMocks.complete,
    resolveColumnReference: apiMocks.resolve,
  },
}))

import { isSimpleColumnReference, useColumnReferences } from '../useColumnReferences'

const context = (entityDraft: Record<string, unknown> = { columns: ['first'] }) => ({
  projectName: 'demo',
  entityName: 'sample',
  entityDraft,
  editedFieldPath: 'entities.sample.keys',
})

describe('useColumnReferences', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    apiMocks.complete.mockReset()
    apiMocks.resolve.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('debounces completion and sends a copy of the latest draft and field context', async () => {
    apiMocks.complete.mockResolvedValue({ candidates: ['@value: entities.site.keys'] })
    const scope = effectScope()
    let references!: ReturnType<typeof useColumnReferences>
    scope.run(() => {
      references = useColumnReferences()
    })

    references.scheduleCompletion(context(), '@value')
    const latestDraft = { columns: ['second'] }
    references.scheduleCompletion(
      {
        ...context(latestDraft),
        editedFieldPath: 'entities.sample.foreign_keys.0.local_keys',
        preferredEntity: 'site',
      },
      '@value: entities.site.k'
    )
    latestDraft.columns.push('changed after request scheduling')

    expect(apiMocks.complete).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(300)

    expect(apiMocks.complete).toHaveBeenCalledTimes(1)
    expect(apiMocks.complete).toHaveBeenCalledWith('demo', 'sample', {
      entity_draft: { columns: ['second'] },
      prefix: '@value: entities.site.k',
      edited_field_path: 'entities.sample.foreign_keys.0.local_keys',
      preferred_entity: 'site',
    })
    await vi.runAllTicks()
    expect(references.candidates.value).toEqual(['@value: entities.site.keys'])
    scope.stop()
  })

  it('clears old choices and ignores a completion response from an older draft', async () => {
    let resolveFirst!: (value: { candidates: string[] }) => void
    apiMocks.complete
      .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce({ candidates: ['@value: entities.site.columns'] })
    const scope = effectScope()
    let references!: ReturnType<typeof useColumnReferences>
    scope.run(() => {
      references = useColumnReferences()
    })

    references.scheduleCompletion(context({ columns: ['old'] }), '@value: entities.site.k')
    await vi.advanceTimersByTimeAsync(300)
    references.scheduleCompletion(context({ columns: ['new'] }), '@value: entities.site.c')
    resolveFirst({ candidates: ['@value: entities.site.keys'] })
    await vi.runAllTicks()

    expect(references.candidates.value).toEqual([])
    expect(references.completionLoading.value).toBe(true)
    await vi.advanceTimersByTimeAsync(300)
    await vi.runAllTicks()
    expect(references.candidates.value).toEqual(['@value: entities.site.columns'])
    scope.stop()
  })

  it('keeps unresolved results separate from request errors and ignores stale resolve results', async () => {
    let resolveFirst!: (value: ColumnReferenceResolveResponse) => void
    apiMocks.resolve.mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve))).mockResolvedValueOnce({
      directive: '@value: entities.site.columns',
      path: 'entities.site.columns',
      status: 'unresolved',
      reason_code: 'missing_path',
      reason: 'The referenced path does not exist in the current project draft.',
    })

    const scope = effectScope()
    let references!: ReturnType<typeof useColumnReferences>
    scope.run(() => {
      references = useColumnReferences()
    })

    const firstResult: ColumnReferenceResolveResponse = {
      directive: '@value: entities.site.keys',
      path: 'entities.site.keys',
      status: 'resolved',
      columns: ['old_column'],
    }
    const firstPromise = references.resolveReference(context({ columns: ['old'] }), firstResult.directive)
    const secondPromise = references.resolveReference(context({ columns: ['new'] }), '@value: entities.site.columns')
    resolveFirst(firstResult)
    await firstPromise
    await secondPromise

    expect(references.inspection.value?.status).toBe('unresolved')
    expect(references.inspection.value?.reason).toContain('does not exist')
    expect(references.inspectionError.value).toBeNull()

    apiMocks.resolve.mockRejectedValueOnce(new Error('read denied'))
    await references.resolveReference(context(), '@value: entities.site.keys')
    expect(references.inspection.value).toBeNull()
    expect(references.inspectionError.value).toBe('read denied')
    scope.stop()
  })

  it('does not expose delayed errors from older completion or inspection requests', async () => {
    let rejectFirstCompletion!: (error: Error) => void
    apiMocks.complete
      .mockReturnValueOnce(new Promise((_resolve, reject) => (rejectFirstCompletion = reject)))
      .mockResolvedValueOnce({ candidates: ['@value: entities.site.columns'] })
    let rejectFirstInspection!: (error: Error) => void
    apiMocks.resolve
      .mockReturnValueOnce(new Promise((_resolve, reject) => (rejectFirstInspection = reject)))
      .mockResolvedValueOnce({
        directive: '@value: entities.site.columns',
        path: 'entities.site.columns',
        status: 'resolved',
        columns: ['latest_column'],
      })

    const scope = effectScope()
    let references!: ReturnType<typeof useColumnReferences>
    scope.run(() => {
      references = useColumnReferences()
    })

    references.scheduleCompletion(context({ columns: ['old'] }), '@value: entities.site.k')
    await vi.advanceTimersByTimeAsync(300)
    references.scheduleCompletion(context({ columns: ['new'] }), '@value: entities.site.c')
    rejectFirstCompletion(new Error('old completion failed'))
    await vi.runAllTicks()
    expect(references.completionError.value).toBeNull()
    await vi.advanceTimersByTimeAsync(300)
    await vi.runAllTicks()
    expect(references.candidates.value).toEqual(['@value: entities.site.columns'])

    const firstResolve = references.resolveReference(context({ columns: ['old'] }), '@value: entities.site.keys')
    const secondResolve = references.resolveReference(context({ columns: ['new'] }), '@value: entities.site.columns')
    await secondResolve
    rejectFirstInspection(new Error('old inspection failed'))
    await firstResolve
    expect(references.inspection.value?.columns).toEqual(['latest_column'])
    expect(references.inspectionError.value).toBeNull()
    scope.stop()
  })

  it('sends the saved entity name only when the draft renames it', async () => {
    apiMocks.complete.mockResolvedValue({ candidates: [] })
    apiMocks.resolve.mockResolvedValue({ directive: '@value: entities.renamed.keys', path: null, status: 'unresolved' })
    const scope = effectScope()
    let references!: ReturnType<typeof useColumnReferences>
    scope.run(() => {
      references = useColumnReferences()
    })

    references.scheduleCompletion({ ...context(), originalEntityName: 'saved' }, '@value: entities.')
    await vi.advanceTimersByTimeAsync(300)
    await references.resolveReference({ ...context(), originalEntityName: 'saved' }, '@value: entities.renamed.keys')

    expect(apiMocks.complete).toHaveBeenCalledWith('demo', 'sample', expect.objectContaining({ original_entity_name: 'saved' }))
    expect(apiMocks.resolve).toHaveBeenCalledWith('demo', 'sample', expect.objectContaining({ original_entity_name: 'saved' }))

    apiMocks.complete.mockClear()
    apiMocks.resolve.mockClear()
    references.scheduleCompletion(context(), '@value: entities.')
    await vi.advanceTimersByTimeAsync(300)
    await references.resolveReference(context(), '@value: entities.renamed.keys')

    expect(apiMocks.complete).toHaveBeenCalledWith('demo', 'sample', expect.not.objectContaining({ original_entity_name: expect.anything() }))
    expect(apiMocks.resolve).toHaveBeenCalledWith('demo', 'sample', expect.not.objectContaining({ original_entity_name: expect.anything() }))
    scope.stop()
  })

  it('does not request malformed or legacy expression values and clears pending work on disposal', async () => {
    apiMocks.complete.mockResolvedValue({ candidates: [] })
    const scope = effectScope()
    let references!: ReturnType<typeof useColumnReferences>
    scope.run(() => {
      references = useColumnReferences()
    })

    expect(isSimpleColumnReference('@value: entities.site.keys')).toBe(true)
    expect(isSimpleColumnReference("['literal'] + @value: entities.site.keys")).toBe(false)
    await references.resolveReference(context(), "['literal'] + @value: entities.site.keys")
    expect(apiMocks.resolve).not.toHaveBeenCalled()

    references.scheduleCompletion(context(), '@value: entities.site')
    scope.stop()
    await vi.advanceTimersByTimeAsync(300)
    expect(apiMocks.complete).not.toHaveBeenCalled()
    expect(references.candidates.value).toEqual([])
  })
})
