/**
 * Composable for managing task status operations
 *
 * Provides reactive state and methods for tracking entity completion status,
 * fetching task status from the API, and performing task operations
 * (mark complete, mark ignored, reset).
 */

import { ref, computed } from 'vue'
import type { Ref } from 'vue'
import { apiClient } from '@/api/client'

/**
 * Task status enum matching backend TaskStatus
 */
export enum TaskStatus {
  TODO = 'todo',
  DONE = 'done',
  IGNORED = 'ignored'
}

/**
 * Task priority enum matching backend TaskPriority
 */
export enum TaskPriority {
  CRITICAL = 'critical', // Required + validation errors
  READY = 'ready',       // Required + passes validation
  WAITING = 'waiting',   // Has blockers (dependencies not done)
  OPTIONAL = 'optional'  // Not required
}

/**
 * Entity task status from API
 */
export interface EntityTaskStatus {
  entity_name: string
  status: TaskStatus
  priority: TaskPriority
  required: boolean
  exists: boolean
  validation_passed: boolean
  preview_available: boolean
  blocked_by: string[]
  issues: string[]
}

/**
 * Project-level task status from API
 */
export interface ProjectTaskStatus {
  project_name: string
  entities: Record<string, EntityTaskStatus>
  completion_stats: {
    total: number
    completed: number
    ignored: number
    todo: number
    completion_percentage: number
  }
}

/**
 * Task operation response
 */
export interface TaskOperationResponse {
  success: boolean
  message: string
  entity_name: string
  new_status: TaskStatus
}

/**
 * Composable for task status management
 */
export function useTaskStatus(projectName?: Ref<string> | string) {
  // Reactive state
  const taskStatus = ref<ProjectTaskStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed project name
  const project = computed(() =>
    typeof projectName === 'string' ? projectName : projectName?.value ?? ''
  )

  /**
   * Fetch task status for the project
   */
  async function fetchTaskStatus(): Promise<void> {
    if (!project.value) {
      error.value = 'No project specified'
      return
    }

    loading.value = true
    error.value = null

    try {
      const response = await apiClient.get<ProjectTaskStatus>(
        `/projects/${project.value}/tasks`
      )
      taskStatus.value = response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch task status'
      console.error('Failed to fetch task status:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Mark an entity as complete
   */
  async function markComplete(entityName: string): Promise<boolean> {
    if (!project.value) {
      error.value = 'No project specified'
      return false
    }

    loading.value = true
    error.value = null

    try {
      const response = await apiClient.post<TaskOperationResponse>(
        `/projects/${project.value}/tasks/${entityName}/complete`
      )

      // Update local state
      if (taskStatus.value?.entities[entityName]) {
        taskStatus.value.entities[entityName].status = TaskStatus.DONE
      }

      // Refresh full status to get updated stats
      await fetchTaskStatus()

      return response.data.success
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to mark complete'
      console.error('Failed to mark complete:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Mark an entity as ignored
   */
  async function markIgnored(entityName: string): Promise<boolean> {
    if (!project.value) {
      error.value = 'No project specified'
      return false
    }

    loading.value = true
    error.value = null

    try {
      const response = await apiClient.post<TaskOperationResponse>(
        `/projects/${project.value}/tasks/${entityName}/ignore`
      )

      // Update local state
      if (taskStatus.value?.entities[entityName]) {
        taskStatus.value.entities[entityName].status = TaskStatus.IGNORED
      }

      // Refresh full status to get updated stats
      await fetchTaskStatus()

      return response.data.success
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to mark ignored'
      console.error('Failed to mark ignored:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Reset entity status to todo
   */
  async function resetStatus(entityName: string): Promise<boolean> {
    if (!project.value) {
      error.value = 'No project specified'
      return false
    }

    loading.value = true
    error.value = null

    try {
      const response = await apiClient.delete<TaskOperationResponse>(
        `/projects/${project.value}/tasks/${entityName}`
      )

      // Update local state
      if (taskStatus.value?.entities[entityName]) {
        taskStatus.value.entities[entityName].status = TaskStatus.TODO
      }

      // Refresh full status to get updated stats
      await fetchTaskStatus()

      return response.data.success
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to reset status'
      console.error('Failed to reset status:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Get status for a specific entity
   */
  function getEntityStatus(entityName: string): EntityTaskStatus | undefined {
    return taskStatus.value?.entities[entityName]
  }

  /**
   * Check if entity is done
   */
  function isDone(entityName: string): boolean {
    return getEntityStatus(entityName)?.status === TaskStatus.DONE
  }

  /**
   * Check if entity is ignored
   */
  function isIgnored(entityName: string): boolean {
    return getEntityStatus(entityName)?.status === TaskStatus.IGNORED
  }

  /**
   * Check if entity is blocked (has unresolved dependencies)
   */
  function isBlocked(entityName: string): boolean {
    const status = getEntityStatus(entityName)
    return (status?.blocked_by?.length ?? 0) > 0
  }

  /**
   * Check if entity has validation errors
   */
  function hasErrors(entityName: string): boolean {
    const status = getEntityStatus(entityName)
    return status?.exists === true && status?.validation_passed === false
  }

  /**
   * Get entities filtered by status
   */
  function getEntitiesByStatus(status: TaskStatus): string[] {
    if (!taskStatus.value) return []
    return Object.entries(taskStatus.value.entities)
      .filter(([_, entityStatus]) => entityStatus.status === status)
      .map(([name]) => name)
  }

  /**
   * Get completion percentage
   */
  const completionPercentage = computed(() => {
    return taskStatus.value?.completion_stats.completion_percentage ?? 0
  })

  /**
   * Get completion summary text
   */
  const completionSummary = computed(() => {
    if (!taskStatus.value) return 'No data'
    const stats = taskStatus.value.completion_stats
    return `${stats.completed} of ${stats.total} entities complete`
  })

  return {
    // State
    taskStatus,
    loading,
    error,

    // Methods
    fetchTaskStatus,
    markComplete,
    markIgnored,
    resetStatus,
    getEntityStatus,
    isDone,
    isIgnored,
    isBlocked,
    hasErrors,
    getEntitiesByStatus,

    // Computed
    completionPercentage,
    completionSummary
  }
}
