import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import { useSessionStore } from '@/stores/session'
import type { Project, ProjectMetadata, ValidationResult } from '@/types'
import type { ProjectCreateRequest, ProjectUpdateRequest, BackupInfo, MetadataUpdateRequest } from '@/api/projects'

export const useProjectStore = defineStore('project', () => {
  // State
  const projects = ref<ProjectMetadata[]>([])
  const selectedProject = ref<Project | null>(null)
  const validationResult = ref<ValidationResult | null>(null)
  const backups = ref<BackupInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const hasUnsavedChanges = ref(false)

  // Getters
  const currentProjectName = computed(() => {
    return selectedProject.value?.metadata?.name || null
  })

  const sortedProjects = computed(() => {
    return [...projects.value].sort((a, b) => a.name.localeCompare(b.name))
  })

  const projectByName = computed(() => {
    return (name: string) => projects.value.find((c) => c.name === name)
  })

  const hasErrors = computed(() => {
    return validationResult.value ? validationResult.value.error_count > 0 : false
  })

  const hasWarnings = computed(() => {
    return validationResult.value ? validationResult.value.warning_count > 0 : false
  })

  // Actions
  async function fetchProjects() {
    loading.value = true
    error.value = null
    try {
      projects.value = await api.projects.list()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch projects'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function selectProject(name: string) {
    loading.value = true
    error.value = null
    try {
      selectedProject.value = await api.projects.get(name)
      hasUnsavedChanges.value = false
      return selectedProject.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: ProjectCreateRequest) {
    loading.value = true
    error.value = null
    try {
      const config = await api.projects.create(data)
      projects.value.push({
        name: config.metadata?.name ?? data.name,
        entity_count: Object.keys(config.entities || {}).length,
        file_path: config.metadata?.file_path,
        created_at: config.metadata?.created_at,
        modified_at: config.metadata?.modified_at,
        is_valid: config.metadata?.is_valid,
      })
      selectedProject.value = config
      hasUnsavedChanges.value = false
      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateProject(name: string, data: ProjectUpdateRequest) {
    loading.value = true
    error.value = null
    try {
      const config = await api.projects.update(name, data)

      // Update metadata in list
      const index = projects.value.findIndex((c) => c.name === name)
      if (index !== -1) {
        projects.value[index] = {
          name: config.metadata?.name ?? name,
          entity_count: Object.keys(config.entities || {}).length,
          file_path: config.metadata?.file_path,
          created_at: config.metadata?.created_at,
          modified_at: config.metadata?.modified_at,
          is_valid: config.metadata?.is_valid,
        }
      }

      selectedProject.value = config
      hasUnsavedChanges.value = false
      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateMetadata(name: string, data: MetadataUpdateRequest) {
    loading.value = true
    error.value = null
    try {
      const config = await api.projects.updateMetadata(name, data)

      // Update metadata in list
      const oldName = name
      const newName = config.metadata?.name ?? name
      const index = projects.value.findIndex((c) => c.name === oldName)

      if (index !== -1 && config.metadata) {
        projects.value[index] = {
          name: config.metadata.name,
          description: config.metadata.description,
          version: config.metadata.version,
          entity_count: config.metadata.entity_count,
          file_path: config.metadata.file_path,
          created_at: config.metadata.created_at,
          modified_at: config.metadata.modified_at,
          is_valid: config.metadata.is_valid,
          default_entity: config.metadata.default_entity,
        }
      }

      selectedProject.value = config
      hasUnsavedChanges.value = false

      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update metadata'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(name: string) {
    loading.value = true
    error.value = null
    try {
      await api.projects.delete(name)
      projects.value = projects.value.filter((c) => c.name !== name)
      if (selectedProject.value?.metadata?.name === name) {
        selectedProject.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function validateProject(name: string) {
    loading.value = true
    error.value = null
    try {
      validationResult.value = await api.projects.validate(name)
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
      backups.value = await api.projects.listBackups(name)
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
      const config = await api.projects.restore(name, { backup_path: backupPath })
      selectedProject.value = config

      // Update in list if exists
      const index = projects.value.findIndex((c) => c.name === name)
      if (index !== -1 && config.metadata) {
        projects.value[index] = {
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

    // Mark session as modified if active
    const sessionStore = useSessionStore()
    if (sessionStore.hasActiveSession) {
      sessionStore.markModified()
    }
  }

  /**
   * Save current configuration (session-aware).
   */
  async function saveProject() {
    if (!selectedProject.value?.metadata?.name) {
      throw new Error('No configuration selected')
    }

    const sessionStore = useSessionStore()
    const name = selectedProject.value.metadata.name

    // Build update request
    const updateData: ProjectUpdateRequest = {
      entities: selectedProject.value.entities,
      options: selectedProject.value.options || {},
    }

    // Include version if session active (optimistic locking)
    if (sessionStore.hasActiveSession) {
      ;(updateData as any).version = sessionStore.version
    }

    loading.value = true
    error.value = null

    try {
      const config = await api.projects.update(name, updateData)

      // Update metadata in list
      const index = projects.value.findIndex((c) => c.name === name)
      if (index !== -1 && config.metadata) {
        projects.value[index] = {
          name: config.metadata.name,
          entity_count: config.metadata.entity_count,
          file_path: config.metadata.file_path,
          created_at: config.metadata.created_at,
          modified_at: config.metadata.modified_at,
          is_valid: config.metadata.is_valid,
        }
      }

      selectedProject.value = config
      hasUnsavedChanges.value = false

      // Increment session version on successful save
      if (sessionStore.hasActiveSession) {
        sessionStore.incrementVersion()
      }

      return config
    } catch (err: any) {
      // Handle version conflict (409)
      if (err?.response?.status === 409) {
        error.value = 'Project was modified by another user. Please reload and merge changes.'
      } else {
        error.value = err instanceof Error ? err.message : 'Failed to save configuration'
      }
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearValidation() {
    validationResult.value = null
  }

  async function getActiveProject() {
    try {
      const result = await api.projects.getActive()
      return result.name
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to get active configuration'
      return null
    }
  }

  async function activateProject(name: string) {
    loading.value = true
    error.value = null
    try {
      const config = await api.projects.activate(name)
      selectedProject.value = config
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
      return await api.projects.getDataSources(name)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to get data sources'
      throw err
    }
  }

  async function connectDataSource(name: string, sourceName: string, sourceFilename: string) {
    loading.value = true
    error.value = null
    try {
      const config = await api.projects.connectDataSource(name, sourceName, sourceFilename)
      selectedProject.value = config
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
      const config = await api.projects.disconnectDataSource(name, sourceName)
      selectedProject.value = config
      return config
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to disconnect data source'
      throw err
    } finally {
      loading.value = false
    }
  }

  function reset() {
    projects.value = []
    selectedProject.value = null
    validationResult.value = null
    backups.value = []
    loading.value = false
    error.value = null
    hasUnsavedChanges.value = false
  }

  return {
    // State
    projects,
    selectedProject,
    validationResult,
    backups,
    loading,
    error,
    hasUnsavedChanges,
    // Getters
    currentProjectName,
    sortedProjects,
    projectByName,
    hasErrors,
    hasWarnings,
    // Actions
    fetchProjects,
    selectProject,
    createProject,
    updateProject,
    updateMetadata,
    deleteProject,
    validateProject,
    fetchBackups,
    restoreBackup,
    getActiveProject,
    activateProject,
    getConfigurationDataSources,
    connectDataSource,
    disconnectDataSource,
    saveProject,
    markAsChanged,
    clearError,
    clearValidation,
    reset,
  }
})
