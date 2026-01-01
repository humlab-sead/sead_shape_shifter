/**
 * Unit tests for validation API service
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { validationApi } from '../validation'
import type { ValidationResult, DependencyGraph, CircularDependencyCheck } from '@/types'

// Mock the API client
vi.mock('../client', () => ({
  apiRequest: vi.fn(),
}))

import { apiRequest } from '../client'

describe('validationApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('validateEntity', () => {
    it('should validate a specific entity successfully', async () => {
      const mockValidation: ValidationResult = {
        is_valid: true,
        errors: [],
        warnings: [],
        info: [],
        error_count: 0,
        warning_count: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockValidation)

      const result = await validationApi.validateEntity('test-project', 'test-entity')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/entities/test-entity/validate',
      })
      expect(result).toEqual(mockValidation)
      expect(result.is_valid).toBe(true)
    })

    it('should return validation errors for entity', async () => {
      const mockValidation: ValidationResult = {
        is_valid: false,
        errors: [
          {
            severity: 'error',
            entity: 'test-entity',
            field: 'field1',
            message: 'Field is required',
            code: 'REQUIRED_FIELD',
          },
          {
            severity: 'error',
            entity: 'test-entity',
            field: 'field2',
            message: 'Invalid data type',
            code: 'INVALID_TYPE',
          },
        ],
        warnings: [],
        info: [],
        error_count: 2,
        warning_count: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockValidation)

      const result = await validationApi.validateEntity('test-project', 'test-entity')

      expect(result.is_valid).toBe(false)
      expect(result.errors).toHaveLength(2)
      expect(result.error_count).toBe(2)
    })

    it('should return validation warnings', async () => {
      const mockValidation: ValidationResult = {
        is_valid: true,
        errors: [],
        warnings: [
          {
            severity: 'warning',
            entity: 'test-entity',
            message: 'Deprecated field usage',
            code: 'DEPRECATED',
            suggestion: 'Use new_field instead',
          },
        ],
        info: [],
        error_count: 0,
        warning_count: 1,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockValidation)

      const result = await validationApi.validateEntity('test-project', 'test-entity')

      expect(result.is_valid).toBe(true)
      expect(result.warnings).toHaveLength(1)
      expect(result.warnings[0]?.suggestion).toBe('Use new_field instead')
    })

    it('should handle entity with special characters in name', async () => {
      const mockValidation: ValidationResult = {
        is_valid: true,
        errors: [],
        warnings: [],
        info: [],
        error_count: 0,
        warning_count: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockValidation)

      await validationApi.validateEntity('test-project', 'entity_with_underscore')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/entities/entity_with_underscore/validate',
      })
    })

    it('should handle validation with auto-fixable errors', async () => {
      const mockValidation: ValidationResult = {
        is_valid: false,
        errors: [
          {
            severity: 'error',
            entity: 'test-entity',
            message: 'Missing foreign key',
            code: 'MISSING_FK',
            auto_fixable: true,
            suggestion: 'Add foreign_key field',
          },
        ],
        warnings: [],
        info: [],
        error_count: 1,
        warning_count: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockValidation)

      const result = await validationApi.validateEntity('test-project', 'test-entity')

      expect(result.errors[0]?.auto_fixable).toBe(true)
      expect(result.errors[0]?.suggestion).toBeDefined()
    })
  })

  describe('getDependencies', () => {
    it('should fetch dependency graph successfully', async () => {
      const mockGraph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: [], depth: 0 },
          { name: 'entity2', depends_on: ['entity1'], depth: 1 },
          { name: 'entity3', depends_on: ['entity1', 'entity2'], depth: 2 },
        ],
        edges: [
          ['entity1', 'entity2'],
          ['entity1', 'entity3'],
          ['entity2', 'entity3'],
        ],
        has_cycles: false,
        cycles: [],
        topological_order: ['entity1', 'entity2', 'entity3'],
      }

      vi.mocked(apiRequest).mockResolvedValue(mockGraph)

      const result = await validationApi.getDependencies('test-project')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects/test-project/dependencies',
      })
      expect(result).toEqual(mockGraph)
      expect(result.nodes).toHaveLength(3)
      expect(result.edges).toHaveLength(3)
    })

    it('should handle empty dependency graph', async () => {
      const mockGraph: DependencyGraph = {
        nodes: [],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: [],
      }

      vi.mocked(apiRequest).mockResolvedValue(mockGraph)

      const result = await validationApi.getDependencies('empty-project')

      expect(result.nodes).toHaveLength(0)
      expect(result.edges).toHaveLength(0)
    })

    it('should handle dependency graph with cycles', async () => {
      const mockGraph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: ['entity2'], depth: 0 },
          { name: 'entity2', depends_on: ['entity1'], depth: 1 },
        ],
        edges: [
          ['entity1', 'entity2'],
          ['entity2', 'entity1'],
        ],
        has_cycles: true,
        cycles: [['entity1', 'entity2']],
        topological_order: null,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockGraph)

      const result = await validationApi.getDependencies('test-project')

      expect(result.has_cycles).toBe(true)
      expect(result.cycles).toHaveLength(1)
      expect(result.topological_order).toBeNull()
    })

    it('should handle complex dependency graph', async () => {
      const mockGraph: DependencyGraph = {
        nodes: [
          { name: 'A', depends_on: [], depth: 0 },
          { name: 'B', depends_on: ['A'], depth: 1 },
          { name: 'C', depends_on: ['A'], depth: 1 },
          { name: 'D', depends_on: ['B', 'C'], depth: 2 },
          { name: 'E', depends_on: ['D'], depth: 3 },
        ],
        edges: [
          ['A', 'B'],
          ['A', 'C'],
          ['B', 'D'],
          ['C', 'D'],
          ['D', 'E'],
        ],
        has_cycles: false,
        cycles: [],
        topological_order: ['A', 'B', 'C', 'D', 'E'],
      }

      vi.mocked(apiRequest).mockResolvedValue(mockGraph)

      const result = await validationApi.getDependencies('complex-project')

      expect(result.nodes).toHaveLength(5)
      expect(result.edges).toHaveLength(5)
      expect(result.topological_order).toEqual(['A', 'B', 'C', 'D', 'E'])
    })

    it('should handle entities with no dependencies', async () => {
      const mockGraph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: [], depth: 0 },
          { name: 'entity2', depends_on: [], depth: 0 },
          { name: 'entity3', depends_on: [], depth: 0 },
        ],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: ['entity1', 'entity2', 'entity3'],
      }

      vi.mocked(apiRequest).mockResolvedValue(mockGraph)

      const result = await validationApi.getDependencies('test-project')

      expect(result.edges).toHaveLength(0)
      expect(result.nodes.every((node) => node.depends_on.length === 0)).toBe(true)
    })
  })

  describe('checkCircularDependencies', () => {
    it('should return no cycles when dependencies are valid', async () => {
      const mockCheck: CircularDependencyCheck = {
        has_cycles: false,
        cycles: [],
        cycle_count: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockCheck)

      const result = await validationApi.checkCircularDependencies('test-project')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/dependencies/check',
      })
      expect(result.has_cycles).toBe(false)
      expect(result.cycle_count).toBe(0)
      expect(result.cycles).toHaveLength(0)
    })

    it('should detect simple circular dependency', async () => {
      const mockCheck: CircularDependencyCheck = {
        has_cycles: true,
        cycles: [['entity1', 'entity2']],
        cycle_count: 1,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockCheck)

      const result = await validationApi.checkCircularDependencies('test-project')

      expect(result.has_cycles).toBe(true)
      expect(result.cycle_count).toBe(1)
      expect(result.cycles).toHaveLength(1)
      expect(result.cycles[0]).toEqual(['entity1', 'entity2'])
    })

    it('should detect multiple circular dependencies', async () => {
      const mockCheck: CircularDependencyCheck = {
        has_cycles: true,
        cycles: [
          ['entity1', 'entity2'],
          ['entity3', 'entity4', 'entity5'],
        ],
        cycle_count: 2,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockCheck)

      const result = await validationApi.checkCircularDependencies('test-project')

      expect(result.has_cycles).toBe(true)
      expect(result.cycle_count).toBe(2)
      expect(result.cycles).toHaveLength(2)
    })

    it('should detect complex circular dependency chain', async () => {
      const mockCheck: CircularDependencyCheck = {
        has_cycles: true,
        cycles: [['A', 'B', 'C', 'D']],
        cycle_count: 1,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockCheck)

      const result = await validationApi.checkCircularDependencies('test-project')

      expect(result.has_cycles).toBe(true)
      expect(result.cycles[0]).toHaveLength(4)
    })

    it('should handle self-referencing entity', async () => {
      const mockCheck: CircularDependencyCheck = {
        has_cycles: true,
        cycles: [['entity1']],
        cycle_count: 1,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockCheck)

      const result = await validationApi.checkCircularDependencies('test-project')

      expect(result.has_cycles).toBe(true)
      expect(result.cycles[0]).toEqual(['entity1'])
    })
  })

  describe('error handling', () => {
    it('should propagate API errors for validateEntity', async () => {
      const error = new Error('Entity not found')
      vi.mocked(apiRequest).mockRejectedValue(error)

      await expect(validationApi.validateEntity('test-project', 'nonexistent')).rejects.toThrow('Entity not found')
    })

    it('should propagate API errors for getDependencies', async () => {
      const error = new Error('Project not found')
      vi.mocked(apiRequest).mockRejectedValue(error)

      await expect(validationApi.getDependencies('nonexistent')).rejects.toThrow('Project not found')
    })

    it('should propagate API errors for checkCircularDependencies', async () => {
      const error = new Error('Validation failed')
      vi.mocked(apiRequest).mockRejectedValue(error)

      await expect(validationApi.checkCircularDependencies('test-project')).rejects.toThrow('Validation failed')
    })
  })
})
