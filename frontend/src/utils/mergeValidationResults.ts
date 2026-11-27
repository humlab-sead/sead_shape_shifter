import type { ValidationResult } from '@/types'

/**
 * Combines the project, data and target model validation results into the one the panel shows.
 *
 * Messages and counts are added together. How the data run ended (mode, status, reason and
 * per-entity status) comes from the data result, so a run that did not complete is not
 * shown as passed.
 */
export function mergeValidationResults(
  structural: ValidationResult | null,
  data: ValidationResult | null,
  conformance: ValidationResult | null
): ValidationResult | null {
  const results = [structural, data, conformance].filter((result): result is ValidationResult => result !== null)

  if (results.length === 0) return null
  if (results.length === 1) return results[0]!

  return {
    is_valid: results.every((result) => result.is_valid),
    errors: results.flatMap((result) => result.errors),
    warnings: results.flatMap((result) => result.warnings),
    info: results.flatMap((result) => result.info || []),
    error_count: results.reduce((sum, result) => sum + result.error_count, 0),
    warning_count: results.reduce((sum, result) => sum + result.warning_count, 0),
    validation_mode: data?.validation_mode,
    status: data?.status,
    status_reason: data?.status_reason,
    entity_statuses: data?.entity_statuses,
  }
}
