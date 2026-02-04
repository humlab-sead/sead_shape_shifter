export interface FormattedError {
  message: string
  detail?: string
  errorType?: string
  tips?: string[]
  context?: Record<string, unknown>
  recoverable?: boolean
}

/**
 * Props subset that can be bound directly onto the ErrorAlert component.
 * Kept as a standalone type so it can be imported without relying on SFC exports.
 */
export interface ErrorAlertBindProps {
  message: string
  details?: string
  tips?: string[]
  errorType?: string
  context?: Record<string, unknown>
  recoverable?: boolean
}

/**
 * Create ErrorAlert bind props from a FormattedError object.
 *
 * Usage:
 *   import { fromFormattedError } from '@/components/common/errorAlert'
 *   <ErrorAlert v-bind="fromFormattedError(error)" />
 */
export function fromFormattedError(error: FormattedError): ErrorAlertBindProps {
  return {
    message: error.message,
    details: error.detail,
    tips: error.tips,
    errorType: error.errorType,
    context: error.context,
    recoverable: error.recoverable,
  }
}
