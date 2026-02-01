/**
 * Composable for fetching available columns for FK editing.
 */
import { ref } from 'vue'
import { apiClient } from '@/api/client'

export interface ColumnAvailability {
  explicit: string[]
  keys: string[]
  extra: string[]
  unnested: string[]
  foreign_key: string[]
  system: string[]
  directives: string[]
}

export interface AvailableColumnsResponse {
  local_columns: ColumnAvailability
  remote_columns?: ColumnAvailability
}

export function useColumnIntrospection() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch available columns for FK editing.
   */
  async function getAvailableColumns(
    projectName: string,
    entityName: string,
    remoteEntity?: string
  ): Promise<AvailableColumnsResponse | null> {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      if (remoteEntity) {
        params.append('remote_entity', remoteEntity)
      }

      const url = `/projects/${projectName}/entities/${entityName}/columns${
        params.toString() ? '?' + params.toString() : ''
      }`

      const response = await apiClient.get<AvailableColumnsResponse>(url)
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to fetch available columns'
      console.error('Error fetching available columns:', e)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Flatten ColumnAvailability into a single categorized list.
   */
  function flattenColumns(availability: ColumnAvailability): Array<{ value: string; category: string }> {
    const result: Array<{ value: string; category: string }> = []

    // Add categories in priority order
    availability.keys.forEach((col) => result.push({ value: col, category: 'Keys' }))
    availability.explicit.forEach((col) => result.push({ value: col, category: 'Explicit' }))
    availability.extra.forEach((col) => result.push({ value: col, category: 'Extra' }))
    availability.unnested.forEach((col) => result.push({ value: col, category: 'Unnested' }))
    availability.foreign_key.forEach((col) => result.push({ value: col, category: 'Foreign Key' }))
    availability.system.forEach((col) => result.push({ value: col, category: 'System' }))
    availability.directives.forEach((col) => result.push({ value: col, category: 'Directives' }))

    return result
  }

  return {
    loading,
    error,
    getAvailableColumns,
    flattenColumns,
  }
}
