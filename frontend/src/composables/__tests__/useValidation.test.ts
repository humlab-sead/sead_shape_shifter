import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick } from 'vue'
import { useValidation } from '../useValidation'
import { useValidationStore } from '@/stores'
import type { ValidationResult, EntityValidationResult } from '@/types'

// Mock console methods
const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

describe('useValidation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    consoleError.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('initialization', () => {
    it('should initialize with default options', () => {
      const { loading, error, validationResult } = useValidation()

      expect(loading.value).toBe(false)
      expect(error.value).toBeNull()
      expect(validationResult.value).toBeNull()
    })

    it('should accept projectName option', () => {
      const { lastValidatedProject } = useValidation({ projectName: 'test-project' })

      expect(lastValidatedProject).toBeDefined()
      expect(lastValidatedProject.value).toBeNull()
    })

    it('should accept autoValidate option', () => {
      const { validationResult } = useValidation({ autoValidate: true })

      expect(validationResult.value).toBeNull()
    })

    it('should accept validateOnChange option', () => {
      const { validationResult } = useValidation({ validateOnChange: true })

      expect(validationResult.value).toBeNull()
    })
  })

  describe('computed state', () => {
    it('should expose validationResult from store', () => {
      const store = useValidationStore()
      const { validationResult } = useValidation()

      const mockResult: ValidationResult = {
        is_valid: true,
        has_errors: false,
        has_warnings: false,
        messages: [],
      }

      store.$patch({ validationResult: mockResult })

      expect(validationResult.value).toEqual(mockResult)
    })

    it('should expose entityValidationResults from store', () => {
      const store = useValidationStore()
      const { entityValidationResults } = useValidation()

      const mockResults: Record<string, EntityValidationResult> = {
        entity1: {
          entity_name: 'entity1',
          is_valid: true,
          errors: [],
          warnings: [],
        },
      }

      store.$patch({ entityValidationResults: mockResults })

      expect(entityValidationResults.value).toEqual(mockResults)
    })

    it('should expose loading state from store', () => {
      const store = useValidationStore()
      const { loading } = useValidation()

      store.$patch({ loading: true })
      expect(loading.value).toBe(true)

      store.$patch({ loading: false })
      expect(loading.value).toBe(false)
    })

    it('should expose error state from store', () => {
      const store = useValidationStore()
      const { error } = useValidation()

      store.$patch({ error: 'Test error' })
      expect(error.value).toBe('Test error')

      store.$patch({ error: null })
      expect(error.value).toBeNull()
    })
  })

  describe('computed getters', () => {
    it('should compute hasErrors correctly', () => {
      const store = useValidationStore()
      const { hasErrors } = useValidation()

      vi.spyOn(store, 'hasErrors', 'get').mockReturnValue(true)

      expect(hasErrors.value).toBe(true)
    })

    it('should compute hasWarnings correctly', () => {
      const store = useValidationStore()
      const { hasWarnings } = useValidation()

      vi.spyOn(store, 'hasWarnings', 'get').mockReturnValue(true)

      expect(hasWarnings.value).toBe(true)
    })

    it('should compute errorCount correctly', () => {
      const store = useValidationStore()
      const { errorCount } = useValidation()

      vi.spyOn(store, 'errorCount', 'get').mockReturnValue(2)

      expect(errorCount.value).toBe(2)
    })

    it('should compute warningCount correctly', () => {
      const store = useValidationStore()
      const { warningCount } = useValidation()

      vi.spyOn(store, 'warningCount', 'get').mockReturnValue(1)

      expect(warningCount.value).toBe(1)
    })

    it('should compute isValid correctly', () => {
      const store = useValidationStore()
      const { isValid } = useValidation()

      store.$patch({
        validationResult: {
          is_valid: true,
          has_errors: false,
          has_warnings: false,
          messages: [],
        },
      })

      expect(isValid.value).toBe(true)
    })
  })

  describe('validate action', () => {
    it('should validate a project', async () => {
      const store = useValidationStore()
      const mockResult: ValidationResult = {
        is_valid: true,
        has_errors: false,
        has_warnings: false,
        messages: [],
      }

      vi.spyOn(store, 'validateProject').mockResolvedValue(mockResult)

      const { validate, lastValidatedProject } = useValidation()
      const result = await validate('test-project')

      expect(store.validateProject).toHaveBeenCalledWith('test-project')
      expect(result).toEqual(mockResult)
      expect(lastValidatedProject.value).toBe('test-project')
    })

    it('should handle validation errors', async () => {
      const store = useValidationStore()
      const error = new Error('Validation failed')

      vi.spyOn(store, 'validateProject').mockRejectedValue(error)

      const { validate } = useValidation()

      await expect(validate('test-project')).rejects.toThrow('Validation failed')
    })
  })

  describe('validateEntity action', () => {
    it('should validate a specific entity', async () => {
      const store = useValidationStore()
      const mockResult: EntityValidationResult = {
        entity_name: 'test-entity',
        is_valid: true,
        errors: [],
        warnings: [],
      }

      vi.spyOn(store, 'validateEntity').mockResolvedValue(mockResult)

      const { validateEntity } = useValidation()
      const result = await validateEntity('test-project', 'test-entity')

      expect(store.validateEntity).toHaveBeenCalledWith('test-project', 'test-entity')
      expect(result).toEqual(mockResult)
    })

    it('should handle entity validation errors', async () => {
      const store = useValidationStore()
      const error = new Error('Entity validation failed')

      vi.spyOn(store, 'validateEntity').mockRejectedValue(error)

      const { validateEntity } = useValidation()

      await expect(validateEntity('test-project', 'entity')).rejects.toThrow()
    })
  })

  describe('helper methods', () => {
    it('should get entity validation result', () => {
      const store = useValidationStore()
      const mockResult: EntityValidationResult = {
        entity_name: 'entity1',
        is_valid: true,
        errors: [],
        warnings: [],
      }

      vi.spyOn(store, 'getEntityValidation').mockReturnValue(mockResult)

      const { getEntityValidation } = useValidation()
      const result = getEntityValidation('entity1')

      expect(store.getEntityValidation).toHaveBeenCalledWith('entity1')
      expect(result).toEqual(mockResult)
    })

    it('should check if entity has errors', () => {
      const store = useValidationStore()
      vi.spyOn(store, 'hasEntityErrors').mockReturnValue(true)

      const { hasEntityErrors } = useValidation()
      const result = hasEntityErrors('entity1')

      expect(store.hasEntityErrors).toHaveBeenCalledWith('entity1')
      expect(result).toBe(true)
    })

    it('should check if entity has warnings', () => {
      const store = useValidationStore()
      vi.spyOn(store, 'hasEntityWarnings').mockReturnValue(false)

      const { hasEntityWarnings } = useValidation()
      const result = hasEntityWarnings('entity1')

      expect(store.hasEntityWarnings).toHaveBeenCalledWith('entity1')
      expect(result).toBe(false)
    })
  })

  describe('clearValidation action', () => {
    it('should clear validation state', async () => {
      const store = useValidationStore()
      vi.spyOn(store, 'clearValidation')
      vi.spyOn(store, 'validateProject').mockResolvedValue({
        is_valid: true,
        has_errors: false,
        has_warnings: false,
        messages: [],
      })

      const { clearValidation, lastValidatedProject, validate } = useValidation()

      await validate('test-project')
      expect(lastValidatedProject.value).toBe('test-project')

      clearValidation()

      expect(store.clearValidation).toHaveBeenCalled()
      expect(lastValidatedProject.value).toBeNull()
    })
  })

  describe('clearError action', () => {
    it('should clear error state', () => {
      const store = useValidationStore()
      vi.spyOn(store, 'clearError')

      const { clearError } = useValidation()
      clearError()

      expect(store.clearError).toHaveBeenCalled()
    })
  })

  describe('summary statistics', () => {
    it('should compute validation summary correctly', () => {
      const store = useValidationStore()
      const { validationSummary } = useValidation()

      vi.spyOn(store, 'errorCount', 'get').mockReturnValue(2)
      vi.spyOn(store, 'warningCount', 'get').mockReturnValue(1)
      vi.spyOn(store, 'isValid', 'get').mockReturnValue(false)
      vi.spyOn(store, 'messagesByEntity', 'get').mockReturnValue({
        entity1: [{ severity: 'error', message: 'Error 1', entity: 'entity1', field: null }],
        entity2: [{ severity: 'error', message: 'Error 2', entity: 'entity2', field: null }],
      })

      expect(validationSummary.value.errorCount).toBe(2)
      expect(validationSummary.value.warningCount).toBe(1)
      expect(validationSummary.value.totalIssues).toBe(3)
      expect(validationSummary.value.isValid).toBe(false)
    })
  })

  describe('stale state tracking', () => {
    it('should track if validation is stale', async () => {
      const store = useValidationStore()
      vi.spyOn(store, 'validateProject').mockResolvedValue({
        is_valid: true,
        has_errors: false,
        has_warnings: false,
        messages: [],
      })

      const { isStale, validate } = useValidation({ projectName: 'project1' })

      expect(isStale.value).toBe(true)

      await validate('project1')
      expect(isStale.value).toBe(false)
    })

    it('should detect stale state when project changes', async () => {
      const store = useValidationStore()
      vi.spyOn(store, 'validateProject').mockResolvedValue({
        is_valid: true,
        has_errors: false,
        has_warnings: false,
        messages: [],
      })

      const { isStale, validate } = useValidation({ projectName: 'project2' })

      await validate('project1')
      expect(isStale.value).toBe(true)
    })
  })
})
