/**
 * Composable for data validation operations
 */
import { ref, computed } from 'vue'
import { apiClient } from '@/api/client'
import type { ValidationResult, ValidationError } from '@/types/validation'

export function useDataValidation() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const result = ref<ValidationResult | null>(null)

  const hasErrors = computed(() => result.value?.error_count ?? 0 > 0)
  const hasWarnings = computed(() => result.value?.warning_count ?? 0 > 0)
  const isValid = computed(() => result.value?.is_valid ?? true)

  // Group issues by category
  const issuesByCategory = computed(() => {
    if (!result.value) return {}

    const allIssues = [...(result.value.errors || []), ...(result.value.warnings || []), ...(result.value.info || [])]

    const grouped: Record<string, ValidationError[]> = {}

    allIssues.forEach((issue) => {
      const category = issue.category || 'structural'
      if (!grouped[category]) {
        grouped[category] = []
      }
      grouped[category].push(issue)
    })

    return grouped
  })

  // Group issues by priority
  const issuesByPriority = computed(() => {
    if (!result.value) return {}

    const allIssues = [...(result.value.errors || []), ...(result.value.warnings || []), ...(result.value.info || [])]

    const grouped: Record<string, ValidationError[]> = {}

    allIssues.forEach((issue) => {
      const priority = issue.priority || 'medium'
      if (!grouped[priority]) {
        grouped[priority] = []
      }
      grouped[priority].push(issue)
    })

    return grouped
  })

  // Get auto-fixable issues
  const autoFixableIssues = computed(() => {
    if (!result.value) return []

    const allIssues = [...(result.value.errors || []), ...(result.value.warnings || [])]

    return allIssues.filter((issue) => issue.auto_fixable)
  })

  /**
   * Run data validation on project
   */
  async function validateData(
    projectName: string,
    entityNames?: string[],
    validationMode: 'sample' | 'complete' = 'sample'
  ): Promise<ValidationResult | null> {
    loading.value = true
    error.value = null
    result.value = null

    try {
      const params: Record<string, string> = { validation_mode: validationMode }
      if (entityNames && entityNames.length > 0) {
        params.entity_names = entityNames.join(',')
      }

      const response = await apiClient.post<ValidationResult>(`/projects/${projectName}/validate/data`, null, {
        params,
      })

      result.value = response.data

      return response.data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Data validation failed'
      error.value = message
      console.error('Data validation error:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear validation results
   */
  function clearResults() {
    result.value = null
    error.value = null
  }

  /**
   * Preview fixes for validation errors
   */
  async function previewFixes(projectName: string, errors: ValidationError[]): Promise<any> {
    loading.value = true
    error.value = null

    try {
      const response = await apiClient.post(`/projects/${projectName}/fixes/preview`, errors)

      return response.data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to preview fixes'
      error.value = message
      console.error('Preview fixes error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Apply fixes for validation errors
   */
  async function applyFixes(projectName: string, errors: ValidationError[]): Promise<any> {
    loading.value = true
    error.value = null

    try {
      const response = await apiClient.post(`/projects/${projectName}/fixes/apply`, errors)

      return response.data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to apply fixes'
      error.value = message
      console.error('Apply fixes error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    loading,
    error,
    result,

    // Computed
    hasErrors,
    hasWarnings,
    isValid,
    issuesByCategory,
    issuesByPriority,
    autoFixableIssues,

    // Methods
    validateData,
    clearResults,
    previewFixes,
    applyFixes,
  }
}
