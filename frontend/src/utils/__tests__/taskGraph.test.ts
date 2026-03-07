import { describe, expect, it } from 'vitest'

import { shouldShowNodeForTaskFilter } from '@/utils/taskGraph'
import type { EntityTaskStatus } from '@/composables/useTaskStatus'

function mkStatus(overrides: Partial<EntityTaskStatus> = {}): EntityTaskStatus {
  return {
    entity_name: 'entity',
    status: 'todo',
    priority: 'optional',
    required: false,
    exists: true,
    validation_passed: true,
    preview_available: true,
    flagged: false,
    blocked_by: [],
    issues: [],
    ...overrides,
  } as EntityTaskStatus
}

describe('taskGraph', () => {
  it('shows undefined status for all filters', () => {
    expect(shouldShowNodeForTaskFilter(undefined, 'all')).toBe(true)
    expect(shouldShowNodeForTaskFilter(undefined, 'critical')).toBe(true)
  })

  it('filters by basic task status', () => {
    expect(shouldShowNodeForTaskFilter(mkStatus({ status: 'todo' as any }), 'todo')).toBe(true)
    expect(shouldShowNodeForTaskFilter(mkStatus({ status: 'ongoing' as any }), 'ongoing')).toBe(true)
    expect(shouldShowNodeForTaskFilter(mkStatus({ status: 'done' as any }), 'done')).toBe(true)
    expect(shouldShowNodeForTaskFilter(mkStatus({ status: 'ignored' as any }), 'ignored')).toBe(true)
    expect(shouldShowNodeForTaskFilter(mkStatus({ status: 'done' as any }), 'todo')).toBe(false)
  })

  it('filters blocked entities', () => {
    expect(shouldShowNodeForTaskFilter(mkStatus({ blocked_by: ['dep_a'] }), 'blocked')).toBe(true)
    expect(shouldShowNodeForTaskFilter(mkStatus({ blocked_by: [] }), 'blocked')).toBe(false)
  })

  it('filters critical entities', () => {
    expect(shouldShowNodeForTaskFilter(mkStatus({ priority: 'critical' as any }), 'critical')).toBe(true)
    expect(shouldShowNodeForTaskFilter(mkStatus({ priority: 'ready' as any }), 'critical')).toBe(false)
  })
})
