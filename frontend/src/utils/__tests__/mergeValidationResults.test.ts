import { describe, expect, it } from 'vitest'
import { mergeValidationResults } from '../mergeValidationResults'
import type { ValidationResult } from '@/types'

function result(overrides: Partial<ValidationResult> = {}): ValidationResult {
  return { is_valid: true, errors: [], warnings: [], info: [], error_count: 0, warning_count: 0, ...overrides }
}

const failedDataRun = result({
  is_valid: false,
  validation_mode: 'complete',
  status: 'failed',
  status_reason: "Entity 'feature_type' has 19 invalid typed value(s) during coercion",
  entity_statuses: { feature_type: { status: 'failed', reason: 'invalid values' } },
})

describe('mergeValidationResults', () => {
  it('returns null when nothing has run', () => {
    expect(mergeValidationResults(null, null, null)).toBeNull()
  })

  it('keeps how the data run ended when it is combined with other results', () => {
    const merged = mergeValidationResults(result(), failedDataRun, result())

    expect(merged).toMatchObject({
      is_valid: false,
      validation_mode: 'complete',
      status: 'failed',
      status_reason: failedDataRun.status_reason,
      entity_statuses: failedDataRun.entity_statuses,
    })
  })

  it('adds up the messages and counts of all results', () => {
    const message = { severity: 'error' as const, message: 'broken' }
    const merged = mergeValidationResults(result({ errors: [message], error_count: 1 }), result(), null)

    expect(merged!.error_count).toBe(1)
    expect(merged!.errors).toEqual([message])
  })

  it('has no run status when data validation has not run', () => {
    const merged = mergeValidationResults(result(), null, result())

    expect(merged!.status).toBeUndefined()
  })
})
