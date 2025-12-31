/**
 * Composable for testing foreign key joins
 */
import { ref, computed } from 'vue'
import { apiClient } from '@/api/client'

export interface JoinStatistics {
  total_rows: number
  matched_rows: number
  unmatched_rows: number
  match_percentage: number
  null_key_rows: number
  duplicate_matches: number
}

export interface CardinalityInfo {
  expected: string
  actual: string
  matches: boolean
  explanation: string
}

export interface UnmatchedRow {
  row_data: Record<string, any>
  local_key_values: any[]
  reason: string
}

export interface JoinTestResult {
  entity_name: string
  remote_entity: string
  local_keys: string[]
  remote_keys: string[]
  join_type: string
  statistics: JoinStatistics
  cardinality: CardinalityInfo
  unmatched_sample: UnmatchedRow[]
  execution_time_ms: number
  success: boolean
  warnings: string[]
  recommendations: string[]
}

export function useForeignKeyTester() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const testResult = ref<JoinTestResult | null>(null)

  /**
   * Test a foreign key join
   */
  const testForeignKey = async (
    configName: string,
    entityName: string,
    fkIndex: number,
    sampleSize: number = 100
  ): Promise<JoinTestResult | null> => {
    loading.value = true
    error.value = null
    testResult.value = null

    try {
      const response = await apiClient.post<JoinTestResult>(
        `/configurations/${encodeURIComponent(configName)}/entities/${encodeURIComponent(entityName)}/foreign-keys/${fkIndex}/test`,
        null,
        {
          params: { sample_size: sampleSize },
        }
      )

      testResult.value = response.data
      return response.data
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to test foreign key'
      error.value = message
      console.error('Foreign key test error:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear test result
   */
  const clearResult = () => {
    testResult.value = null
    error.value = null
  }

  /**
   * Check if test passed
   */
  const testPassed = computed(() => {
    return testResult.value?.success === true
  })

  /**
   * Get match percentage color
   */
  const matchPercentageColor = computed(() => {
    if (!testResult.value) return 'grey'
    const percentage = testResult.value.statistics.match_percentage
    if (percentage >= 95) return 'success'
    if (percentage >= 80) return 'warning'
    return 'error'
  })

  /**
   * Get cardinality status color
   */
  const cardinalityStatusColor = computed(() => {
    if (!testResult.value) return 'grey'
    return testResult.value.cardinality.matches ? 'success' : 'warning'
  })

  /**
   * Check if there are warnings
   */
  const hasWarnings = computed(() => {
    return testResult.value && testResult.value.warnings.length > 0
  })

  /**
   * Check if there are recommendations
   */
  const hasRecommendations = computed(() => {
    return testResult.value && testResult.value.recommendations.length > 0
  })

  /**
   * Format match percentage as string
   */
  const matchPercentageText = computed(() => {
    if (!testResult.value) return 'N/A'
    return `${testResult.value.statistics.match_percentage.toFixed(1)}%`
  })

  return {
    // State
    loading,
    error,
    testResult,

    // Actions
    testForeignKey,
    clearResult,

    // Computed
    testPassed,
    matchPercentageColor,
    cardinalityStatusColor,
    hasWarnings,
    hasRecommendations,
    matchPercentageText,
  }
}
