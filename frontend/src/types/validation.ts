/**
 * TypeScript types for validation.
 */

export type ValidationSeverity = 'error' | 'warning' | 'info'
export type ValidationCategory = 'structural' | 'data' | 'performance'
export type ValidationPriority = 'low' | 'medium' | 'high' | 'critical'

export interface ValidationError {
  severity: ValidationSeverity
  entity?: string | null
  field?: string | null
  message: string
  code?: string | null
  suggestion?: string | null
  category?: ValidationCategory
  priority?: ValidationPriority
  auto_fixable?: boolean
}

export interface ValidationResult {
  is_valid: boolean
  errors: ValidationError[]
  warnings: ValidationError[]
  info: ValidationError[]
  error_count: number
  warning_count: number
}

// Helper functions
export function getErrorCount(result: ValidationResult): number {
  return result.errors.length
}

export function getWarningCount(result: ValidationResult): number {
  return result.warnings.length
}

export function getTotalIssues(result: ValidationResult): number {
  return result.errors.length + result.warnings.length
}

export function getErrorsForEntity(result: ValidationResult, entityName: string): ValidationError[] {
  return result.errors.filter((e) => e.entity === entityName)
}

export function getWarningsForEntity(result: ValidationResult, entityName: string): ValidationError[] {
  return result.warnings.filter((e) => e.entity === entityName)
}

export function groupByEntity(errors: ValidationError[]): Map<string, ValidationError[]> {
  const grouped = new Map<string, ValidationError[]>()
  for (const error of errors) {
    const key = error.entity || 'general'
    if (!grouped.has(key)) {
      grouped.set(key, [])
    }
    grouped.get(key)!.push(error)
  }
  return grouped
}

export function groupBySeverity(
  result: ValidationResult
): Record<ValidationSeverity, ValidationError[]> {
  return {
    error: result.errors,
    warning: result.warnings,
    info: result.info,
  }
}
