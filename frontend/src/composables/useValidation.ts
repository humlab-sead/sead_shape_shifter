/**
 * Composable for validation functionality
 * Wraps the validation store with convenient methods
 */

import { computed, watch, ref } from 'vue'
import { useValidationStore } from '@/stores'

export interface UseValidationOptions {
  configName?: string
  autoValidate?: boolean
  validateOnChange?: boolean
}

export function useValidation(options: UseValidationOptions = {}) {
  const { configName, autoValidate = false, validateOnChange = false } = options
  const store = useValidationStore()
  const lastValidatedConfig = ref<string | null>(null)

  // Computed state from store
  const validationResult = computed(() => store.validationResult)
  const entityValidationResults = computed(() => store.entityValidationResults)
  const loading = computed(() => store.loading)
  const error = computed(() => store.error)

  // Computed getters
  const hasErrors = computed(() => store.hasErrors)
  const hasWarnings = computed(() => store.hasWarnings)
  const errorCount = computed(() => store.errorCount)
  const warningCount = computed(() => store.warningCount)
  const errors = computed(() => store.errors)
  const warnings = computed(() => store.warnings)
  const allMessages = computed(() => store.allMessages)
  const messagesBySeverity = computed(() => store.messagesBySeverity)
  const messagesByEntity = computed(() => store.messagesByEntity)
  const isValid = computed(() => store.isValid)

  // Actions
  async function validate(name: string) {
    try {
      const result = await store.validateConfiguration(name)
      lastValidatedConfig.value = name
      return result
    } catch (err) {
      console.error(`Failed to validate configuration "${name}":`, err)
      throw err
    }
  }

  async function validateEntity(name: string, entityName: string) {
    try {
      return await store.validateEntity(name, entityName)
    } catch (err) {
      console.error(`Failed to validate entity "${entityName}":`, err)
      throw err
    }
  }

  function getEntityValidation(entityName: string) {
    return store.getEntityValidation(entityName)
  }

  function hasEntityErrors(entityName: string) {
    return store.hasEntityErrors(entityName)
  }

  function hasEntityWarnings(entityName: string) {
    return store.hasEntityWarnings(entityName)
  }

  function clearValidation() {
    store.clearValidation()
    lastValidatedConfig.value = null
  }

  function clearError() {
    store.clearError()
  }

  // Helper: Get summary statistics
  const validationSummary = computed(() => ({
    isValid: isValid.value,
    totalIssues: errorCount.value + warningCount.value,
    errorCount: errorCount.value,
    warningCount: warningCount.value,
    entityCount: Object.keys(messagesByEntity.value).length,
  }))

  // Helper: Check if validation is stale
  const isStale = computed(() => {
    return configName ? lastValidatedConfig.value !== configName : false
  })

  // Auto-validate if enabled
  if (autoValidate && configName) {
    validate(configName)
  }

  // Watch for config changes and re-validate if enabled
  watch(
    () => configName,
    async (newName, oldName) => {
      if (validateOnChange && newName && newName !== oldName) {
        await validate(newName)
      }
    }
  )

  return {
    // State
    validationResult,
    entityValidationResults,
    loading,
    error,
    lastValidatedConfig,
    // Computed
    hasErrors,
    hasWarnings,
    errorCount,
    warningCount,
    errors,
    warnings,
    allMessages,
    messagesBySeverity,
    messagesByEntity,
    isValid,
    validationSummary,
    isStale,
    // Actions
    validate,
    validateEntity,
    getEntityValidation,
    hasEntityErrors,
    hasEntityWarnings,
    clearValidation,
    clearError,
  }
}
