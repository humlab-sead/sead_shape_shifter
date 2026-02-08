/**
 * Pinia store for entity reconciliation state management.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  EntityResolutionCatalog,
  ReconciliationCandidate,
  AutoReconcileResult,
  ReconciliationPreviewRow,
  EntityResolutionListItem,
  EntityResolutionCatalogCreateRequest,
  EntityResolutionCatalogUpdateRequest,
} from '@/types/reconciliation'
import { apiClient } from '@/api/client'
import { reconciliationSpecApi, reconciliationServiceApi } from '@/api/reconciliation'
// import { load } from 'js-yaml'

export const useReconciliationStore = defineStore('reconciliation', () => {
  // State
  const reconciliationConfig = ref<EntityResolutionCatalog | null>(null)
  const previewData = ref<Record<string, ReconciliationPreviewRow[]>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedTarget = ref<string | null>(null) // Currently selected target field
  
  // Specification management state
  const specifications = ref<EntityResolutionListItem[]>([])
  const selectedSpec = ref<EntityResolutionListItem | null>(null)
  const loadingSpecs = ref(false)
  const specsError = ref<string | null>(null)

  // Getters
  const reconcilableEntities = computed(() => {
    if (!reconciliationConfig.value) return []
    return Object.keys(reconciliationConfig.value.entities).filter(
      (entityName) => {
        const targetFields = reconciliationConfig.value!.entities[entityName]
        // Entity is reconcilable if it has at least one target with a service_type
        return Object.values(targetFields).some(
          (spec) => spec?.remote?.service_type != null
        )
      }
    )
  })

  // Get available targets for a specific entity
  const getEntityTargets = computed(() => {
    return (entityName: string): string[] => {
      if (!reconciliationConfig.value || !reconciliationConfig.value.entities[entityName]) {
        return []
      }
      return Object.keys(reconciliationConfig.value.entities[entityName])
    }
  })

  const hasConfig = computed(() => reconciliationConfig.value !== null)

  // Actions
  async function loadEntityResolutionCatalog(projectName: string) {
    loading.value = true
    error.value = null
    try {
      console.log(`[Reconciliation Store] Loading config for project: ${projectName}`)
      const response = await apiClient.get(`/projects/${projectName}/reconciliation`)
      console.log('[Reconciliation Store] Config loaded:', response.data)
      reconciliationConfig.value = response.data
      console.log('[Reconciliation Store] Reconcilable entities:', reconcilableEntities.value)
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to load reconciliation config'
      console.error('[Reconciliation Store] Failed to load reconciliation config:', e)
      console.error('[Reconciliation Store] Error details:', e.response)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function saveEntityResolutionCatalog(projectName: string) {
    if (!reconciliationConfig.value) {
      throw new Error('No config to save')
    }

    loading.value = true
    error.value = null
    try {
      const response = await apiClient.put(`/projects/${projectName}/reconciliation`, reconciliationConfig.value)
      reconciliationConfig.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to save reconciliation config'
      console.error('Failed to save reconciliation config:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function saveEntityResolutionCatalogRaw(projectName: string, yamlContent: string) {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.put(`/projects/${projectName}/reconciliation/raw`, yamlContent, {
        headers: { 'Content-Type': 'text/plain' }
      })
      reconciliationConfig.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to save reconciliation config'
      console.error('Failed to save reconciliation config:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function autoReconcile(
    projectName: string,
    entityName: string,
    targetField: string,
    threshold: number = 0.95,
    reviewThreshold?: number
  ): Promise<AutoReconcileResult> {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(
        `/projects/${projectName}/reconciliation/${entityName}/${targetField}/auto-reconcile-sync`,
        null,
        { params: { threshold, review_threshold: reviewThreshold } }
      )

      // Reload config to get updated mappings
      await loadEntityResolutionCatalog(projectName)

      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Auto-reconciliation failed'
      console.error('Auto-reconciliation failed:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function autoReconcileAsync(
    projectName: string,
    entityName: string,
    targetField: string,
    threshold: number = 0.95,
    reviewThreshold?: number
  ): Promise<{ operation_id: string; message: string }> {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(
        `/projects/${projectName}/reconciliation/${entityName}/${targetField}/auto-reconcile`,
        null,
        { params: { threshold, review_threshold: reviewThreshold } }
      )

      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to start reconciliation'
      console.error('Failed to start reconciliation:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateMapping(
    projectName: string,
    entityName: string,
    targetField: string,
    sourceValue: any,
    targetId: number | null,
    notes?: string
  ) {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(`/projects/${projectName}/reconciliation/${entityName}/${targetField}/mapping`, {
        source_value: sourceValue,
        target_id: targetId,
        notes,
      })
      reconciliationConfig.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to update mapping'
      console.error('Failed to update mapping:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteMapping(projectName: string, entityName: string, targetField: string, sourceValue: any) {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.delete(`/projects/${projectName}/reconciliation/${entityName}/${targetField}/mapping`, {
        params: { source_value: JSON.stringify(sourceValue) },
      })
      reconciliationConfig.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to delete mapping'
      console.error('Failed to delete mapping:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function suggestEntities(
    projectName: string,
    entityName: string,
    targetField: string,
    query: string
  ): Promise<ReconciliationCandidate[]> {
    if (query.length < 2) {
      return []
    }

    try {
      const response = await apiClient.get(`/projects/${projectName}/reconciliation/${entityName}/${targetField}/suggest`, {
        params: { query },
      })
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to get suggestions'
      console.error('Failed to get entity suggestions:', e)
      return []
    }
  }

  async function loadPreviewData(projectName: string, entityName: string, targetField: string) {
    try {
      console.log(`[Reconciliation Store] Loading preview data for ${entityName}.${targetField}`)
      const response = await apiClient.get(`/projects/${projectName}/reconciliation/${entityName}/${targetField}/preview`)
      
      // Response is already enriched with reconciliation data
      previewData.value[entityName] = response.data
      console.log(`[Reconciliation Store] Loaded ${response.data.length} preview rows for ${entityName}.${targetField}`)
    } catch (e: any) {
      console.error('[Reconciliation Store] Failed to load preview data:', e)
      previewData.value[entityName] = []
      // Don't throw - allow UI to show empty state
    }
  }

  function clearError() {
    error.value = null
  }

  async function checkServiceHealth() {
    try {
      return await reconciliationServiceApi.checkHealth()
    } catch (e: any) {
      console.error('Failed to check reconciliation service health:', e)
      throw e
    }
  }

  async function getServiceManifest() {
    try {
      return await reconciliationServiceApi.getManifest()
    } catch (e: any) {
      console.error('Failed to get reconciliation service manifest:', e)
      throw e
    }
  }

  function $reset() {
    reconciliationConfig.value = null
    previewData.value = {}
    loading.value = false
    error.value = null
    selectedTarget.value = null
    specifications.value = []
    selectedSpec.value = null
    loadingSpecs.value = false
    specsError.value = null
  }

  // Specification management actions

  async function loadSpecifications(projectName: string) {
    loadingSpecs.value = true
    specsError.value = null
    try {
      specifications.value = await reconciliationSpecApi.listSpecifications(projectName)
    } catch (e: any) {
      specsError.value = e.response?.data?.detail || 'Failed to load specifications'
      console.error('Failed to load specifications:', e)
      throw e
    } finally {
      loadingSpecs.value = false
    }
  }

  async function createSpecification(
    projectName: string,
    request: EntityResolutionCatalogCreateRequest
  ) {
    loadingSpecs.value = true
    specsError.value = null
    try {
      const updatedConfig = await reconciliationSpecApi.createSpecification(
        projectName,
        request
      )
      reconciliationConfig.value = updatedConfig
      // Reload specifications list
      await loadSpecifications(projectName)
    } catch (e: any) {
      specsError.value = e.response?.data?.detail || 'Failed to create specification'
      console.error('Failed to create specification:', e)
      throw e
    } finally {
      loadingSpecs.value = false
    }
  }

  async function updateSpecification(
    projectName: string,
    entityName: string,
    targetField: string,
    request: EntityResolutionCatalogUpdateRequest
  ) {
    loadingSpecs.value = true
    specsError.value = null
    try {
      const updatedConfig = await reconciliationSpecApi.updateSpecification(
        projectName,
        entityName,
        targetField,
        request
      )
      reconciliationConfig.value = updatedConfig
      // Reload specifications list
      await loadSpecifications(projectName)
    } catch (e: any) {
      specsError.value = e.response?.data?.detail || 'Failed to update specification'
      console.error('Failed to update specification:', e)
      throw e
    } finally {
      loadingSpecs.value = false
    }
  }

  async function deleteSpecification(
    projectName: string,
    entityName: string,
    targetField: string,
    force: boolean = false
  ) {
    loadingSpecs.value = true
    specsError.value = null
    try {
      const updatedConfig = await reconciliationSpecApi.deleteSpecification(
        projectName,
        entityName,
        targetField,
        force
      )
      reconciliationConfig.value = updatedConfig
      // Reload specifications list
      await loadSpecifications(projectName)
      // Clear selected spec if it was deleted
      if (
        selectedSpec.value?.entity_name === entityName &&
        selectedSpec.value?.target_field === targetField
      ) {
        selectedSpec.value = null
      }
    } catch (e: any) {
      specsError.value = e.response?.data?.detail || 'Failed to delete specification'
      console.error('Failed to delete specification:', e)
      throw e
    } finally {
      loadingSpecs.value = false
    }
  }

  async function getAvailableFields(projectName: string, entityName: string): Promise<string[]> {
    try {
      return await reconciliationSpecApi.getAvailableFields(projectName, entityName)
    } catch (e: any) {
      console.error('Failed to get available fields:', e)
      throw e
    }
  }

  async function getMappingCount(
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<number> {
    try {
      return await reconciliationSpecApi.getMappingCount(projectName, entityName, targetField)
    } catch (e: any) {
      console.error('Failed to get mapping count:', e)
      throw e
    }
  }


  return {
    // State
    reconciliationConfig,
    previewData,
    loading,
    error,
    selectedTarget,
    specifications,
    selectedSpec,
    loadingSpecs,
    specsError,

    // Getters
    reconcilableEntities,
    getEntityTargets,
    hasConfig,

    // Actions
    loadEntityResolutionCatalog,
    saveEntityResolutionCatalog,
    saveEntityResolutionCatalogRaw,
    autoReconcile,
    autoReconcileAsync,
    updateMapping,
    deleteMapping,
    suggestEntities,
    loadPreviewData,
    checkServiceHealth,
    getServiceManifest,
    clearError,
    $reset,
    
    // Specification management actions
    loadSpecifications,
    createSpecification,
    updateSpecification,
    deleteSpecification,
    getAvailableFields,
    getMappingCount,
  }
})
