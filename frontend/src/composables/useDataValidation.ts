/**
 * Composable for data validation operations
 */
import { ref, computed } from 'vue'
import axios from 'axios'
import type { ValidationResult, ValidationError } from '@/types/validation'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8012/api/v1'

// Cache for validation results with 5-minute TTL
interface CacheEntry {
  result: ValidationResult
  timestamp: number
}
const validationCache = new Map<string, CacheEntry>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

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

    const allIssues = [
      ...(result.value.errors || []),
      ...(result.value.warnings || []),
      ...(result.value.info || [])
    ]

    const grouped: Record<string, ValidationError[]> = {}
    
    allIssues.forEach(issue => {
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

    const allIssues = [
      ...(result.value.errors || []),
      ...(result.value.warnings || []),
      ...(result.value.info || [])
    ]

    const grouped: Record<string, ValidationError[]> = {}
    
    allIssues.forEach(issue => {
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

    const allIssues = [
      ...(result.value.errors || []),
      ...(result.value.warnings || [])
    ]

    return allIssues.filter(issue => issue.auto_fixable)
  })

  /**
   * Run data validation on configuration
   */
  async function validateData(
    configName: string,
    entityNames?: string[]
  ): Promise<ValidationResult | null> {
    // Check cache first
    const cacheKey = `${configName}:${entityNames?.join(',') || 'all'}`
    const cached = validationCache.get(cacheKey)
    
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      result.value = cached.result
      return cached.result
    }

    loading.value = true
    error.value = null
    result.value = null

    try {
      const params = entityNames && entityNames.length > 0
        ? { entity_names: entityNames.join(',') }
        : {}

      const response = await axios.post<ValidationResult>(
        `${API_BASE}/configurations/${configName}/validate/data`,
        null,
        { params }
      )

      result.value = response.data
      
      // Update cache
      validationCache.set(cacheKey, {
        result: response.data,
        timestamp: Date.now()
      })
      
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
  async function previewFixes(
    configName: string,
    errors: ValidationError[]
  ): Promise<any> {
    loading.value = true
    error.value = null

    try {
      const response = await axios.post(
        `${API_BASE}/configurations/${configName}/fixes/preview`,
        errors
      )

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
  async function applyFixes(
    configName: string,
    errors: ValidationError[]
  ): Promise<any> {
    loading.value = true
    error.value = null

    try {
      const response = await axios.post(
        `${API_BASE}/configurations/${configName}/fixes/apply`,
        errors
      )

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

  /**
   * Clear validation cache (useful for testing and forcing refresh)
   */
  function clearCache() {
    validationCache.clear()
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
    clearCache
  }
}
