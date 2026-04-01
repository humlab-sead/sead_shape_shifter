/**
 * TypeScript types for validation.
 */

export type ValidationSeverity = 'error' | 'warning' | 'info'
export type ValidationCategory = 'structural' | 'data' | 'performance' | 'conformance'
export type ValidationPriority = 'low' | 'medium' | 'high' | 'critical'
export type DataValidationMode = 'sample' | 'complete'

export interface ValidationError {
  severity: ValidationSeverity
  entity?: string | null
  branch_name?: string | null
  branch_source?: string | null
  field?: string | null
  message: string
  code?: string | null
  suggestion?: string | null
  category?: ValidationCategory
  priority?: ValidationPriority
  auto_fixable?: boolean
}

export interface ValidationBranchGroup {
  key: string
  branchName: string | null
  branchSource: string | null
  messages: ValidationError[]
}

export interface ValidationEntityGroup {
  key: string
  entity: string | null
  messages: ValidationError[]
  entityMessages: ValidationError[]
  branchGroups: ValidationBranchGroup[]
}

export interface ValidationResult {
  is_valid: boolean
  errors: ValidationError[]
  warnings: ValidationError[]
  info: ValidationError[]
  error_count: number
  warning_count: number
  validation_mode?: DataValidationMode | null
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

export function groupByEntityScope(messages: ValidationError[]): ValidationEntityGroup[] {
  const entityGroups = new Map<string, ValidationEntityGroup>()

  for (const message of messages) {
    const entityKey = message.entity || 'general'
    if (!entityGroups.has(entityKey)) {
      entityGroups.set(entityKey, {
        key: entityKey,
        entity: message.entity || null,
        messages: [],
        entityMessages: [],
        branchGroups: [],
      })
    }

    const entityGroup = entityGroups.get(entityKey)!
    entityGroup.messages.push(message)

    if (!message.branch_name && !message.branch_source) {
      entityGroup.entityMessages.push(message)
      continue
    }

    const branchKey = `${message.branch_name || ''}::${message.branch_source || ''}`
    let branchGroup = entityGroup.branchGroups.find((group) => group.key === branchKey)
    if (!branchGroup) {
      branchGroup = {
        key: branchKey,
        branchName: message.branch_name || null,
        branchSource: message.branch_source || null,
        messages: [],
      }
      entityGroup.branchGroups.push(branchGroup)
    }

    branchGroup.messages.push(message)
  }

  return Array.from(entityGroups.values()).sort((left, right) => {
    if (left.entity === null) return -1
    if (right.entity === null) return 1
    return left.key.localeCompare(right.key)
  })
}

export function groupBySeverity(result: ValidationResult): Record<ValidationSeverity, ValidationError[]> {
  return {
    error: result.errors,
    warning: result.warnings,
    info: result.info,
  }
}
