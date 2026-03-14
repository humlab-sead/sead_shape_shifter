import { describe, expect, it } from 'vitest'

import { getTaskStatusNodeClasses, shouldShowNodeForTaskFilter } from '@/utils/taskGraph'
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

  it('computes task status classes for graph nodes', () => {
    expect(getTaskStatusNodeClasses(mkStatus({ status: 'done' as any }))).toEqual(['task-done'])
    expect(getTaskStatusNodeClasses(mkStatus({ status: 'ignored' as any }))).toEqual(['task-ignored'])
    expect(getTaskStatusNodeClasses(mkStatus({ status: 'ongoing' as any }))).toEqual(['task-ongoing'])
    expect(getTaskStatusNodeClasses(mkStatus({ blocked_by: ['dep_a'] }))).toEqual(['task-blocked'])
    expect(getTaskStatusNodeClasses(mkStatus({ priority: 'critical' as any }))).toEqual(['task-critical'])
    expect(getTaskStatusNodeClasses(mkStatus({ priority: 'ready' as any }))).toEqual(['task-ready'])
    expect(getTaskStatusNodeClasses(mkStatus({ status: 'done' as any, flagged: true }))).toEqual(['task-done', 'task-flagged'])
    expect(getTaskStatusNodeClasses(undefined)).toEqual([])
  })
})
