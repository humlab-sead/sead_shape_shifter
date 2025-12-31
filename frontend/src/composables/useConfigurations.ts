/**
 * Composable for configuration management
 * Wraps the configuration store with convenient methods and auto-fetching
 */

import { computed, onMounted, ref } from 'vue'
import { useProjectStore } from '@/stores'
import type { ProjectCreateRequest, ConfigurationUpdateRequest } from '@/api/configurations'

export interface UseConfigurationsOptions {
  autoFetch?: boolean
  configName?: string
}

export function useConfigurations(options: UseConfigurationsOptions = {}) {
  const { autoFetch = true, configName } = options
  const store = useProjectStore()
  const initialized = ref(false)

  // Computed state from store
  const configurations = computed(() => store.sortedConfigurations)
  const selectedConfig = computed(() => store.selectedConfig)
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
      await store.fetchConfigurations()
      initialized.value = true
    } catch (err) {
      console.error('Failed to fetch configurations:', err)
      throw err
    }
  }

  async function select(name: string) {
    try {
      return await store.selectConfiguration(name)
    } catch (err) {
      console.error(`Failed to select configuration "${name}":`, err)
      throw err
    }
  }

  async function create(data: ProjectCreateRequest) {
    try {
      return await store.createConfiguration(data)
    } catch (err) {
      console.error('Failed to create configuration:', err)
      throw err
    }
  }

  async function update(name: string, data: ProjectUpdateRequest) {
    try {
      return await store.updateConfiguration(name, data)
    } catch (err) {
      console.error(`Failed to update configuration "${name}":`, err)
      throw err
    }
  }

  async function remove(name: string) {
    try {
      await store.deleteConfiguration(name)
    } catch (err) {
      console.error(`Failed to delete configuration "${name}":`, err)
      throw err
    }
  }

  async function validate(name: string) {
    try {
      return await store.validateConfiguration(name)
    } catch (err) {
      console.error(`Failed to validate configuration "${name}":`, err)
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

  async function restore(name: string, backupPath: string) {
    try {
      return await store.restoreBackup(name, backupPath)
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
  const configByName = (name: string) => store.configByName(name)
  const isEmpty = computed(() => configurations.value.length === 0)
  const count = computed(() => configurations.value.length)

  // Auto-fetch on mount if enabled
  onMounted(async () => {
    if (autoFetch && !initialized.value) {
      await fetch()
    }

    // Auto-select configuration if specified
    if (configName && !loading.value) {
      await select(configName)
    }
  })

  return {
    // State
    configurations,
    selectedConfig,
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
    select,
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
    configByName,
  }
}
