import type { EntityTaskStatus } from '@/composables/useTaskStatus'

export type TaskGraphFilter = 'all' | 'todo' | 'done' | 'ignored' | 'blocked' | 'critical'

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
    case 'done':
      return status.status === 'done'
    case 'ignored':
      return status.status === 'ignored'
    case 'blocked':
      return (status.blocked_by?.length ?? 0) > 0
    case 'critical':
      return status.priority === 'critical'
    case 'all':
    default:
      return true
  }
}
