/**
 * Composable for target-model conformance validation
 */
import { ref, computed } from 'vue'
import { apiClient } from '@/api/client'
import type { ValidationResult } from '@/types/validation'

export function useConformanceValidation() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const result = ref<ValidationResult | null>(null)

  const hasErrors = computed(() => (result.value?.error_count ?? 0) > 0)
  const hasWarnings = computed(() => (result.value?.warning_count ?? 0) > 0)
  const isValid = computed(() => result.value?.is_valid ?? true)

  /**
   * Run target-model conformance validation on a project
   */
  async function validateConformance(projectName: string): Promise<ValidationResult | null> {
    loading.value = true
    error.value = null
    result.value = null

    try {
      const response = await apiClient.post<ValidationResult>(`/projects/${projectName}/validate/target-model`)
      result.value = response.data
      return response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Conformance validation failed'
      console.error('Conformance validation error:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  function clearResults() {
    result.value = null
    error.value = null
  }

  return {
    loading,
    error,
    result,
    hasErrors,
    hasWarnings,
    isValid,
    validateConformance,
    clearResults,
  }
}
