/**
 * Composable for entity data preview functionality
 */
import { ref, computed } from 'vue'
import axios from 'axios'

export interface ColumnInfo {
  name: string
  data_type: string
  nullable: boolean
  is_key: boolean
}

export interface PreviewResult {
  entity_name: string
  rows: Record<string, any>[]
  columns: ColumnInfo[]
  total_rows_in_preview: number
  estimated_total_rows: number | null
  execution_time_ms: number
  has_dependencies: boolean
  dependencies_loaded: string[]
  transformations_applied: string[]
  cache_hit: boolean
}

export function useEntityPreview() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const previewData = ref<PreviewResult | null>(null)

  const hasData = computed(() => previewData.value !== null)
  const rowCount = computed(() => previewData.value?.total_rows_in_preview ?? 0)
  const totalRows = computed(() => previewData.value?.estimated_total_rows ?? 0)

  /**
   * Preview entity data with transformations
   */
  async function previewEntity(
    configName: string,
    entityName: string,
    limit: number = 50
  ): Promise<PreviewResult | null> {
    if (!configName || !entityName) {
      error.value = 'Configuration and entity name are required'
      return null
    }

    loading.value = true
    error.value = null

    try {
      const response = await axios.post<PreviewResult>(
        `/api/v1/configurations/${configName}/entities/${entityName}/preview`,
        {},
        { params: { limit } }
      )

      previewData.value = response.data
      return response.data
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to load preview'
      error.value = message
      console.error('Preview error:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get entity sample (larger dataset)
   */
  async function getEntitySample(
    configName: string,
    entityName: string,
    limit: number = 100
  ): Promise<PreviewResult | null> {
    if (!configName || !entityName) {
      error.value = 'Configuration and entity name are required'
      return null
    }

    loading.value = true
    error.value = null

    try {
      const response = await axios.post<PreviewResult>(
        `/api/v1/configurations/${configName}/entities/${entityName}/sample`,
        {},
        { params: { limit } }
      )

      previewData.value = response.data
      return response.data
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to load sample'
      error.value = message
      console.error('Sample error:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Invalidate preview cache for entity
   */
  async function invalidateCache(
    configName: string,
    entityName?: string
  ): Promise<boolean> {
    try {
      const params = entityName ? { entity_name: entityName } : {}
      await axios.delete(
        `/api/v1/configurations/${configName}/preview-cache`,
        { params }
      )
      return true
    } catch (err: any) {
      console.error('Cache invalidation error:', err)
      return false
    }
  }

  /**
   * Clear preview data and error
   */
  function clearPreview() {
    previewData.value = null
    error.value = null
  }

  /**
   * Clear error only
   */
  function clearError() {
    error.value = null
  }

  return {
    // State
    loading,
    error,
    previewData,
    hasData,
    rowCount,
    totalRows,

    // Actions
    previewEntity,
    getEntitySample,
    invalidateCache,
    clearPreview,
    clearError,
  }
}
