import { onScopeDispose, ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { entitiesApi } from '@/api/entities'
import type { ColumnAvailabilityRequest, ColumnAvailabilityResponse } from '@/api/entities'

const REQUEST_DEBOUNCE_MS = 300

export function useColumnAvailability() {
  const availability = ref<ColumnAvailabilityResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let requestVersion = 0

  const fetchAvailability = async (
    version: number,
    projectName: string,
    entityName: string,
    request: ColumnAvailabilityRequest
  ): Promise<void> => {
    if (version !== requestVersion) return

    try {
      const result = await entitiesApi.getColumnAvailability(projectName, entityName, request)
      if (version === requestVersion) {
        availability.value = result
      }
    } catch (caughtError) {
      if (version === requestVersion) {
        error.value = caughtError instanceof Error ? caughtError.message : 'Failed to fetch column availability'
      }
    } finally {
      if (version === requestVersion) {
        loading.value = false
      }
    }
  }

  const debouncedFetch = useDebounceFn(fetchAvailability, REQUEST_DEBOUNCE_MS)

  function refresh(projectName: string, entityName: string, request: ColumnAvailabilityRequest): void {
    const version = ++requestVersion
    availability.value = null
    error.value = null

    if (!projectName || !entityName) {
      loading.value = false
      return
    }

    loading.value = true
    void debouncedFetch(version, projectName, entityName, request)
  }

  onScopeDispose(() => {
    requestVersion += 1
  })

  return { availability, loading, error, refresh }
}
