/**
 * Utility for extracting and formatting user-friendly error messages from API errors
 * Supports both legacy string errors and structured domain exceptions from backend
 */

import type { AxiosError } from 'axios'
import type { StructuredError, FormattedError } from '@/types'

/**
 * Type guard to check if error response is a structured error
 */
function isStructuredError(data: any): data is StructuredError {
  return (
    data &&
    typeof data === 'object' &&
    'error_type' in data &&
    'message' in data &&
    'recoverable' in data
  )
}

/**
 * Extract error details from various error response structures
 * Priority: structured errors > legacy string errors > fallback
 */
function extractErrorDetails(error: any): FormattedError {
  // Default values
  let message = 'An unexpected error occurred'
  let detail: string | undefined
  let errorType: string | undefined
  let tips: string[] | undefined
  let context: Record<string, any> | undefined
  let recoverable: boolean | undefined

  // Try to extract from Axios error response
  if (error.response?.data) {
    const data = error.response.data

    // **Priority 1: Structured domain exception format**
    if (isStructuredError(data)) {
      return {
        message: data.message,
        errorType: data.error_type,
        tips: data.tips,
        context: data.context,
        recoverable: data.recoverable,
      }
    }

    // **Priority 2: Legacy FastAPI HTTPException format with detail string**
    if (typeof data.detail === 'string') {
      const fullDetail = data.detail

      // Split by newlines to separate main error from tips
      const lines = fullDetail.split('\n\n')
      message = lines[0]

      // Extract tips if present (legacy format)
      if (lines.length > 1) {
        const tipsSection = lines.slice(1).join('\n\n')
        if (tipsSection.includes('Tip:') || tipsSection.includes('Check') || tipsSection.includes('•')) {
          tips = tipsSection
            .split('\n')
            .map((line: string) => line.trim())
            .filter((line: string) => line && line !== 'Tip:')
        } else {
          detail = tipsSection
        }
      }
    }

    // **Priority 3: Alternative legacy formats**
    if (data.error_type && !errorType) {
      errorType = data.error_type
    }
    if (data.message && typeof data.message === 'string' && !detail) {
      detail = data.message
    }
    if (data.error && typeof data.error === 'string' && !detail) {
      detail = data.error
    }
  }

  // Fallback to error message
  if (message === 'An unexpected error occurred') {
    message = error.message || 'An unexpected error occurred'
  }

  return {
    message,
    detail,
    errorType,
    tips,
    context,
    recoverable,
  }
}

/**
 * Format error for user display
 */
export function formatErrorMessage(error: unknown): FormattedError {
  // Handle Axios errors
  if (error && typeof error === 'object' && 'isAxiosError' in error) {
    const axiosError = error as AxiosError
    return extractErrorDetails(axiosError)
  }

  // Handle regular Error objects
  if (error instanceof Error) {
    return {
      message: error.message,
    }
  }

  // Handle string errors
  if (typeof error === 'string') {
    return {
      message: error,
    }
  }

  // Unknown error type
  return {
    message: 'An unexpected error occurred',
    detail: String(error),
  }
}

/**
 * Parse structured error from API response
 * Returns structured error if available, otherwise null
 */
export function parseStructuredError(error: unknown): StructuredError | null {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as AxiosError
    if (axiosError.response?.data && isStructuredError(axiosError.response.data)) {
      return axiosError.response.data
    }
  }
  return null
}

/**
 * Get a single line error message (for snackbars, etc.)
 */
export function getErrorMessage(error: unknown): string {
  const formatted = formatErrorMessage(error)
  return formatted.message
}

/**
 * Check if error is a specific HTTP status code
 */
export function isHttpError(error: unknown, statusCode: number): boolean {
  if (error && typeof error === 'object' && 'isAxiosError' in error) {
    const axiosError = error as AxiosError
    return axiosError.response?.status === statusCode
  }
  return false
}

/**
 * Check if error is a validation error (400)
 */
export function isValidationError(error: unknown): boolean {
  return isHttpError(error, 400)
}

/**
 * Check if error is a not found error (404)
 */
export function isNotFoundError(error: unknown): boolean {
  return isHttpError(error, 404)
}

/**
 * Check if error is a server error (500)
 */
export function isServerError(error: unknown): boolean {
  return isHttpError(error, 500)
}
