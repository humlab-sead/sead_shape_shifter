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
  IngestResponse,
  ProjectIngesterRequest,
} from '@/types/ingester'

export const useIngesterStore = defineStore('ingester', () => {
  // State
  const ingesters = ref<IngesterMetadata[]>([])
  const selectedIngester = ref<IngesterMetadata | null>(null)
  const validationResult = ref<ValidateResponse | null>(null)
  const ingestionResult = ref<IngestResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let projectAttemptKey: string | null = null
  let projectAttemptRunId: string | null = null

  // Computed
  const hasIngesters = computed(() => ingesters.value.length > 0)
  const isValidating = computed(() => loading.value)
  const isIngesting = computed(() => loading.value)

  function projectRequestForAttempt(request: ProjectIngesterRequest): { request: ProjectIngesterRequest; runId: string } {
    const context = request.submission_context
    const normalizedSubmissionName = context.submission_name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
    const attemptKey = JSON.stringify([
      normalizedSubmissionName,
      request.project_name.trim(),
      context.timestamp.trim(),
      context.datatype.trim().toLowerCase(),
      context.identifier.trim().toUpperCase(),
    ])

    if (attemptKey !== projectAttemptKey || !projectAttemptRunId) {
      projectAttemptKey = attemptKey
      projectAttemptRunId = globalThis.crypto.randomUUID()
    }

    return {
      request: {
        ...request,
        submission_context: {
          ...context,
          run_id: projectAttemptRunId,
        },
      },
      runId: projectAttemptRunId,
    }
  }

  function resetProjectAttempt() {
    projectAttemptKey = null
    projectAttemptRunId = null
  }

  // Actions
  async function fetchIngesters() {
    loading.value = true
    error.value = null
    try {
      ingesters.value = await ingesterApi.listIngesters()
      // Auto-select first ingester if available
      if (ingesters.value.length > 0 && !selectedIngester.value) {
        const firstIngester = ingesters.value[0] ?? null
        selectedIngester.value = firstIngester
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
      validationResult.value = await ingesterApi.validate(selectedIngester.value.key, request)
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
      ingestionResult.value = await ingesterApi.ingest(selectedIngester.value.key, request)
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Ingestion failed'
      console.error('Ingestion error:', e)
    } finally {
      loading.value = false
    }
  }

  async function validateProject(request: ProjectIngesterRequest) {
    if (selectedIngester.value?.key !== 'sead_change_request') {
      error.value = selectedIngester.value ? 'SEAD Change Request must be selected' : 'No ingester selected'
      return
    }

    const projectRequest = projectRequestForAttempt(request).request
    loading.value = true
    error.value = null
    validationResult.value = null

    try {
      validationResult.value = await ingesterApi.validateProject(projectRequest)
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Validation failed'
      console.error('Validation error:', e)
    } finally {
      loading.value = false
    }
  }

  async function ingestProject(request: ProjectIngesterRequest) {
    if (selectedIngester.value?.key !== 'sead_change_request') {
      error.value = selectedIngester.value ? 'SEAD Change Request must be selected' : 'No ingester selected'
      return
    }

    const attempt = projectRequestForAttempt(request)
    loading.value = true
    error.value = null
    ingestionResult.value = null

    try {
      ingestionResult.value = await ingesterApi.ingestProject(attempt.request)
      if (ingestionResult.value.success && projectAttemptRunId === attempt.runId) {
        resetProjectAttempt()
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Ingestion failed'
      console.error('Ingestion error:', e)
    } finally {
      loading.value = false
    }
  }

  function selectIngester(key: string) {
    selectedIngester.value = ingesters.value.find((i) => i.key === key) ?? null
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
    validateProject,
    ingestProject,
    resetProjectAttempt,
    selectIngester,
    clearValidation,
    clearIngestion,
    clearError,
  }
})
