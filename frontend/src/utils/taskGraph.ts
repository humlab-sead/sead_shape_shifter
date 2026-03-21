import type { EntityTaskStatus } from '@/composables/useTaskStatus'

export type TaskGraphFilter = 'all' | 'todo' | 'ongoing' | 'done' | 'ignored' | 'blocked' | 'critical' | 'flagged'
export type GraphColorByMode = 'task' | 'type'

export const TASK_STATUS_NODE_CLASSES = ['task-todo', 'task-done', 'task-ignored', 'task-ongoing', 'task-blocked', 'task-critical', 'task-ready', 'task-flagged', 'task-has-note']

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

/**
 * Compute task status classes applied to graph nodes.
 * Only one primary status class is applied, while `task-flagged` can be combined.
 * Derived states like blocked/critical/ready take precedence over the default todo state.
 */
export function getTaskStatusNodeClasses(status: EntityTaskStatus | undefined): string[] {
  if (!status) {
    return []
  }

  const classes: string[] = []

  if (status.status === 'done') {
    classes.push('task-done')
  } else if (status.status === 'ignored') {
    classes.push('task-ignored')
  } else if (status.status === 'ongoing') {
    classes.push('task-ongoing')
  } else if ((status.blocked_by?.length ?? 0) > 0) {
    classes.push('task-blocked')
  } else if (status.priority === 'critical') {
    classes.push('task-critical')
  } else if (status.priority === 'ready') {
    classes.push('task-ready')
  } else if (status.status === 'todo') {
    classes.push('task-todo')
  }

  if (status.flagged === true) {
    classes.push('task-flagged')
  }

  if (status.has_note === true) {
    classes.push('task-has-note')
  }

  return classes
}
