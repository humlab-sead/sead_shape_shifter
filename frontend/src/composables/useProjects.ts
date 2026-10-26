/**
 * Composable for project management
 * Wraps the project store with convenient methods and auto-fetching
 */

import { computed, onMounted, ref } from 'vue'
import { useProjectStore } from '@/stores'
import type { ProjectCreateRequest, ProjectUpdateRequest } from '@/api/projects'

export interface UseProjectsOptions {
  autoFetch?: boolean
  projectName?: string
}

export function useProjects(options: UseProjectsOptions = {}) {
  const { autoFetch = true, projectName } = options
  const store = useProjectStore()
  const initialized = ref(false)

  // Computed state from store
  const projects = computed(() => store.sortedProjects)
  const selectedProject = computed(() => store.selectedProject)
  const validationResult = computed(() => store.validationResult)
  const backups = computed(() => store.backups)
  const loading = computed(() => store.loading)
  const error = computed(() => store.error)
  const hasUnsavedChanges = computed(() => store.hasUnsavedChanges)
  const hasErrors = computed(() => store.hasErrors)
  const hasWarnings = computed(() => store.hasWarnings)

  // Actions
  async function fetch() {
    try {
      await store.fetchProjects()
      initialized.value = true
    } catch (err) {
      console.error('Failed to fetch projects:', err)
      throw err
    }
  }

  /**
   * Refresh the project list in the background without blocking the view.
   * Used when a cached list is shown but its freshness window has expired.
   */
  async function revalidate() {
    try {
      await store.fetchProjects({ silent: true })
    } catch (err) {
      console.error('Failed to revalidate projects:', err)
    }
  }

  /**
   * Load the project list on mount using a stale-while-revalidate strategy: a
   * cached list is shown immediately and only re-fetched when it is stale, while
   * a cold cache blocks on the first fetch.
   */
  async function ensureLoaded() {
    if (store.projects.length > 0) {
      initialized.value = true
      if (store.isProjectsStale()) {
        void revalidate()
      }
      return
    }
    await fetch()
  }

  async function select(name: string) {
    try {
      return await store.selectProject(name)
    } catch (err) {
      console.error(`Failed to select project "${name}":`, err)
      throw err
    }
  }

  async function refresh(name: string) {
    try {
      return await store.refreshProject(name)
    } catch (err) {
      console.error(`Failed to refresh project "${name}":`, err)
      throw err
    }
  }

  async function create(data: ProjectCreateRequest) {
    try {
      return await store.createProject(data)
    } catch (err) {
      console.error('Failed to create project:', err)
      throw err
    }
  }

  async function update(name: string, data: ProjectUpdateRequest) {
    try {
      return await store.updateProject(name, data)
    } catch (err) {
      console.error(`Failed to update project "${name}":`, err)
      throw err
    }
  }

  async function remove(name: string) {
    try {
      await store.deleteProject(name)
    } catch (err) {
      console.error(`Failed to delete project "${name}":`, err)
      throw err
    }
  }

  async function validate(name: string) {
    try {
      return await store.validateProject(name)
    } catch (err) {
      console.error(`Failed to validate project "${name}":`, err)
      throw err
    }
  }

  async function fetchBackups(name: string) {
    try {
      return await store.fetchBackups(name)
    } catch (err) {
      console.error(`Failed to fetch backups for "${name}":`, err)
      throw err
    }
  }

  async function restore(name: string, backupName: string) {
    try {
      return await store.restoreBackup(name, backupName)
    } catch (err) {
      console.error(`Failed to restore backup for "${name}":`, err)
      throw err
    }
  }

  function markAsChanged() {
    store.markAsChanged()
  }

  function clearError() {
    store.clearError()
  }

  function clearValidation() {
    store.clearValidation()
  }

  // Helper getters
  const projectByName = (name: string) => store.projectByName(name)
  const isEmpty = computed(() => projects.value.length === 0)
  const count = computed(() => projects.value.length)

  // Auto-fetch on mount if enabled
  onMounted(async () => {
    if (autoFetch && !initialized.value) {
      await ensureLoaded()
    }

    // Auto-select project if specified
    if (projectName && !loading.value) {
      await select(projectName)
    }
  })

  return {
    // State
    projects,
    selectedProject,
    validationResult,
    backups,
    loading,
    error,
    hasUnsavedChanges,
    hasErrors,
    hasWarnings,
    initialized,
    isEmpty,
    count,
    // Actions
    fetch,
    revalidate,
    ensureLoaded,
    select,
    refresh,
    create,
    update,
    remove,
    validate,
    fetchBackups,
    restore,
    markAsChanged,
    clearError,
    clearValidation,
    // Helpers
    projectByName,
  }
}
