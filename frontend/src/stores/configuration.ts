import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import type { Configuration, ConfigMetadata, ValidationResult } from '@/types'
import type {
  ConfigurationCreateRequest,
  ConfigurationUpdateRequest,
  BackupInfo,
} from '@/api/configurations'

export const useConfigurationStore = defineStore('configuration', () => {
  // State
  const configurations = ref<ConfigMetadata[]>([])
  const selectedConfig = ref<Configuration | null>(null)
  const validationResult = ref<ValidationResult | null>(null)
  const backups = ref<BackupInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const hasUnsavedChanges = ref(false)

  // Getters
  const currentConfigName = computed(() => {
    return selectedConfig.value?.metadata?.name || null
  })

  const sortedConfigurations = computed(() => {
    return [...configurations.value].sort((a, b) => a.name.localeCompare(b.name))
  })

  const configByName = computed(() => {
    return (name: string) => configurations.value.find((c) => c.name === name)
  })

  const hasErrors = computed(() => {
    return validationResult.value ? validationResult.value.error_count > 0 : false
  })

  const hasWarnings = computed(() => {
    return validationResult.value ? validationResult.value.warning_count > 0 : false
  })

  // Actions
  async function fetchConfigurations() {
    loading.value = true
    error.value = null
    try {
      configurations.value = await api.configurations.list()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch configurations'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function selectConfiguration(name: string) {
    loading.value = true
    error.value = null
    try {
      selectedConfig.value = await api.configurations.get(name)
      hasUnsavedChanges.value = false
      return selectedConfig.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createConfiguration(data: ConfigurationCreateRequest) {
    loading.value = true
    error.value = null
    try {
      const config = await api.configurations.create(data)
      configurations.value.push({
        name: config.metadata?.name ?? data.name,
        entity_count: Object.keys(config.entities || {}).length,
        file_path: config.metadata?.file_path,
        created_at: config.metadata?.created_at,
        modified_at: config.metadata?.modified_at,
        is_valid: config.metadata?.is_valid,
      })
      selectedConfig.value = config
      hasUnsavedChanges.value = false
      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateConfiguration(name: string, data: ConfigurationUpdateRequest) {
    loading.value = true
    error.value = null
    try {
      const config = await api.configurations.update(name, data)
      
      // Update metadata in list
      const index = configurations.value.findIndex((c) => c.name === name)
      if (index !== -1) {
        configurations.value[index] = {
          name: config.metadata?.name ?? name,
          entity_count: Object.keys(config.entities || {}).length,
          file_path: config.metadata?.file_path,
          created_at: config.metadata?.created_at,
          modified_at: config.metadata?.modified_at,
          is_valid: config.metadata?.is_valid,
        }
      }
      
      selectedConfig.value = config
      hasUnsavedChanges.value = false
      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteConfiguration(name: string) {
    loading.value = true
    error.value = null
    try {
      await api.configurations.delete(name)
      configurations.value = configurations.value.filter((c) => c.name !== name)
      if (selectedConfig.value?.metadata?.name === name) {
        selectedConfig.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function validateConfiguration(name: string) {
    loading.value = true
    error.value = null
    try {
      validationResult.value = await api.configurations.validate(name)
      return validationResult.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to validate configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchBackups(name: string) {
    loading.value = true
    error.value = null
    try {
      backups.value = await api.configurations.listBackups(name)
      return backups.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch backups'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function restoreBackup(name: string, backupPath: string) {
    loading.value = true
    error.value = null
    try {
      const config = await api.configurations.restore(name, { backup_path: backupPath })
      selectedConfig.value = config
      
      // Update in list if exists
      const index = configurations.value.findIndex((c) => c.name === name)
      if (index !== -1 && config.metadata) {
        configurations.value[index] = {
          name: config.metadata.name,
          entity_count: config.metadata.entity_count,
          file_path: config.metadata.file_path,
          created_at: config.metadata.created_at,
          modified_at: config.metadata.modified_at,
          is_valid: config.metadata.is_valid,
        }
      }
      
      hasUnsavedChanges.value = false
      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to restore backup'
      throw err
    } finally {
      loading.value = false
    }
  }

  function markAsChanged() {
    hasUnsavedChanges.value = true
  }

  function clearError() {
    error.value = null
  }

  function clearValidation() {
    validationResult.value = null
  }

  async function getActiveConfiguration() {
    try {
      const result = await api.configurations.getActive()
      return result.name
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to get active configuration'
      return null
    }
  }

  async function activateConfiguration(name: string) {
    loading.value = true
    error.value = null
    try {
      const config = await api.configurations.activate(name)
      selectedConfig.value = config
      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to activate configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getConfigurationDataSources(name: string) {
    try {
      return await api.configurations.getDataSources(name)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to get data sources'
      throw err
    }
  }

  async function connectDataSource(name: string, sourceName: string, sourceFilename: string) {
    loading.value = true
    error.value = null
    try {
      const config = await api.configurations.connectDataSource(name, sourceName, sourceFilename)
      selectedConfig.value = config
      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to connect data source'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function disconnectDataSource(name: string, sourceName: string) {
    loading.value = true
    error.value = null
    try {
      const config = await api.configurations.disconnectDataSource(name, sourceName)
      selectedConfig.value = config
      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to disconnect data source'
      throw err
    } finally {
      loading.value = false
    }
  }

  function reset() {
    configurations.value = []
    selectedConfig.value = null
    validationResult.value = null
    backups.value = []
    loading.value = false
    error.value = null
    hasUnsavedChanges.value = false
  }

  return {
    // State
    configurations,
    selectedConfig,
    validationResult,
    backups,
    loading,
    error,
    hasUnsavedChanges,
    // Getters
    currentConfigName,
    sortedConfigurations,
    configByName,
    hasErrors,
    hasWarnings,
    // Actions
    fetchConfigurations,
    selectConfiguration,
    createConfiguration,
    updateConfiguration,
    deleteConfiguration,
    validateConfiguration,
    fetchBackups,
    restoreBackup,
    getActiveConfiguration,
    activateConfiguration,
    getConfigurationDataSources,
    connectDataSource,
    disconnectDataSource,
    markAsChanged,
    clearError,
    clearValidation,
    reset,
  }
})
