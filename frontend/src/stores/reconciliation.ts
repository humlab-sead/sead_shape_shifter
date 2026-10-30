/**
 * Pinia store for entity reconciliation state management.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  EntityResolutionCatalog,
  DeleteSpecificationResult,
  ReconciliationCandidate,
  AutoReconcileResult,
  ExportToMappingResult,
  ReconciliationPreviewRow,
  EntityResolutionListItem,
  EntityResolutionCatalogCreateRequest,
  EntityResolutionCatalogUpdateRequest,
  DecisionUpdateRequest,
  MappingEntityResponse,
} from '@/types/reconciliation'
import { apiClient } from '@/api/client'
import { reconciliationSpecApi, reconciliationServiceApi } from '@/api/reconciliation'
// import { load } from 'js-yaml'

type PreviewDataByProject = Record<string, Record<string, Record<string, ReconciliationPreviewRow[]>>>
type PreviewErrorsByProject = Record<string, Record<string, Record<string, string>>>
type MappingDataByProject = Record<string, Record<string, MappingEntityResponse>>

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response
    const detail = response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

export const useReconciliationStore = defineStore('reconciliation', () => {
  // State
  const reconciliationConfig = ref<EntityResolutionCatalog | null>(null)
  const previewData = ref<PreviewDataByProject>({})
  const previewErrors = ref<PreviewErrorsByProject>({})
  const mappingData = ref<MappingDataByProject>({})
  const mappingErrors = ref<Record<string, Record<string, string>>>({})
  const mappingLoading = ref<Record<string, Record<string, boolean>>>({})
  const previewRequestVersions = new Map<string, number>()
  const mappingRequestVersions = new Map<string, number>()
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
    return Object.keys(reconciliationConfig.value.entities).filter((entityName) => {
      const targetFields = reconciliationConfig.value!.entities[entityName]
      if (!targetFields) return false
      // Entity is reconcilable if it has at least one target with a service_type
      return Object.values(targetFields).some((spec) => spec?.remote?.service_type != null)
    })
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
        headers: { 'Content-Type': 'text/plain' },
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
      const result = await reconciliationServiceApi.autoReconcile(
        projectName,
        entityName,
        targetField,
        threshold,
        reviewThreshold
      )

      // Reload config to get updated mappings
      await loadEntityResolutionCatalog(projectName)

      return result
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
    request: DecisionUpdateRequest,
    notes?: string
  ) {
    loading.value = true
    error.value = null
    try {
      const decision = notes === undefined ? request : { ...request, notes }
      reconciliationConfig.value = await reconciliationServiceApi.updateDecision(
        projectName,
        entityName,
        targetField,
        decision
      )
      await Promise.all([
        loadEntityResolutionCatalog(projectName),
        loadPreviewData(projectName, entityName, targetField),
      ])
    } catch (e: any) {
      error.value = getErrorMessage(e, 'Failed to update mapping')
      console.error('Failed to update mapping:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteMapping(projectName: string, entityName: string, targetField: string, localKeyValue: string) {
    loading.value = true
    error.value = null
    try {
      reconciliationConfig.value = await reconciliationServiceApi.deleteDecision(
        projectName,
        entityName,
        targetField,
        localKeyValue
      )
      await Promise.all([
        loadEntityResolutionCatalog(projectName),
        loadPreviewData(projectName, entityName, targetField),
      ])
    } catch (e: any) {
      error.value = getErrorMessage(e, 'Failed to delete mapping')
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
      return await reconciliationServiceApi.suggestEntities(projectName, entityName, targetField, query)
    } catch (e: any) {
      error.value = getErrorMessage(e, 'Failed to get suggestions')
      console.error('Failed to get entity suggestions:', e)
      throw e
    }
  }

  function setPreviewError(projectName: string, entityName: string, targetField: string, message: string | null) {
    const projectErrors = previewErrors.value[projectName] ?? {}
    const entityErrors = { ...(projectErrors[entityName] ?? {}) }
    if (message === null) {
      delete entityErrors[targetField]
    } else {
      entityErrors[targetField] = message
    }
    previewErrors.value = {
      ...previewErrors.value,
      [projectName]: { ...projectErrors, [entityName]: entityErrors },
    }
  }

  async function loadPreviewData(
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<ReconciliationPreviewRow[]> {
    const requestKey = JSON.stringify([projectName, entityName, targetField])
    const requestVersion = (previewRequestVersions.get(requestKey) ?? 0) + 1
    previewRequestVersions.set(requestKey, requestVersion)
    setPreviewError(projectName, entityName, targetField, null)
    try {
      const rows = await reconciliationServiceApi.getPreview(projectName, entityName, targetField)
      if (previewRequestVersions.get(requestKey) === requestVersion) {
        const projectData = previewData.value[projectName] ?? {}
        const entityData = projectData[entityName] ?? {}
        previewData.value = {
          ...previewData.value,
          [projectName]: { ...projectData, [entityName]: { ...entityData, [targetField]: rows } },
        }
      }
      return rows
    } catch (e: any) {
      const message = getErrorMessage(e, 'Failed to load reconciliation preview')
      if (previewRequestVersions.get(requestKey) === requestVersion) {
        setPreviewError(projectName, entityName, targetField, message)
      }
      console.error('[Reconciliation Store] Failed to load preview data:', e)
      throw e
    }
  }

  async function loadMappingData(projectName: string, entityName: string): Promise<MappingEntityResponse> {
    const requestKey = JSON.stringify([projectName, entityName])
    const requestVersion = (mappingRequestVersions.get(requestKey) ?? 0) + 1
    mappingRequestVersions.set(requestKey, requestVersion)
    const projectLoading = mappingLoading.value[projectName] ?? {}
    mappingLoading.value = { ...mappingLoading.value, [projectName]: { ...projectLoading, [entityName]: true } }
    const projectErrors = { ...(mappingErrors.value[projectName] ?? {}) }
    delete projectErrors[entityName]
    mappingErrors.value = { ...mappingErrors.value, [projectName]: projectErrors }

    try {
      const result = await reconciliationServiceApi.getEntityMapping(projectName, entityName)
      if (mappingRequestVersions.get(requestKey) === requestVersion) {
        const projectMappings = mappingData.value[projectName] ?? {}
        mappingData.value = { ...mappingData.value, [projectName]: { ...projectMappings, [entityName]: result } }
      }
      return result
    } catch (e: any) {
      const message = getErrorMessage(e, 'Failed to load mapping sidecar')
      if (mappingRequestVersions.get(requestKey) === requestVersion) {
        mappingErrors.value = {
          ...mappingErrors.value,
          [projectName]: { ...(mappingErrors.value[projectName] ?? {}), [entityName]: message },
        }
      }
      console.error('Failed to load mapping sidecar:', e)
      throw e
    } finally {
      if (mappingRequestVersions.get(requestKey) === requestVersion) {
        mappingLoading.value = {
          ...mappingLoading.value,
          [projectName]: { ...(mappingLoading.value[projectName] ?? {}), [entityName]: false },
        }
      }
    }
  }

  async function putManualMapping(
    projectName: string,
    entityName: string,
    localKeyValue: string,
    targetId: number,
    notes?: string
  ) {
    try {
      const result = await reconciliationServiceApi.putManualMapping(projectName, entityName, localKeyValue, {
        target_id: targetId,
        notes,
      })
      try {
        await loadMappingData(projectName, entityName)
      } catch (e: unknown) {
        throw new Error(
          `Manual link was saved, but its sidecar could not be reloaded: ${getErrorMessage(e, 'request failed')}`
        )
      }
      return result
    } catch (e: any) {
      const message = getErrorMessage(e, 'Failed to save manual mapping link')
      mappingErrors.value = {
        ...mappingErrors.value,
        [projectName]: { ...(mappingErrors.value[projectName] ?? {}), [entityName]: message },
      }
      console.error('Failed to save manual mapping link:', e)
      throw e
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

  async function exportToMapping(
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<ExportToMappingResult> {
    loading.value = true
    error.value = null
    try {
      return await reconciliationServiceApi.exportToMapping(projectName, entityName, targetField)
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to export reconciliation links to mapping'
      console.error('Failed to export reconciliation links to mapping:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  function $reset() {
    reconciliationConfig.value = null
    previewData.value = {}
    previewErrors.value = {}
    mappingData.value = {}
    mappingErrors.value = {}
    mappingLoading.value = {}
    previewRequestVersions.clear()
    mappingRequestVersions.clear()
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

  async function createSpecification(projectName: string, request: EntityResolutionCatalogCreateRequest) {
    loadingSpecs.value = true
    specsError.value = null
    try {
      const updatedConfig = await reconciliationSpecApi.createSpecification(projectName, request)
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
  ): Promise<number> {
    loadingSpecs.value = true
    specsError.value = null
    try {
      const result: DeleteSpecificationResult = await reconciliationSpecApi.deleteSpecification(
        projectName,
        entityName,
        targetField,
        force
      )
      const { removed_owned_links: removedOwnedLinks, ...updatedConfig } = result
      reconciliationConfig.value = updatedConfig
      // Reload specifications list
      await loadSpecifications(projectName)
      // Clear selected spec if it was deleted
      if (selectedSpec.value?.entity_name === entityName && selectedSpec.value?.target_field === targetField) {
        selectedSpec.value = null
      }
      return removedOwnedLinks
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

  async function getMappingCount(projectName: string, entityName: string, targetField: string): Promise<number> {
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
    previewErrors,
    mappingData,
    mappingErrors,
    mappingLoading,
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
    loadMappingData,
    putManualMapping,
    checkServiceHealth,
    getServiceManifest,
    exportToMapping,
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
