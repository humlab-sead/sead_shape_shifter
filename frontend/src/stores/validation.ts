import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import type {
  ValidationResult,
  ValidationError,
  DependencyGraph,
  CircularDependencyCheck,
} from '@/types'

export const useValidationStore = defineStore('validation', () => {
  // State
  const validationResult = ref<ValidationResult | null>(null)
  const entityValidationResults = ref<Map<string, ValidationResult>>(new Map())
  const dependencyGraph = ref<DependencyGraph | null>(null)
  const circularDependencyCheck = ref<CircularDependencyCheck | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const hasErrors = computed(() => {
    return validationResult.value ? validationResult.value.error_count > 0 : false
  })

  const hasWarnings = computed(() => {
    return validationResult.value ? validationResult.value.warning_count > 0 : false
  })

  const errorCount = computed(() => validationResult.value?.error_count ?? 0)

  const warningCount = computed(() => validationResult.value?.warning_count ?? 0)

  const errors = computed(() => {
    return validationResult.value?.errors ?? []
  })

  const warnings = computed(() => {
    return validationResult.value?.warnings ?? []
  })

  const allMessages = computed(() => {
    return [...errors.value, ...warnings.value]
  })

  const messagesBySeverity = computed(() => {
    const grouped: Record<string, ValidationError[]> = {
      error: [],
      warning: [],
      info: [],
    }
    allMessages.value.forEach((msg: ValidationError) => {
      const severityGroup = grouped[msg.severity]
      if (severityGroup) {
        severityGroup.push(msg)
      }
    })
    return grouped
  })

  const messagesByEntity = computed(() => {
    const grouped: Record<string, ValidationError[]> = {}
    allMessages.value.forEach((msg: ValidationError) => {
      if (msg.entity) {
        if (!grouped[msg.entity]) {
          grouped[msg.entity] = []
        }
        const entityGroup = grouped[msg.entity]
        if (entityGroup) {
          entityGroup.push(msg)
        }
      }
    })
    return grouped
  })

  const hasCircularDependencies = computed(() => {
    return dependencyGraph.value?.has_cycles || circularDependencyCheck.value?.has_cycles || false
  })

  const cycles = computed(() => {
    return dependencyGraph.value?.cycles ?? circularDependencyCheck.value?.cycles ?? []
  })

  const cycleCount = computed(() => {
    return circularDependencyCheck.value?.cycle_count ?? cycles.value.length
  })

  const topologicalOrder = computed(() => {
    return dependencyGraph.value?.topological_order ?? []
  })

  const isValid = computed(() => {
    return validationResult.value?.is_valid ?? true
  })

  // Actions
  async function validateConfiguration(configName: string) {
    loading.value = true
    error.value = null
    try {
      validationResult.value = await api.projects.validate(configName)
      return validationResult.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to validate configuration'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function validateEntity(configName: string, entityName: string) {
    loading.value = true
    error.value = null
    try {
      const result = await api.validation.validateEntity(configName, entityName)
      entityValidationResults.value.set(entityName, result)
      return result
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to validate entity'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchDependencies(configName: string) {
    loading.value = true
    error.value = null
    try {
      dependencyGraph.value = await api.validation.getDependencies(configName)
      return dependencyGraph.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch dependencies'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function checkCircularDependencies(configName: string) {
    loading.value = true
    error.value = null
    try {
      circularDependencyCheck.value = await api.validation.checkCircularDependencies(configName)
      return circularDependencyCheck.value
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : 'Failed to check circular dependencies'
      throw err
    } finally {
      loading.value = false
    }
  }

  function getEntityValidation(entityName: string): ValidationResult | null {
    return entityValidationResults.value.get(entityName) || null
  }

  function hasEntityErrors(entityName: string): boolean {
    const result = getEntityValidation(entityName)
    return result ? result.error_count > 0 : false
  }

  function hasEntityWarnings(entityName: string): boolean {
    const result = getEntityValidation(entityName)
    return result ? result.warning_count > 0 : false
  }

  function clearValidation() {
    validationResult.value = null
    entityValidationResults.value.clear()
  }

  function clearDependencies() {
    dependencyGraph.value = null
    circularDependencyCheck.value = null
  }

  function clearError() {
    error.value = null
  }

  function reset() {
    validationResult.value = null
    entityValidationResults.value.clear()
    dependencyGraph.value = null
    circularDependencyCheck.value = null
    loading.value = false
    error.value = null
  }

  return {
    // State
    validationResult,
    entityValidationResults,
    dependencyGraph,
    circularDependencyCheck,
    loading,
    error,
    // Getters
    hasErrors,
    hasWarnings,
    errorCount,
    warningCount,
    errors,
    warnings,
    allMessages,
    messagesBySeverity,
    messagesByEntity,
    hasCircularDependencies,
    cycles,
    cycleCount,
    topologicalOrder,
    isValid,
    // Actions
    validateConfiguration,
    validateEntity,
    fetchDependencies,
    checkCircularDependencies,
    getEntityValidation,
    hasEntityErrors,
    hasEntityWarnings,
    clearValidation,
    clearDependencies,
    clearError,
    reset,
  }
})
