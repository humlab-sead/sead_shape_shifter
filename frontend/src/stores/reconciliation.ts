/**
 * Pinia store for entity reconciliation state management.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ReconciliationConfig,
  EntityReconciliationSpec,
  ReconciliationCandidate,
  AutoReconcileResult,
  ReconciliationPreviewRow,
} from '@/types/reconciliation'
import { apiClient } from '@/api/client'

export const useReconciliationStore = defineStore('reconciliation', () => {
  // State
  const config = ref<ReconciliationConfig | null>(null)
  const previewData = ref<Record<string, ReconciliationPreviewRow[]>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const reconcilableEntities = computed(() => {
    if (!config.value) return []
    return Object.keys(config.value.entities)
  })

  const hasConfig = computed(() => config.value !== null)

  // Actions
  async function loadConfig(configName: string) {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get(`/configurations/${configName}/reconciliation`)
      config.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to load reconciliation config'
      console.error('Failed to load reconciliation config:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function saveConfig(configName: string) {
    if (!config.value) {
      throw new Error('No config to save')
    }

    loading.value = true
    error.value = null
    try {
      const response = await apiClient.put(`/configurations/${configName}/reconciliation`, config.value)
      config.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to save reconciliation config'
      console.error('Failed to save reconciliation config:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function autoReconcile(
    configName: string,
    entityName: string,
    threshold: number = 0.95
  ): Promise<AutoReconcileResult> {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(
        `/configurations/${configName}/reconciliation/${entityName}/auto-reconcile`,
        null,
        { params: { threshold } }
      )

      // Reload config to get updated mappings
      await loadConfig(configName)

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
    configName: string,
    entityName: string,
    sourceValues: any[],
    seadId: number | null,
    notes?: string
  ) {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(`/configurations/${configName}/reconciliation/${entityName}/mapping`, {
        source_values: sourceValues,
        sead_id: seadId,
        notes,
      })
      config.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to update mapping'
      console.error('Failed to update mapping:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteMapping(configName: string, entityName: string, sourceValues: any[]) {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.delete(`/configurations/${configName}/reconciliation/${entityName}/mapping`, {
        params: { source_values: JSON.stringify(sourceValues) },
      })
      config.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to delete mapping'
      console.error('Failed to delete mapping:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function suggestEntities(
    configName: string,
    entityName: string,
    query: string
  ): Promise<ReconciliationCandidate[]> {
    if (query.length < 2) {
      return []
    }

    try {
      const response = await apiClient.get(`/configurations/${configName}/reconciliation/${entityName}/suggest`, {
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

  function $reset() {
    config.value = null
    previewData.value = {}
    loading.value = false
    error.value = null
  }

  return {
    // State
    config,
    previewData,
    loading,
    error,

    // Getters
    reconcilableEntities,
    hasConfig,

    // Actions
    loadConfig,
    saveConfig,
    autoReconcile,
    updateMapping,
    deleteMapping,
    suggestEntities,
    clearError,
    $reset,
  }
})
