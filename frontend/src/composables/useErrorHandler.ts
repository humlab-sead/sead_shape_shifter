/**
 * Composable for consistent error handling across components.
 *
 * Provides reactive error state and methods to handle errors from API calls,
 * converting them to FormattedError objects for display with ErrorAlert.
 *
 * Usage:
 * ```ts
 * const { error, errorProps, handleError, clearError } = useErrorHandler()
 *
 * async function fetchData() {
 *   try {
 *     await api.getData()
 *   } catch (e) {
 *     handleError(e)
 *   }
 * }
 * ```
 *
 * In template:
 * ```vue
 * <ErrorAlert v-if="error" v-bind="errorProps" @close="clearError" closable />
 * ```
 */

import { ref, computed } from 'vue'
import type { Ref } from 'vue'
import type { FormattedError } from '@/types'
import { formatErrorMessage } from '@/utils/errors'

export interface UseErrorHandlerOptions {
  /** Default action text for recoverable errors */
  defaultActionText?: string
  /** Whether to show tips by default */
  showTips?: boolean
  /** Whether to show context by default */
  showContext?: boolean
  /** Callback when error is set */
  onError?: (error: FormattedError) => void
  /** Callback when error is cleared */
  onClear?: () => void
}

export interface UseErrorHandlerReturn {
  /** The current error state */
  error: Ref<FormattedError | null>
  /** Whether there is an error */
  hasError: Ref<boolean>
  /** Props to spread on ErrorAlert component */
  errorProps: Ref<Record<string, any>>
  /** Handle an error (converts and sets error state) */
  handleError: (e: unknown, overrides?: Partial<FormattedError>) => void
  /** Clear the current error */
  clearError: () => void
  /** Set error directly from a FormattedError */
  setError: (error: FormattedError) => void
  /** Wrap an async function with error handling */
  withErrorHandling: <T>(fn: () => Promise<T>) => Promise<T | undefined>
}

/**
 * Composable for consistent error handling
 */
export function useErrorHandler(options: UseErrorHandlerOptions = {}): UseErrorHandlerReturn {
  const {
    defaultActionText,
    showTips = true,
    showContext = false,
    onError,
    onClear,
  } = options

  // State
  const error = ref<FormattedError | null>(null)

  // Computed
  const hasError = computed(() => error.value !== null)

  const errorProps = computed(() => {
    if (!error.value) return {}

    return {
      message: error.value.message,
      details: error.value.detail,
      tips: error.value.tips,
      errorType: error.value.errorType,
      context: error.value.context,
      recoverable: error.value.recoverable,
      actionText: error.value.recoverable !== false ? defaultActionText : undefined,
      showTips,
      showContext,
    }
  })

  // Methods
  function handleError(e: unknown, overrides: Partial<FormattedError> = {}): void {
    const formatted = formatErrorMessage(e)
    const merged: FormattedError = {
      ...formatted,
      ...overrides,
    }
    error.value = merged

    if (onError) {
      onError(merged)
    }
  }

  function clearError(): void {
    error.value = null
    if (onClear) {
      onClear()
    }
  }

  function setError(err: FormattedError): void {
    error.value = err
    if (onError) {
      onError(err)
    }
  }

  /**
   * Wrap an async function with automatic error handling
   * Returns undefined if an error occurred
   */
  async function withErrorHandling<T>(fn: () => Promise<T>): Promise<T | undefined> {
    clearError()
    try {
      return await fn()
    } catch (e) {
      handleError(e)
      return undefined
    }
  }

  return {
    error,
    hasError,
    errorProps,
    handleError,
    clearError,
    setError,
    withErrorHandling,
  }
}

/**
 * Simple error state for components that just need a string error
 * Use useErrorHandler for full structured error support
 */
export function useSimpleError() {
  const error = ref<string | null>(null)

  function handleError(e: unknown): void {
    const formatted = formatErrorMessage(e)
    error.value = formatted.message
  }

  function clearError(): void {
    error.value = null
  }

  return {
    error,
    hasError: computed(() => error.value !== null),
    handleError,
    clearError,
  }
}
