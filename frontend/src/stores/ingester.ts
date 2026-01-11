/**
 * Pinia store for ingester state management
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ingesterApi } from '@/api/ingester'
import type {
  IngesterMetadata,
  ValidateRequest,
  ValidateResponse,
  IngestRequest,
  IngestResponse
} from '@/types/ingester'

export const useIngesterStore = defineStore('ingester', () => {
  // State
  const ingesters = ref<IngesterMetadata[]>([])
  const selectedIngester = ref<IngesterMetadata | null>(null)
  const validationResult = ref<ValidateResponse | null>(null)
  const ingestionResult = ref<IngestResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const hasIngesters = computed(() => ingesters.value.length > 0)
  const isValidating = computed(() => loading.value)
  const isIngesting = computed(() => loading.value)

  // Actions
  async function fetchIngesters() {
    loading.value = true
    error.value = null
    try {
      ingesters.value = await ingesterApi.listIngesters()
      // Auto-select first ingester if available
      if (ingesters.value.length > 0 && !selectedIngester.value) {
        selectedIngester.value = ingesters.value[0]
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch ingesters'
      console.error('Error fetching ingesters:', e)
    } finally {
      loading.value = false
    }
  }

  async function validate(request: ValidateRequest) {
    if (!selectedIngester.value) {
      error.value = 'No ingester selected'
      return
    }

    loading.value = true
    error.value = null
    validationResult.value = null

    try {
      validationResult.value = await ingesterApi.validate(
        selectedIngester.value.key,
        request
      )
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Validation failed'
      console.error('Validation error:', e)
    } finally {
      loading.value = false
    }
  }

  async function ingest(request: IngestRequest) {
    if (!selectedIngester.value) {
      error.value = 'No ingester selected'
      return
    }

    loading.value = true
    error.value = null
    ingestionResult.value = null

    try {
      ingestionResult.value = await ingesterApi.ingest(
        selectedIngester.value.key,
        request
      )
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Ingestion failed'
      console.error('Ingestion error:', e)
    } finally {
      loading.value = false
    }
  }

  function selectIngester(key: string) {
    selectedIngester.value = ingesters.value.find(i => i.key === key) || null
  }

  function clearValidation() {
    validationResult.value = null
  }

  function clearIngestion() {
    ingestionResult.value = null
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    ingesters,
    selectedIngester,
    validationResult,
    ingestionResult,
    loading,
    error,

    // Computed
    hasIngesters,
    isValidating,
    isIngesting,

    // Actions
    fetchIngesters,
    validate,
    ingest,
    selectIngester,
    clearValidation,
    clearIngestion,
    clearError
  }
})
