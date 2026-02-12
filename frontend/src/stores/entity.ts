import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import { useProjectStore } from '@/stores'
import type { EntityResponse, EntityCreateRequest, EntityUpdateRequest } from '@/api/entities'

export const useEntityStore = defineStore('entity', () => {
  // State
  const entities = ref<EntityResponse[]>([])
  const selectedEntity = ref<EntityResponse | null>(null)
  const currentProjectName = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const hasUnsavedChanges = ref(false)
  
  // Overlay state
  const showEditorOverlay = ref(false)
  const overlayEntityName = ref<string | null>(null)
  const overlayInitialTab = ref<'form' | 'yaml'>('form')

  // Cross-store access
  const projectStore = useProjectStore()

  // Refresh project from disk to ensure in-memory state matches saved state
  async function refreshProjectState(projectName: string) {
    if (projectStore.selectedProject?.metadata?.name === projectName) {
      await projectStore.refreshProject(projectName)
    }
  }

  // Getters
  const entitiesByType = computed(() => {
    const grouped: Record<string, EntityResponse[]> = {}
    entities.value.forEach((entity: EntityResponse) => {
      const type = (entity.entity_data.type as string) || 'unknown'
      if (!grouped[type]) {
        grouped[type] = []
      }
      grouped[type].push(entity)
    })
    return grouped
  })

  const entityCount = computed(() => entities.value.length)

  const sortedEntities = computed(() => {
    return [...entities.value].sort((a, b) => a.name.localeCompare(b.name))
  })

  const entityByName = computed(() => {
    return (name: string) => entities.value.find((e: EntityResponse) => e.name === name)
  })

  const rootEntities = computed(() => {
    return entities.value.filter((e: EntityResponse) => !e.entity_data.source)
  })

  const childrenOf = computed(() => {
    return (parentName: string) => {
      return entities.value.filter((e: EntityResponse) => e.entity_data.source === parentName)
    }
  })

  const hasForeignKeys = computed(() => {
    return (entityName: string) => {
      const entity = entities.value.find((e: EntityResponse) => e.name === entityName)
      const foreignKeys = entity?.entity_data.foreign_keys
      return Array.isArray(foreignKeys) && foreignKeys.length > 0
    }
  })

  // Actions
  async function fetchEntities(projectName: string) {
    console.log('[EntityStore] fetchEntities called:', { projectName, stack: new Error().stack })
    loading.value = true
    error.value = null
    currentProjectName.value = projectName
    try {
      entities.value = await api.entities.list(projectName)
      console.log('[EntityStore] fetchEntities complete:', { count: entities.value.length })
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch entities'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function selectEntity(projectName: string, entityName: string) {
    loading.value = true
    error.value = null
    try {
      selectedEntity.value = await api.entities.get(projectName, entityName)
      hasUnsavedChanges.value = false
      return selectedEntity.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load entity'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createEntity(projectName: string, data: EntityCreateRequest) {
    loading.value = true
    error.value = null
    try {
      const entity = await api.entities.create(projectName, data)
      entities.value.push(entity)
      selectedEntity.value = entity
      hasUnsavedChanges.value = false
      
      // Refresh project from disk to sync in-memory state
      await refreshProjectState(projectName)
      
      return entity
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create entity'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateEntity(projectName: string, entityName: string, data: EntityUpdateRequest) {
    console.log('[EntityStore] updateEntity called:', { projectName, entityName, hasData: !!data })
    loading.value = true
    error.value = null
    try {
      const entity = await api.entities.update(projectName, entityName, data)
      console.log('[EntityStore] Update API call complete:', { entityName: entity.name })

      // Update entity in list
      const index = entities.value.findIndex((e: EntityResponse) => e.name === entityName)
      if (index !== -1) {
        const oldEntity = entities.value[index]
        entities.value[index] = entity
        console.log('[EntityStore] Entity replaced in list:', {
          index,
          oldEntity: oldEntity.name,
          newEntity: entity.name,
          sameReference: oldEntity === entity
        })
      }

      selectedEntity.value = entity
      hasUnsavedChanges.value = false
      
      // Note: Backend already persists entity to disk.
      // Don't call refreshProjectState() here as it causes component recreation
      // which resets dialog state (closes the entity editor).
      
      console.log('[EntityStore] updateEntity complete')
      return entity
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update entity'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteEntity(projectName: string, entityName: string) {
    loading.value = true
    error.value = null
    try {
      await api.entities.delete(projectName, entityName)
      entities.value = entities.value.filter((e: EntityResponse) => e.name !== entityName)
      if (selectedEntity.value?.name === entityName) {
        selectedEntity.value = null
      }
      
      // Note: Backend already persists deletion to disk.
      // Don't call refreshProjectState() here as it causes unnecessary component recreation.
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete entity'
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

  function reset() {
    entities.value = []
    selectedEntity.value = null
    currentProjectName.value = null
    loading.value = false
    error.value = null
    hasUnsavedChanges.value = false
    showEditorOverlay.value = false
    overlayEntityName.value = null
  }
  
  // Overlay management
  function openEditorOverlay(entityName: string, initialTab: 'form' | 'yaml' = 'form') {
    overlayEntityName.value = entityName
    overlayInitialTab.value = initialTab
    showEditorOverlay.value = true
  }
  
  function closeEditorOverlay() {
    showEditorOverlay.value = false
    overlayEntityName.value = null
    overlayInitialTab.value = 'form'
  }

  return {
    // State
    entities,
    selectedEntity,
    currentProjectName,
    loading,
    error,
    hasUnsavedChanges,
    showEditorOverlay,
    overlayEntityName,
    overlayInitialTab,
    // Getters
    entitiesByType,
    entityCount,
    sortedEntities,
    entityByName,
    rootEntities,
    childrenOf,
    hasForeignKeys,
    // Actions
    fetchEntities,
    selectEntity,
    createEntity,
    updateEntity,
    deleteEntity,
    markAsChanged,
    clearError,
    reset,
    openEditorOverlay,
    closeEditorOverlay,
  }
})
