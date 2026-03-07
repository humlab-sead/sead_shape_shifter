import type { EntityTaskStatus } from '@/composables/useTaskStatus'

export type TaskGraphFilter = 'all' | 'todo' | 'ongoing' | 'done' | 'ignored' | 'blocked' | 'critical' | 'flagged'

/**
 * Decide if a node should be visible for the active task filter.
 */
export function shouldShowNodeForTaskFilter(status: EntityTaskStatus | undefined, filter: TaskGraphFilter): boolean {
  if (!status) {
    return true
  }

  switch (filter) {
    case 'todo':
      return status.status === 'todo'
    case 'ongoing':
      return status.status === 'ongoing'
    case 'done':
      return status.status === 'done'
    case 'ignored':
      return status.status === 'ignored'
    case 'blocked':
      return (status.blocked_by?.length ?? 0) > 0
    case 'critical':
      return status.priority === 'critical'
    case 'flagged':
      return status.flagged === true
    case 'all':
    default:
      return true
  }
}
