import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import type { ColumnAvailabilityResponse } from '@/api/entities'

const mockGetColumnAvailability = vi.hoisted(() => vi.fn())

vi.mock('@/api/entities', () => ({
  entitiesApi: { getColumnAvailability: mockGetColumnAvailability },
}))

import { useColumnAvailability } from '../useColumnAvailability'

const response: ColumnAvailabilityResponse = {
  columns: ['sample_name'],
  business_keys: ['sample_name'],
  replacements: ['sample_name'],
  drop_duplicates: ['sample_name'],
  drop_empty_rows: ['sample_name'],
  extra_columns: { sources: ['sample_name'] },
  filters: { extract: ['sample_name'] },
  foreign_keys: [],
  unnest: { id_vars: ['sample_name'], value_vars: [] },
}

describe('useColumnAvailability', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockGetColumnAvailability.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('sends one request for the latest draft and selected parent state', async () => {
    mockGetColumnAvailability.mockResolvedValue(response)
    const scope = effectScope()
    let composable!: ReturnType<typeof useColumnAvailability>
    scope.run(() => {
      composable = useColumnAvailability()
    })

    composable.refresh('project', 'child', { entity_draft: { columns: ['first'] } })
    const latestRequest = {
      entity_draft: {
        columns: ['second'],
        foreign_keys: [{ entity: 'parent', local_keys: ['parent_name'] }],
      },
      source_columns: ['second', 'parent_name'],
    }
    composable.refresh('project', 'child', latestRequest)

    expect(mockGetColumnAvailability).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(300)

    expect(mockGetColumnAvailability).toHaveBeenCalledTimes(1)
    expect(mockGetColumnAvailability).toHaveBeenCalledWith('project', 'child', latestRequest)
    await vi.runAllTicks()
    expect(composable.availability.value).toEqual(response)
    expect(composable.loading.value).toBe(false)
    scope.stop()
  })

  it('ignores an in-flight response after a newer draft is scheduled', async () => {
    let resolveFirst!: (value: ColumnAvailabilityResponse) => void
    const firstResponse = new Promise<ColumnAvailabilityResponse>((resolve) => {
      resolveFirst = resolve
    })
    const latestResponse = { ...response, columns: ['latest'] }
    mockGetColumnAvailability.mockReturnValueOnce(firstResponse).mockResolvedValueOnce(latestResponse)
    const scope = effectScope()
    let composable!: ReturnType<typeof useColumnAvailability>
    scope.run(() => {
      composable = useColumnAvailability()
    })

    composable.refresh('project', 'child', { entity_draft: { columns: ['first'] } })
    await vi.advanceTimersByTimeAsync(300)
    composable.refresh('project', 'child', { entity_draft: { columns: ['latest'] } })
    resolveFirst(response)
    await vi.runAllTicks()
    expect(composable.availability.value).toBeNull()

    await vi.advanceTimersByTimeAsync(300)
    await vi.runAllTicks()
    expect(composable.availability.value).toEqual(latestResponse)
    scope.stop()
  })

  it('skips unnamed entities and exposes request errors without throwing', async () => {
    mockGetColumnAvailability.mockRejectedValue(new Error('request failed'))
    const scope = effectScope()
    let composable!: ReturnType<typeof useColumnAvailability>
    scope.run(() => {
      composable = useColumnAvailability()
    })

    composable.refresh('project', '', { entity_draft: {} })
    await vi.advanceTimersByTimeAsync(300)
    expect(mockGetColumnAvailability).not.toHaveBeenCalled()

    composable.refresh('project', 'entity', { entity_draft: {} })
    await vi.advanceTimersByTimeAsync(300)
    await vi.runAllTicks()
    expect(composable.error.value).toBe('request failed')
    expect(composable.loading.value).toBe(false)
    scope.stop()
  })
})
