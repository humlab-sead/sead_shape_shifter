import { onScopeDispose, ref } from 'vue'
import { validationApi } from '@/api/validation'
import type { DraftEntityValidationRequest, ValidationResult } from '@/types'

const REQUEST_DEBOUNCE_MS = 300

export interface DraftEntityValidationContext {
  projectName: string
  entityName: string
  entityDraft: Record<string, unknown>
  originalEntityName?: string
}

function cloneEntityDraft(entityDraft: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(entityDraft)) as Record<string, unknown>
}

function getContextKey(context: DraftEntityValidationContext): string {
  return JSON.stringify([
    context.projectName,
    context.entityName,
    context.originalEntityName ?? null,
    context.entityDraft,
  ])
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Could not read validation for the current draft.'
}

export function useDraftEntityValidation() {
  const result = ref<ValidationResult | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)
  let currentKey: string | null = null
  let requestedKey: string | null = null
  let requestVersion = 0
  let requestTimer: ReturnType<typeof setTimeout> | null = null

  function cancelPendingRequest(): void {
    requestVersion += 1
    if (requestTimer !== null) {
      clearTimeout(requestTimer)
      requestTimer = null
    }
    requestedKey = null
    loading.value = false
  }

  function setContext(context: DraftEntityValidationContext | null): void {
    const nextKey = context ? getContextKey(context) : null
    if (nextKey === currentKey) return

    cancelPendingRequest()
    currentKey = nextKey
    result.value = null
    error.value = null
  }

  function validateDraft(context: DraftEntityValidationContext | null): void {
    if (!context?.projectName || !context.entityName) {
      setContext(null)
      return
    }

    const key = getContextKey(context)
    setContext(context)
    if (requestedKey === key) return

    const version = ++requestVersion
    requestedKey = key
    result.value = null
    error.value = null
    loading.value = true

    const request: DraftEntityValidationRequest = {
      entity_draft: cloneEntityDraft(context.entityDraft),
      ...(context.originalEntityName ? { original_entity_name: context.originalEntityName } : {}),
    }

    requestTimer = setTimeout(() => {
      requestTimer = null
      void validationApi
        .validateEntityDraft(context.projectName, context.entityName, request)
        .then((validationResult) => {
          if (version === requestVersion && currentKey === key) {
            result.value = validationResult
          }
        })
        .catch((requestError: unknown) => {
          if (version === requestVersion && currentKey === key) {
            error.value = getErrorMessage(requestError)
            requestedKey = null
          }
        })
        .finally(() => {
          if (version === requestVersion && currentKey === key) {
            loading.value = false
          }
        })
    }, REQUEST_DEBOUNCE_MS)
  }

  function invalidate(): void {
    setContext(null)
  }

  onScopeDispose(invalidate)

  return { result, error, loading, setContext, validateDraft, invalidate }
}
