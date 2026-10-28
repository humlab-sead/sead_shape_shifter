/**
 * Utility for extracting and formatting user-friendly error messages from API errors
 * Supports both legacy string errors and structured domain exceptions from backend
 */

import type { AxiosError } from 'axios'
import type { StructuredError, FormattedError } from '@/types'

function normalizeForeignKeyLanguage(text: string | undefined): string | undefined {
  if (!text) {
    return text
  }

  return text
    .replace(/Allow (?:Null Keys|Missing Join Keys)/gi, 'Allow Missing Join Keys')
    .replace(/null values found in/gi, 'missing values found in')
    .replace(/null keys/gi, 'missing join keys')
    .replace(/null key/gi, 'missing join key')
}

/**
 * Type guard to check if error response is a structured error
 */
function isStructuredError(data: unknown): data is StructuredError {
  return (
    data !== null &&
    typeof data === 'object' &&
    'error_type' in data &&
    typeof data.error_type === 'string' &&
    'message' in data &&
    typeof data.message === 'string' &&
    'recoverable' in data &&
    typeof data.recoverable === 'boolean'
  )
}

function getStructuredError(data: unknown): StructuredError | null {
  if (isStructuredError(data)) {
    return data
  }

  if (data !== null && typeof data === 'object' && 'detail' in data && isStructuredError(data.detail)) {
    return data.detail
  }

  return null
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
    const structuredData = getStructuredError(data)
    if (structuredData) {
      return {
        message: normalizeForeignKeyLanguage(structuredData.message) ?? structuredData.message,
        errorType: structuredData.error_type,
        tips: structuredData.tips?.map((tip) => normalizeForeignKeyLanguage(tip) ?? tip),
        context: structuredData.context,
        recoverable: structuredData.recoverable,
      }
    }

    // **Priority 2: Legacy FastAPI HTTPException format with detail string**
    if (typeof data.detail === 'string') {
      const fullDetail = data.detail

      // Split by newlines to separate main error from tips
      const lines = fullDetail.split('\n\n')
      message = normalizeForeignKeyLanguage(lines[0]) ?? lines[0]

      // Extract tips if present (legacy format)
      if (lines.length > 1) {
        const tipsSection = lines.slice(1).join('\n\n')
        if (tipsSection.includes('Tip:') || tipsSection.includes('Check') || tipsSection.includes('•')) {
          tips = tipsSection
            .split('\n')
            .map((line: string) => line.trim())
            .filter((line: string) => line && line !== 'Tip:')
            .map((line: string) => normalizeForeignKeyLanguage(line) ?? line)
        } else {
          detail = normalizeForeignKeyLanguage(tipsSection)
        }
      }
    }

    // **Priority 3: Alternative legacy formats**
    if (data.error_type && !errorType) {
      errorType = data.error_type
    }
    if (data.message && typeof data.message === 'string' && !detail) {
      detail = normalizeForeignKeyLanguage(data.message)
    }
    if (data.error && typeof data.error === 'string' && !detail) {
      detail = normalizeForeignKeyLanguage(data.error)
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
      message: normalizeForeignKeyLanguage(error.message) ?? error.message,
    }
  }

  // Handle string errors
  if (typeof error === 'string') {
    return {
      message: normalizeForeignKeyLanguage(error) ?? error,
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
    return getStructuredError(axiosError.response?.data)
  }
  return null
}

/**
 * Get a single-line error message and the first actionable tip, when available.
 */
export function getErrorMessage(error: unknown): string {
  const formatted = formatErrorMessage(error)
  const firstTip = formatted.tips?.[0]
  return firstTip ? `${formatted.message} — ${firstTip}` : formatted.message
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
