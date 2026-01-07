import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DispatcherMetadata, ExecuteRequest, ExecuteResult } from '@/api/execute'
import { executeApi } from '@/api/execute'

export const useExecuteStore = defineStore('execute', () => {
  // State
  const dispatchers = ref<DispatcherMetadata[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastResult = ref<ExecuteResult | null>(null)

  // Actions
  async function fetchDispatchers() {
    loading.value = true
    error.value = null
    try {
      dispatchers.value = await executeApi.getDispatchers()
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to fetch dispatchers'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function executeWorkflow(projectName: string, request: ExecuteRequest): Promise<ExecuteResult> {
    loading.value = true
    error.value = null
    try {
      const result = await executeApi.executeWorkflow(projectName, request)
      lastResult.value = result
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to execute workflow'
      throw e
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearLastResult() {
    lastResult.value = null
  }

  return {
    // State
    dispatchers,
    loading,
    error,
    lastResult,
    
    // Actions
    fetchDispatchers,
    executeWorkflow,
    clearError,
    clearLastResult
  }
})
