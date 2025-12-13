import { ref } from 'vue'
import { api } from '../api/client'

export interface ForeignKeySuggestion {
  remote_entity: string
  local_keys: string[]
  remote_keys: string[]
  confidence: number
  reason: string
  cardinality?: string
}

export interface DependencySuggestion {
  entity: string
  reason: string
  confidence: number
}

export interface EntitySuggestions {
  entity_name: string
  foreign_key_suggestions: ForeignKeySuggestion[]
  dependency_suggestions: DependencySuggestion[]
}

export interface AnalyzeSuggestionsRequest {
  entities: Array<{
    name: string
    columns: string[]
  }>
  data_source_name?: string
}

export function useSuggestions() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function analyzeSuggestions(
    request: AnalyzeSuggestionsRequest
  ): Promise<EntitySuggestions[]> {
    loading.value = true
    error.value = null

    try {
      const response = await api.post<EntitySuggestions[]>(
        '/suggestions/analyze',
        request
      )
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to analyze suggestions'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getSuggestionsForEntity(
    entity: { name: string; columns: string[] },
    allEntities: Array<{ name: string; columns: string[] }>,
    dataSourceName?: string
  ): Promise<EntitySuggestions> {
    loading.value = true
    error.value = null

    try {
      const response = await api.post<EntitySuggestions>('/suggestions/entity', {
        entity,
        all_entities: allEntities,
        data_source_name: dataSourceName,
      })
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to get suggestions'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    analyzeSuggestions,
    getSuggestionsForEntity,
  }
}
