/**
 * Unit tests for validation type utilities
 */
import { describe, it, expect } from 'vitest'
import {
  getErrorCount,
  getWarningCount,
  getTotalIssues,
  getErrorsForEntity,
  getWarningsForEntity,
  groupByEntity,
  groupBySeverity,
  type ValidationResult,
  type ValidationError,
} from '../validation'

describe('validation utilities', () => {
  const createMockResult = (
    errors: ValidationError[] = [],
    warnings: ValidationError[] = [],
    info: ValidationError[] = []
  ): ValidationResult => ({
    is_valid: errors.length === 0,
    errors,
    warnings,
    info,
    error_count: errors.length,
    warning_count: warnings.length,
  })

  const createMockError = (overrides: Partial<ValidationError> = {}): ValidationError => ({
    severity: 'error',
    entity: null,
    field: null,
    message: 'Test error',
    code: null,
    suggestion: null,
    category: 'structural',
    priority: 'medium',
    auto_fixable: false,
    ...overrides,
  })

  describe('getErrorCount', () => {
    it('should return 0 for result with no errors', () => {
      const result = createMockResult()
      expect(getErrorCount(result)).toBe(0)
    })

    it('should return correct count for result with errors', () => {
      const errors = [createMockError(), createMockError(), createMockError()]
      const result = createMockResult(errors)
      expect(getErrorCount(result)).toBe(3)
    })

    it('should only count errors, not warnings', () => {
      const errors = [createMockError()]
      const warnings = [createMockError({ severity: 'warning' }), createMockError({ severity: 'warning' })]
      const result = createMockResult(errors, warnings)
      expect(getErrorCount(result)).toBe(1)
    })
  })

  describe('getWarningCount', () => {
    it('should return 0 for result with no warnings', () => {
      const result = createMockResult()
      expect(getWarningCount(result)).toBe(0)
    })

    it('should return correct count for result with warnings', () => {
      const warnings = [createMockError({ severity: 'warning' }), createMockError({ severity: 'warning' })]
      const result = createMockResult([], warnings)
      expect(getWarningCount(result)).toBe(2)
    })

    it('should only count warnings, not errors', () => {
      const errors = [createMockError(), createMockError()]
      const warnings = [createMockError({ severity: 'warning' })]
      const result = createMockResult(errors, warnings)
      expect(getWarningCount(result)).toBe(1)
    })
  })

  describe('getTotalIssues', () => {
    it('should return 0 for result with no issues', () => {
      const result = createMockResult()
      expect(getTotalIssues(result)).toBe(0)
    })

    it('should sum errors and warnings', () => {
      const errors = [createMockError(), createMockError()]
      const warnings = [
        createMockError({ severity: 'warning' }),
        createMockError({ severity: 'warning' }),
        createMockError({ severity: 'warning' }),
      ]
      const result = createMockResult(errors, warnings)
      expect(getTotalIssues(result)).toBe(5)
    })

    it('should not count info messages', () => {
      const errors = [createMockError()]
      const warnings = [createMockError({ severity: 'warning' })]
      const info = [createMockError({ severity: 'info' }), createMockError({ severity: 'info' })]
      const result = createMockResult(errors, warnings, info)
      expect(getTotalIssues(result)).toBe(2)
    })
  })

  describe('getErrorsForEntity', () => {
    it('should return empty array when entity has no errors', () => {
      const errors = [createMockError({ entity: 'entity1' })]
      const result = createMockResult(errors)
      expect(getErrorsForEntity(result, 'entity2')).toEqual([])
    })

    it('should return only errors for specified entity', () => {
      const errors = [
        createMockError({ entity: 'entity1', message: 'Error 1' }),
        createMockError({ entity: 'entity2', message: 'Error 2' }),
        createMockError({ entity: 'entity1', message: 'Error 3' }),
        createMockError({ entity: 'entity3', message: 'Error 4' }),
      ]
      const result = createMockResult(errors)
      const entity1Errors = getErrorsForEntity(result, 'entity1')

      expect(entity1Errors).toHaveLength(2)
      expect(entity1Errors[0]?.message).toBe('Error 1')
      expect(entity1Errors[1]?.message).toBe('Error 3')
    })

    it('should handle errors with null entity', () => {
      const errors = [
        createMockError({ entity: 'entity1', message: 'Error 1' }),
        createMockError({ entity: null, message: 'Error 2' }),
      ]
      const result = createMockResult(errors)
      expect(getErrorsForEntity(result, 'entity1')).toHaveLength(1)
    })

    it('should handle empty error list', () => {
      const result = createMockResult()
      expect(getErrorsForEntity(result, 'entity1')).toEqual([])
    })
  })

  describe('getWarningsForEntity', () => {
    it('should return empty array when entity has no warnings', () => {
      const warnings = [createMockError({ entity: 'entity1', severity: 'warning' })]
      const result = createMockResult([], warnings)
      expect(getWarningsForEntity(result, 'entity2')).toEqual([])
    })

    it('should return only warnings for specified entity', () => {
      const warnings = [
        createMockError({ entity: 'entity1', message: 'Warning 1', severity: 'warning' }),
        createMockError({ entity: 'entity2', message: 'Warning 2', severity: 'warning' }),
        createMockError({ entity: 'entity1', message: 'Warning 3', severity: 'warning' }),
      ]
      const result = createMockResult([], warnings)
      const entity1Warnings = getWarningsForEntity(result, 'entity1')

      expect(entity1Warnings).toHaveLength(2)
      expect(entity1Warnings[0]?.message).toBe('Warning 1')
      expect(entity1Warnings[1]?.message).toBe('Warning 3')
    })

    it('should handle warnings with null entity', () => {
      const warnings = [
        createMockError({ entity: 'entity1', severity: 'warning' }),
        createMockError({ entity: null, severity: 'warning' }),
      ]
      const result = createMockResult([], warnings)
      expect(getWarningsForEntity(result, 'entity1')).toHaveLength(1)
    })
  })

  describe('groupByEntity', () => {
    it('should return empty map for empty error list', () => {
      const grouped = groupByEntity([])
      expect(grouped.size).toBe(0)
    })

    it('should group errors by entity name', () => {
      const errors = [
        createMockError({ entity: 'entity1', message: 'Error 1' }),
        createMockError({ entity: 'entity2', message: 'Error 2' }),
        createMockError({ entity: 'entity1', message: 'Error 3' }),
        createMockError({ entity: 'entity3', message: 'Error 4' }),
      ]
      const grouped = groupByEntity(errors)

      expect(grouped.size).toBe(3)
      expect(grouped.get('entity1')).toHaveLength(2)
      expect(grouped.get('entity2')).toHaveLength(1)
      expect(grouped.get('entity3')).toHaveLength(1)
    })

    it('should use "general" key for errors without entity', () => {
      const errors = [
        createMockError({ entity: null, message: 'General error 1' }),
        createMockError({ entity: null, message: 'General error 2' }),
        createMockError({ entity: 'entity1', message: 'Entity error' }),
      ]
      const grouped = groupByEntity(errors)

      expect(grouped.size).toBe(2)
      expect(grouped.get('general')).toHaveLength(2)
      expect(grouped.get('entity1')).toHaveLength(1)
    })

    it('should preserve error details in grouped results', () => {
      const errors = [
        createMockError({
          entity: 'entity1',
          message: 'Error 1',
          code: 'E001',
          priority: 'high',
        }),
      ]
      const grouped = groupByEntity(errors)
      const entity1Errors = grouped.get('entity1')!

      expect(entity1Errors[0]).toMatchObject({
        entity: 'entity1',
        message: 'Error 1',
        code: 'E001',
        priority: 'high',
      })
    })

    it('should handle mix of entities and general errors', () => {
      const errors = [
        createMockError({ entity: 'entity1', message: 'E1' }),
        createMockError({ entity: null, message: 'G1' }),
        createMockError({ entity: 'entity2', message: 'E2' }),
        createMockError({ entity: null, message: 'G2' }),
        createMockError({ entity: 'entity1', message: 'E3' }),
      ]
      const grouped = groupByEntity(errors)

      expect(grouped.size).toBe(3)
      expect(grouped.get('entity1')).toHaveLength(2)
      expect(grouped.get('entity2')).toHaveLength(1)
      expect(grouped.get('general')).toHaveLength(2)
    })
  })

  describe('groupBySeverity', () => {
    it('should return empty arrays for all severities when result has no issues', () => {
      const result = createMockResult()
      const grouped = groupBySeverity(result)

      expect(grouped.error).toEqual([])
      expect(grouped.warning).toEqual([])
      expect(grouped.info).toEqual([])
    })

    it('should group errors by severity', () => {
      const errors = [
        createMockError({ severity: 'error', message: 'Error 1' }),
        createMockError({ severity: 'error', message: 'Error 2' }),
      ]
      const warnings = [createMockError({ severity: 'warning', message: 'Warning 1' })]
      const info = [createMockError({ severity: 'info', message: 'Info 1' })]
      const result = createMockResult(errors, warnings, info)
      const grouped = groupBySeverity(result)

      expect(grouped.error).toHaveLength(2)
      expect(grouped.warning).toHaveLength(1)
      expect(grouped.info).toHaveLength(1)
    })

    it('should preserve error details in grouped results', () => {
      const errors = [
        createMockError({
          severity: 'error',
          message: 'Critical error',
          priority: 'critical',
          auto_fixable: true,
        }),
      ]
      const result = createMockResult(errors)
      const grouped = groupBySeverity(result)

      expect(grouped.error[0]).toMatchObject({
        severity: 'error',
        message: 'Critical error',
        priority: 'critical',
        auto_fixable: true,
      })
    })

    it('should handle result with only errors', () => {
      const errors = [createMockError(), createMockError()]
      const result = createMockResult(errors)
      const grouped = groupBySeverity(result)

      expect(grouped.error).toHaveLength(2)
      expect(grouped.warning).toEqual([])
      expect(grouped.info).toEqual([])
    })

    it('should handle result with only warnings', () => {
      const warnings = [createMockError({ severity: 'warning' }), createMockError({ severity: 'warning' })]
      const result = createMockResult([], warnings)
      const grouped = groupBySeverity(result)

      expect(grouped.error).toEqual([])
      expect(grouped.warning).toHaveLength(2)
      expect(grouped.info).toEqual([])
    })

    it('should handle result with all severity types', () => {
      const errors = [createMockError({ message: 'E1' })]
      const warnings = [
        createMockError({ severity: 'warning', message: 'W1' }),
        createMockError({ severity: 'warning', message: 'W2' }),
      ]
      const info = [
        createMockError({ severity: 'info', message: 'I1' }),
        createMockError({ severity: 'info', message: 'I2' }),
        createMockError({ severity: 'info', message: 'I3' }),
      ]
      const result = createMockResult(errors, warnings, info)
      const grouped = groupBySeverity(result)

      expect(grouped.error).toHaveLength(1)
      expect(grouped.warning).toHaveLength(2)
      expect(grouped.info).toHaveLength(3)
    })
  })
})
