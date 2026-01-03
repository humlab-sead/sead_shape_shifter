/**
 * Pinia store for entity reconciliation state management.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ReconciliationConfig,
  ReconciliationCandidate,
  AutoReconcileResult,
  ReconciliationPreviewRow,
} from '@/types/reconciliation'
import { apiClient } from '@/api/client'
// import { load } from 'js-yaml'

export const useReconciliationStore = defineStore('reconciliation', () => {
  // State
  const reconciliationConfig = ref<ReconciliationConfig | null>(null)
  const previewData = ref<Record<string, ReconciliationPreviewRow[]>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const reconcilableEntities = computed(() => {
    if (!reconciliationConfig.value) return []
    return Object.keys(reconciliationConfig.value.entities).filter(
      (entityName) => {
        const entity = reconciliationConfig.value!.entities[entityName]
        return entity?.remote?.service_type != null
      }
    )
  })

  const hasConfig = computed(() => reconciliationConfig.value !== null)

  // Actions
  async function loadReconciliationConfig(projectName: string) {
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

  async function saveReconciliationConfig(projectName: string) {
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

  async function autoReconcile(
    projectName: string,
    entityName: string,
    threshold: number = 0.95,
    reviewThreshold?: number
  ): Promise<AutoReconcileResult> {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(
        `/projects/${projectName}/reconciliation/${entityName}/auto-reconcile`,
        null,
        { params: { threshold, review_threshold: reviewThreshold } }
      )

      // Reload config to get updated mappings
      await loadReconciliationConfig(projectName)

      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Auto-reconciliation failed'
      console.error('Auto-reconciliation failed:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateMapping(
    projectName: string,
    entityName: string,
    sourceValues: any[],
    seadId: number | null,
    notes?: string
  ) {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(`/projects/${projectName}/reconciliation/${entityName}/mapping`, {
        source_values: sourceValues,
        sead_id: seadId,
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

  async function deleteMapping(projectName: string, entityName: string, sourceValues: any[]) {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.delete(`/projects/${projectName}/reconciliation/${entityName}/mapping`, {
        params: { source_values: JSON.stringify(sourceValues) },
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
    query: string
  ): Promise<ReconciliationCandidate[]> {
    if (query.length < 2) {
      return []
    }

    try {
      const response = await apiClient.get(`/projects/${projectName}/reconciliation/${entityName}/suggest`, {
        params: { query },
      })
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to get suggestions'
      console.error('Failed to get entity suggestions:', e)
      return []
    }
  }

  function clearError() {
    error.value = null
  }

  async function checkServiceHealth() {
    try {
      const response = await apiClient.get('/reconciliation/health')
      return response.data
    } catch (e: any) {
      console.error('Failed to check reconciliation service health:', e)
      throw e
    }
  }

  function $reset() {
    reconciliationConfig.value = null
    previewData.value = {}
    loading.value = false
    error.value = null
  }

  return {
    // State
    reconciliationConfig,
    previewData,
    loading,
    error,

    // Getters
    reconcilableEntities,
    hasConfig,

    // Actions
    loadReconciliationConfig,
    saveReconciliationConfig,
    autoReconcile,
    updateMapping,
    deleteMapping,
    suggestEntities,
    checkServiceHealth,
    clearError,
    $reset,
  }
})
