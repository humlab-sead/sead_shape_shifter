/**
 * Tests for enhanced structured error parsing
 * Validates support for backend domain exception format
 */

import { describe, it, expect } from 'vitest'
import { formatErrorMessage, parseStructuredError } from '../errors'

describe('Enhanced Error Parsing', () => {
  describe('formatErrorMessage', () => {
    it('should parse structured domain exception', () => {
      const axiosError = {
        isAxiosError: true,
        response: {
          data: {
            error_type: 'ForeignKeyError',
            message: "Entity 'site' has invalid foreign_keys: must be a list",
            tips: [
              "Change foreign_keys to a list: foreign_keys: [...]",
              "Each foreign key should be a separate list item",
              "Check YAML syntax - use '- entity: ...' for list items",
            ],
            context: {
              entity: 'site',
              field: 'foreign_keys',
            },
            recoverable: true,
          },
        },
      }

      const result = formatErrorMessage(axiosError)

      expect(result.message).toBe("Entity 'site' has invalid foreign_keys: must be a list")
      expect(result.errorType).toBe('ForeignKeyError')
      expect(result.tips).toHaveLength(3)
      expect(result.tips![0]).toContain('Change foreign_keys to a list')
      expect(result.context).toEqual({ entity: 'site', field: 'foreign_keys' })
      expect(result.recoverable).toBe(true)
    })

    it('should parse CircularDependencyError with cycle info', () => {
      const axiosError = {
        isAxiosError: true,
        response: {
          data: {
            error_type: 'CircularDependencyError',
            message: 'Circular dependency detected involving 3 entities\n\nDetected cycle: A → B → C → A',
            tips: [
              'Review entity dependencies and remove circular references',
              'Check foreign_keys, source, and depends_on fields',
              'Use GET /api/v1/projects/{name}/dependencies to visualize',
            ],
            context: {
              cycle: ['A', 'B', 'C', 'A'],
              cycle_length: 4,
            },
            recoverable: false,
          },
        },
      }

      const result = formatErrorMessage(axiosError)

      expect(result.message).toContain('Circular dependency detected')
      expect(result.errorType).toBe('CircularDependencyError')
      expect(result.tips).toHaveLength(3)
      expect(result.context?.cycle).toEqual(['A', 'B', 'C', 'A'])
      expect(result.recoverable).toBe(false)
    })

    it('should handle legacy string detail format with tips keyword', () => {
      const axiosError = {
        isAxiosError: true,
        response: {
          data: {
            detail: 'Project not found\n\nTip: Check project name spelling',
          },
        },
      }

      const result = formatErrorMessage(axiosError)

      expect(result.message).toBe('Project not found')
      // Legacy logic treats lines with "Tip:" or "Check" as tips
      expect(result.tips).toBeDefined()
      expect(result.tips!.some((tip) => tip.includes('Check project name spelling'))).toBe(true)
    })

    it('should handle legacy string detail format without keywords', () => {
      const axiosError = {
        isAxiosError: true,
        response: {
          data: {
            detail: 'Project not found\n\nPlease try again later',
          },
        },
      }

      const result = formatErrorMessage(axiosError)

      expect(result.message).toBe('Project not found')
      expect(result.detail).toBe('Please try again later')
    })

    it('should handle plain error objects', () => {
      const error = new Error('Network connection failed')

      const result = formatErrorMessage(error)

      expect(result.message).toBe('Network connection failed')
      expect(result.tips).toBeUndefined()
    })

    it('should handle string errors', () => {
      const result = formatErrorMessage('Something went wrong')

      expect(result.message).toBe('Something went wrong')
    })
  })

  describe('parseStructuredError', () => {
    it('should extract structured error from axios response', () => {
      const axiosError = {
        response: {
          data: {
            error_type: 'MissingDependencyError',
            message: "Entity 'site' references non-existent entity 'location'",
            tips: ['Check entity spelling', 'Ensure entity is defined'],
            context: {
              entity: 'site',
              missing_entity: 'location',
            },
            recoverable: true,
          },
        },
      }

      const result = parseStructuredError(axiosError)

      expect(result).not.toBeNull()
      expect(result!.error_type).toBe('MissingDependencyError')
      expect(result!.message).toContain('non-existent entity')
      expect(result!.recoverable).toBe(true)
    })

    it('should return null for non-structured errors', () => {
      const axiosError = {
        response: {
          data: {
            detail: 'Simple error message',
          },
        },
      }

      const result = parseStructuredError(axiosError)

      expect(result).toBeNull()
    })

    it('should return null for non-axios errors', () => {
      const error = new Error('Regular error')

      const result = parseStructuredError(error)

      expect(result).toBeNull()
    })
  })

  describe('Backward Compatibility', () => {
    it('should handle errors with both old and new formats', () => {
      const axiosError = {
        isAxiosError: true,
        response: {
          data: {
            // Structured format takes priority
            error_type: 'ValidationError',
            message: 'Structured message',
            tips: ['Structured tip'],
            recoverable: true,
            // Legacy format (should be ignored)
            detail: 'Legacy detail message',
          },
        },
      }

      const result = formatErrorMessage(axiosError)

      // Should use structured format
      expect(result.message).toBe('Structured message')
      expect(result.errorType).toBe('ValidationError')
      expect(result.tips).toEqual(['Structured tip'])
    })

    it('should fall back to detail when structured format incomplete', () => {
      const axiosError = {
        isAxiosError: true,
        response: {
          data: {
            detail: 'Only detail available',
          },
        },
      }

      const result = formatErrorMessage(axiosError)

      expect(result.message).toBe('Only detail available')
      expect(result.errorType).toBeUndefined()
    })
  })
})
