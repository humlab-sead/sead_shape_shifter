/**
 * Composable for entity management
 * Wraps the entity store with convenient methods
 */

import { computed, onMounted, ref, watch } from 'vue'
import { useEntityStore } from '@/stores'
import type { EntityCreateRequest, EntityUpdateRequest } from '@/api/entities'

export interface UseEntitiesOptions {
  configName: string
  autoFetch?: boolean
  entityName?: string
}

export function useEntities(options: UseEntitiesOptions) {
  const { configName, autoFetch = true, entityName } = options
  const store = useEntityStore()
  const initialized = ref(false)

  // Computed state from store
  const entities = computed(() => store.sortedEntities)
  const selectedEntity = computed(() => store.selectedEntity)
  const currentConfigName = computed(() => store.currentConfigName)
  const loading = computed(() => store.loading)
  const error = computed(() => store.error)
  const hasUnsavedChanges = computed(() => store.hasUnsavedChanges)

  // Computed getters
  const entitiesByType = computed(() => store.entitiesByType)
  const entityCount = computed(() => store.entityCount)
  const rootEntities = computed(() => store.rootEntities)
  const isEmpty = computed(() => entities.value.length === 0)

  // Actions
  async function fetch() {
    try {
      await store.fetchEntities(configName)
      initialized.value = true
    } catch (err) {
      console.error(`Failed to fetch entities for "${configName}":`, err)
      throw err
    }
  }

  async function select(name: string) {
    try {
      return await store.selectEntity(configName, name)
    } catch (err) {
      console.error(`Failed to select entity "${name}":`, err)
      throw err
    }
  }

  async function create(data: EntityCreateRequest) {
    try {
      return await store.createEntity(configName, data)
    } catch (err) {
      console.error('Failed to create entity:', err)
      throw err
    }
  }

  async function update(name: string, data: EntityUpdateRequest) {
    try {
      return await store.updateEntity(configName, name, data)
    } catch (err) {
      console.error(`Failed to update entity "${name}":`, err)
      throw err
    }
  }

  async function remove(name: string) {
    try {
      await store.deleteEntity(configName, name)
    } catch (err) {
      console.error(`Failed to delete entity "${name}":`, err)
      throw err
    }
  }

  function markAsChanged() {
    store.markAsChanged()
  }

  function clearError() {
    store.clearError()
  }

  // Helper functions
  const entityByName = (name: string) => store.entityByName(name)
  const childrenOf = (parentName: string) => store.childrenOf(parentName)
  const hasForeignKeys = (name: string) => store.hasForeignKeys(name)

  // Auto-fetch on mount if enabled
  onMounted(async () => {
    if (autoFetch && !initialized.value) {
      await fetch()
    }

    // Auto-select entity if specified
    if (entityName && !loading.value) {
      await select(entityName)
    }
  })

  // Watch for configName changes
  watch(
    () => configName,
    async (newConfigName, oldConfigName) => {
      if (newConfigName !== oldConfigName && newConfigName) {
        initialized.value = false
        await fetch()
      }
    }
  )

  return {
    // State
    entities,
    selectedEntity,
    currentConfigName,
    loading,
    error,
    hasUnsavedChanges,
    initialized,
    isEmpty,
    // Computed
    entitiesByType,
    entityCount,
    rootEntities,
    // Actions
    fetch,
    select,
    create,
    update,
    remove,
    markAsChanged,
    clearError,
    // Helpers
    entityByName,
    childrenOf,
    hasForeignKeys,
  }
}
