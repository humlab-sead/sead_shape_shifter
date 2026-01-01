import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useValidationStore } from '../validation'
import type { ValidationResult, ValidationError, DependencyGraph, CircularDependencyCheck } from '@/types'

// Mock the API module
vi.mock('@/api', () => ({
  api: {
    projects: {
      validate: vi.fn(),
    },
    validation: {
      validateEntity: vi.fn(),
      getDependencies: vi.fn(),
      checkCircularDependencies: vi.fn(),
    },
  },
}))

import { api } from '@/api'

describe('useValidationStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should initialize with empty state', () => {
      const store = useValidationStore()

      expect(store.validationResult).toBeNull()
      expect(store.entityValidationResults).toBeInstanceOf(Map)
      expect(store.entityValidationResults.size).toBe(0)
      expect(store.dependencyGraph).toBeNull()
      expect(store.circularDependencyCheck).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('computed getters', () => {
    it('should detect errors', () => {
      const store = useValidationStore()

      expect(store.hasErrors).toBe(false)

      store.validationResult = { error_count: 1 } as ValidationResult
      expect(store.hasErrors).toBe(true)

      store.validationResult = { error_count: 0 } as ValidationResult
      expect(store.hasErrors).toBe(false)
    })

    it('should detect warnings', () => {
      const store = useValidationStore()

      expect(store.hasWarnings).toBe(false)

      store.validationResult = { warning_count: 1 } as ValidationResult
      expect(store.hasWarnings).toBe(true)

      store.validationResult = { warning_count: 0 } as ValidationResult
      expect(store.hasWarnings).toBe(false)
    })

    it('should compute error count', () => {
      const store = useValidationStore()

      expect(store.errorCount).toBe(0)

      store.validationResult = { error_count: 5 } as ValidationResult
      expect(store.errorCount).toBe(5)
    })

    it('should compute warning count', () => {
      const store = useValidationStore()

      expect(store.warningCount).toBe(0)

      store.validationResult = { warning_count: 3 } as ValidationResult
      expect(store.warningCount).toBe(3)
    })

    it('should expose errors array', () => {
      const store = useValidationStore()
      const errors = [
        { message: 'Error 1', severity: 'error' } as ValidationError,
        { message: 'Error 2', severity: 'error' } as ValidationError,
      ]

      expect(store.errors).toEqual([])

      store.validationResult = { errors } as ValidationResult
      expect(store.errors).toEqual(errors)
    })

    it('should expose warnings array', () => {
      const store = useValidationStore()
      const warnings = [
        { message: 'Warning 1', severity: 'warning' } as ValidationError,
        { message: 'Warning 2', severity: 'warning' } as ValidationError,
      ]

      expect(store.warnings).toEqual([])

      store.validationResult = { warnings } as ValidationResult
      expect(store.warnings).toEqual(warnings)
    })

    it('should combine all messages', () => {
      const store = useValidationStore()
      const errors = [{ message: 'Error 1', severity: 'error' } as ValidationError]
      const warnings = [{ message: 'Warning 1', severity: 'warning' } as ValidationError]

      store.validationResult = { errors, warnings } as ValidationResult

      expect(store.allMessages).toEqual([...errors, ...warnings])
    })

    it('should group messages by severity', () => {
      const store = useValidationStore()
      const errors = [
        { message: 'Error 1', severity: 'error' } as ValidationError,
        { message: 'Error 2', severity: 'error' } as ValidationError,
      ]
      const warnings = [{ message: 'Warning 1', severity: 'warning' } as ValidationError]

      store.validationResult = { errors, warnings } as ValidationResult

      expect(store.messagesBySeverity.error).toHaveLength(2)
      expect(store.messagesBySeverity.warning).toHaveLength(1)
      expect(store.messagesBySeverity.info).toHaveLength(0)
    })

    it('should group messages by entity', () => {
      const store = useValidationStore()
      const errors = [
        { message: 'Error 1', severity: 'error', entity: 'entity1' } as ValidationError,
        { message: 'Error 2', severity: 'error', entity: 'entity1' } as ValidationError,
      ]
      const warnings = [{ message: 'Warning 1', severity: 'warning', entity: 'entity2' } as ValidationError]

      store.validationResult = { errors, warnings } as ValidationResult

      expect(store.messagesByEntity.entity1).toHaveLength(2)
      expect(store.messagesByEntity.entity2).toHaveLength(1)
    })

    it('should detect circular dependencies from dependency graph', () => {
      const store = useValidationStore()

      expect(store.hasCircularDependencies).toBe(false)

      store.dependencyGraph = { has_cycles: true } as DependencyGraph
      expect(store.hasCircularDependencies).toBe(true)

      store.dependencyGraph = { has_cycles: false } as DependencyGraph
      expect(store.hasCircularDependencies).toBe(false)
    })

    it('should detect circular dependencies from check result', () => {
      const store = useValidationStore()

      store.circularDependencyCheck = { has_cycles: true } as CircularDependencyCheck
      expect(store.hasCircularDependencies).toBe(true)
    })

    it('should expose cycles from dependency graph', () => {
      const store = useValidationStore()
      const cycles = [['entity1', 'entity2', 'entity1']]

      store.dependencyGraph = { cycles } as DependencyGraph

      expect(store.cycles).toEqual(cycles)
    })

    it('should expose cycles from circular check', () => {
      const store = useValidationStore()
      const cycles = [['entity1', 'entity2', 'entity1']]

      store.circularDependencyCheck = { cycles } as CircularDependencyCheck

      expect(store.cycles).toEqual(cycles)
    })

    it('should compute cycle count', () => {
      const store = useValidationStore()

      expect(store.cycleCount).toBe(0)

      store.circularDependencyCheck = { cycle_count: 3 } as CircularDependencyCheck
      expect(store.cycleCount).toBe(3)
    })

    it('should expose topological order', () => {
      const store = useValidationStore()
      const order = ['entity1', 'entity2', 'entity3']

      expect(store.topologicalOrder).toEqual([])

      store.dependencyGraph = { topological_order: order } as DependencyGraph
      expect(store.topologicalOrder).toEqual(order)
    })

    it('should compute is valid state', () => {
      const store = useValidationStore()

      expect(store.isValid).toBe(true)

      store.validationResult = { is_valid: false } as ValidationResult
      expect(store.isValid).toBe(false)

      store.validationResult = { is_valid: true } as ValidationResult
      expect(store.isValid).toBe(true)
    })
  })

  describe('validateProject', () => {
    it('should validate a project successfully', async () => {
      const store = useValidationStore()
      const mockResult = {
        is_valid: true,
        error_count: 0,
        warning_count: 0,
        errors: [],
        warnings: [],
        info: [],
      } as ValidationResult

      vi.mocked(api.projects.validate).mockResolvedValue(mockResult)

      const result = await store.validateProject('test-project')

      expect(api.projects.validate).toHaveBeenCalledWith('test-project')
      expect(store.validationResult).toEqual(mockResult)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(result).toEqual(mockResult)
    })

    it('should handle validation errors', async () => {
      const store = useValidationStore()

      vi.mocked(api.projects.validate).mockRejectedValue(new Error('Validation failed'))

      await expect(store.validateProject('test-project')).rejects.toThrow('Validation failed')

      expect(store.error).toBe('Validation failed')
      expect(store.loading).toBe(false)
    })
  })

  describe('validateEntity', () => {
    it('should validate an entity successfully', async () => {
      const store = useValidationStore()
      const mockResult = {
        is_valid: true,
        error_count: 0,
        warning_count: 0,
      } as ValidationResult

      vi.mocked(api.validation.validateEntity).mockResolvedValue(mockResult)

      const result = await store.validateEntity('test-project', 'test-entity')

      expect(api.validation.validateEntity).toHaveBeenCalledWith('test-project', 'test-entity')
      expect(store.entityValidationResults.get('test-entity')).toEqual(mockResult)
      expect(result).toEqual(mockResult)
    })

    it('should handle entity validation errors', async () => {
      const store = useValidationStore()

      vi.mocked(api.validation.validateEntity).mockRejectedValue(new Error('Entity validation failed'))

      await expect(store.validateEntity('test-project', 'test-entity')).rejects.toThrow('Entity validation failed')

      expect(store.error).toBe('Entity validation failed')
    })
  })

  describe('fetchDependencies', () => {
    it('should fetch dependencies successfully', async () => {
      const store = useValidationStore()
      const mockGraph = {
        nodes: ['entity1', 'entity2'],
        edges: [['entity1', 'entity2']],
        has_cycles: false,
        cycles: [],
      } as DependencyGraph

      vi.mocked(api.validation.getDependencies).mockResolvedValue(mockGraph)

      const result = await store.fetchDependencies('test-project')

      expect(api.validation.getDependencies).toHaveBeenCalledWith('test-project')
      expect(store.dependencyGraph).toEqual(mockGraph)
      expect(result).toEqual(mockGraph)
    })

    it('should handle fetch dependencies errors', async () => {
      const store = useValidationStore()

      vi.mocked(api.validation.getDependencies).mockRejectedValue(new Error('Fetch failed'))

      await expect(store.fetchDependencies('test-project')).rejects.toThrow('Fetch failed')

      expect(store.error).toBe('Fetch failed')
    })
  })

  describe('checkCircularDependencies', () => {
    it('should check circular dependencies successfully', async () => {
      const store = useValidationStore()
      const mockCheck = {
        has_cycles: true,
        cycle_count: 2,
        cycles: [
          ['entity1', 'entity2', 'entity1'],
          ['entity3', 'entity4', 'entity3'],
        ],
      } as CircularDependencyCheck

      vi.mocked(api.validation.checkCircularDependencies).mockResolvedValue(mockCheck)

      const result = await store.checkCircularDependencies('test-project')

      expect(api.validation.checkCircularDependencies).toHaveBeenCalledWith('test-project')
      expect(store.circularDependencyCheck).toEqual(mockCheck)
      expect(result).toEqual(mockCheck)
    })

    it('should handle check errors', async () => {
      const store = useValidationStore()

      vi.mocked(api.validation.checkCircularDependencies).mockRejectedValue(new Error('Check failed'))

      await expect(store.checkCircularDependencies('test-project')).rejects.toThrow('Check failed')

      expect(store.error).toBe('Check failed')
    })
  })

  describe('getEntityValidation', () => {
    it('should get entity validation result', () => {
      const store = useValidationStore()
      const result = { is_valid: true, error_count: 0 } as ValidationResult

      store.entityValidationResults.set('test-entity', result)

      expect(store.getEntityValidation('test-entity')).toEqual(result)
      expect(store.getEntityValidation('nonexistent')).toBeNull()
    })
  })

  describe('hasEntityErrors', () => {
    it('should detect entity errors', () => {
      const store = useValidationStore()

      expect(store.hasEntityErrors('test-entity')).toBe(false)

      store.entityValidationResults.set('test-entity', { error_count: 1 } as ValidationResult)
      expect(store.hasEntityErrors('test-entity')).toBe(true)

      store.entityValidationResults.set('test-entity', { error_count: 0 } as ValidationResult)
      expect(store.hasEntityErrors('test-entity')).toBe(false)
    })
  })

  describe('hasEntityWarnings', () => {
    it('should detect entity warnings', () => {
      const store = useValidationStore()

      expect(store.hasEntityWarnings('test-entity')).toBe(false)

      store.entityValidationResults.set('test-entity', { warning_count: 1 } as ValidationResult)
      expect(store.hasEntityWarnings('test-entity')).toBe(true)

      store.entityValidationResults.set('test-entity', { warning_count: 0 } as ValidationResult)
      expect(store.hasEntityWarnings('test-entity')).toBe(false)
    })
  })

  describe('clearValidation', () => {
    it('should clear validation state', () => {
      const store = useValidationStore()
      store.validationResult = { error_count: 1 } as ValidationResult
      store.entityValidationResults.set('entity1', { error_count: 0 } as ValidationResult)

      store.clearValidation()

      expect(store.validationResult).toBeNull()
      expect(store.entityValidationResults.size).toBe(0)
    })
  })

  describe('clearDependencies', () => {
    it('should clear dependency state', () => {
      const store = useValidationStore()
      store.dependencyGraph = { has_cycles: false } as DependencyGraph
      store.circularDependencyCheck = { has_cycles: false } as CircularDependencyCheck

      store.clearDependencies()

      expect(store.dependencyGraph).toBeNull()
      expect(store.circularDependencyCheck).toBeNull()
    })
  })

  describe('clearError', () => {
    it('should clear error state', () => {
      const store = useValidationStore()
      store.error = 'Some error'

      store.clearError()

      expect(store.error).toBeNull()
    })
  })

  describe('reset', () => {
    it('should reset all state to initial values', () => {
      const store = useValidationStore()
      store.validationResult = { error_count: 1 } as ValidationResult
      store.entityValidationResults.set('entity1', { error_count: 0 } as ValidationResult)
      store.dependencyGraph = { has_cycles: false } as DependencyGraph
      store.circularDependencyCheck = { has_cycles: false } as CircularDependencyCheck
      store.loading = true
      store.error = 'Some error'

      store.reset()

      expect(store.validationResult).toBeNull()
      expect(store.entityValidationResults.size).toBe(0)
      expect(store.dependencyGraph).toBeNull()
      expect(store.circularDependencyCheck).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })
})
