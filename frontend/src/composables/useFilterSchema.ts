/**
 * Composable for managing filter schemas.
 * 
 * Provides access to filter metadata for dynamic form generation.
 * Schemas are loaded once and cached for the session.
 */

import { ref } from 'vue'
import type { FilterSchema } from '@/types/filter-schema'
import { apiClient } from '@/api/client'

const filterSchemas = ref<Record<string, FilterSchema>>({})
const loading = ref(false)
const error = ref<string | null>(null)

export function useFilterSchema() {
  /**
   * Load all filter schemas from the API.
   * Results are cached - subsequent calls return immediately.
   */
  async function loadFilterSchemas() {
    if (Object.keys(filterSchemas.value).length > 0) {
      return // Already loaded
    }

    loading.value = true
    error.value = null

    try {
      const response = await apiClient.get<Record<string, FilterSchema>>('/filters/types')
      filterSchemas.value = response.data
    } catch (e: any) {
      error.value = e.message || 'Failed to load filter schemas'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Get schema for a specific filter type.
   * 
   * @param key - Filter identifier (e.g., 'query', 'exists_in')
   * @returns Filter schema or undefined if not found
   */
  function getFilterSchema(key: string): FilterSchema | undefined {
    return filterSchemas.value[key]
  }

  /**
   * Get all available filter schemas.
   * 
   * @returns Array of all filter schemas
   */
  function getAllFilterSchemas(): FilterSchema[] {
    return Object.values(filterSchemas.value)
  }

  /**
   * Get filter types formatted for v-select.
   * 
   * @returns Array of {title, value} objects for dropdown
   */
  function getFilterTypes(): Array<{ title: string; value: string }> {
    return Object.values(filterSchemas.value).map((schema) => ({
      title: schema.display_name,
      value: schema.key,
    }))
  }

  return {
    filterSchemas,
    loading,
    error,
    loadFilterSchemas,
    getFilterSchema,
    getAllFilterSchemas,
    getFilterTypes,
  }
}
