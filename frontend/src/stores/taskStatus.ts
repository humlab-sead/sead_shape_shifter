/**
 * Pinia store for task status management
 *
 * Provides centralized state management for entity task status across
 * the application. Integrates with useTaskStatus composable.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ProjectTaskStatus, EntityTaskStatus, TaskStatus } from '@/composables/useTaskStatus'
import { useTaskStatus } from '@/composables/useTaskStatus'

export const useTaskStatusStore = defineStore('taskStatus', () => {
  // State
  const currentProjectName = ref<string>('')
  const taskStatus = ref<ProjectTaskStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const autoRefreshEnabled = ref(true)

  // Composable instance
  let taskComposable = useTaskStatus(currentProjectName)

  /**
   * Initialize store for a specific project
   */
  async function initialize(projectName: string): Promise<void> {
    if (currentProjectName.value === projectName && taskStatus.value) {
      // Already initialized for this project
      return
    }

    currentProjectName.value = projectName
    taskComposable = useTaskStatus(currentProjectName)
    await refresh()
  }

  /**
   * Refresh task status from API
   */
  async function refresh(): Promise<void> {
    if (!currentProjectName.value) return

    loading.value = true
    error.value = null

    await taskComposable.fetchTaskStatus()

    // Sync state from composable
    taskStatus.value = taskComposable.taskStatus.value
    error.value = taskComposable.error.value
    loading.value = taskComposable.loading.value
  }

  /**
   * Mark entity as complete
   */
  async function markComplete(entityName: string): Promise<boolean> {
    const success = await taskComposable.markComplete(entityName)
    
    // Sync state
    taskStatus.value = taskComposable.taskStatus.value
    error.value = taskComposable.error.value
    
    return success
  }

  /**
   * Mark entity as ignored
   */
  async function markIgnored(entityName: string): Promise<boolean> {
    const success = await taskComposable.markIgnored(entityName)
    
    // Sync state
    taskStatus.value = taskComposable.taskStatus.value
    error.value = taskComposable.error.value
    
    return success
  }

  /**
   * Mark entity as ongoing
   */
  async function markOngoing(entityName: string): Promise<boolean> {
    const success = await taskComposable.markOngoing(entityName)
    
    // Sync state
    taskStatus.value = taskComposable.taskStatus.value
    error.value = taskComposable.error.value
    
    return success
  }

  /**
   * Mark entity as todo (planned but not yet created)
   */
  async function markTodo(entityName: string): Promise<boolean> {
    const success = await taskComposable.markTodo(entityName)
    
    // Sync state
    taskStatus.value = taskComposable.taskStatus.value
    error.value = taskComposable.error.value
    
    return success
  }

  /**
   * Reset entity status to todo
   */
  async function resetStatus(entityName: string): Promise<boolean> {
    const success = await taskComposable.resetStatus(entityName)
    
    // Sync state
    taskStatus.value = taskComposable.taskStatus.value
    error.value = taskComposable.error.value
    
    return success
  }

  /**
   * Toggle flagged status for entity
   */
  async function toggleFlagged(entityName: string): Promise<boolean> {
    const success = await taskComposable.toggleFlagged(entityName)
    
    // Sync state
    taskStatus.value = taskComposable.taskStatus.value
    error.value = taskComposable.error.value
    
    return success
  }

  /**
   * Get status for specific entity
   */
  function getEntityStatus(entityName: string): EntityTaskStatus | undefined {
    return taskStatus.value?.entities[entityName]
  }

  /**
   * Update local note presence for a specific entity without a full refresh.
   */
  function setEntityHasNote(entityName: string, hasNote: boolean): void {
    const entityStatus = taskStatus.value?.entities[entityName]
    if (!entityStatus) {
      return
    }

    entityStatus.has_note = hasNote
  }

  /**
   * Check if entity is done
   */
  function isDone(entityName: string): boolean {
    return getEntityStatus(entityName)?.status === 'done'
  }

  /**
   * Check if entity is ongoing
   */
  function isOngoing(entityName: string): boolean {
    return getEntityStatus(entityName)?.status === 'ongoing'
  }

  /**
   * Check if entity is ignored
   */
  function isIgnored(entityName: string): boolean {
    return getEntityStatus(entityName)?.status === 'ignored'
  }

  /**
   * Check if entity is flagged
   */
  function isFlagged(entityName: string): boolean {
    return getEntityStatus(entityName)?.flagged ?? false
  }

  /**
   * Check if entity is blocked
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
   * Get all entities with a specific status
   */
  function getEntitiesByStatus(status: TaskStatus): string[] {
    if (!taskStatus.value) return []
    return Object.entries(taskStatus.value.entities)
      .filter(([_, entityStatus]) => entityStatus.status === status)
      .map(([name]) => name)
  }

  // Computed properties
  const completionStats = computed(() => taskStatus.value?.completion_stats)
  
  const completionPercentage = computed(() => 
    taskStatus.value?.completion_stats.completion_percentage ?? 0
  )
  
  const completionSummary = computed(() => {
    if (!taskStatus.value) return 'No data'
    const stats = taskStatus.value.completion_stats
    return `${stats.done} of ${stats.total} complete`
  })

  const hasData = computed(() => taskStatus.value !== null)

  /**
   * Reset store state
   */
  function $reset() {
    currentProjectName.value = ''
    taskStatus.value = null
    loading.value = false
    error.value = null
    autoRefreshEnabled.value = true
  }

  return {
    // State
    currentProjectName,
    taskStatus,
    loading,
    error,
    autoRefreshEnabled,

    // Computed
    completionStats,
    completionPercentage,
    completionSummary,
    hasData,

    // Actions
    initialize,
    refresh,
    markComplete,
    markIgnored,
    markOngoing,
    markTodo,
    resetStatus,
    toggleFlagged,
    getEntityStatus,
    setEntityHasNote,
    isDone,
    isOngoing,
    isIgnored,
    isFlagged,
    isBlocked,
    hasErrors,
    getEntitiesByStatus,
    $reset
  }
})
