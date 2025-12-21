/**
 * Composable for managing driver schemas
 * 
 * Provides access to data source driver metadata including:
 * - Configuration field definitions
 * - Validation rules
 * - Display information
 */

import { ref, computed } from 'vue'
import { apiClient } from '@/api/client'
import type { DriverSchemas, DriverSchema, FieldMetadata } from '@/types/driver-schema'

const schemas = ref<DriverSchemas>({})
const loading = ref(false)
const error = ref<string | null>(null)
const initialized = ref(false)

export function useDriverSchema() {
  /**
   * Load driver schemas from API
   */
  async function loadSchemas() {
    if (initialized.value) {
      return schemas.value
    }

    loading.value = true
    error.value = null

    try {
      const response = await apiClient.get<DriverSchemas>('/data-sources/drivers')
      schemas.value = response.data
      initialized.value = true
      return schemas.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load driver schemas'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Get schema for a specific driver
   */
  function getSchema(driver: string): DriverSchema | undefined {
    return schemas.value[driver]
  }

  /**
   * Get configuration fields for a driver
   */
  function getFieldsForDriver(driver: string): FieldMetadata[] {
    return schemas.value[driver]?.fields || []
  }

  /**
   * Get required field names for a driver
   */
  function getRequiredFields(driver: string): string[] {
    return getFieldsForDriver(driver)
      .filter(f => f.required)
      .map(f => f.name)
  }

  /**
   * Get optional field names for a driver
   */
  function getOptionalFields(driver: string): string[] {
    return getFieldsForDriver(driver)
      .filter(f => !f.required)
      .map(f => f.name)
  }

  /**
   * Get field by name for a driver
   */
  function getField(driver: string, fieldName: string): FieldMetadata | undefined {
    return getFieldsForDriver(driver).find(f => f.name === fieldName)
  }

  /**
   * Get default value for a field
   */
  function getFieldDefault(driver: string, fieldName: string): any {
    const field = getField(driver, fieldName)
    return field?.default
  }

  /**
   * Initialize form with default values for a driver
   */
  function getDefaultFormValues(driver: string): Record<string, any> {
    const fields = getFieldsForDriver(driver)
    const defaults: Record<string, any> = {}
    
    fields.forEach(field => {
      if (field.default !== undefined && field.default !== null) {
        defaults[field.name] = field.default
      }
    })
    
    return defaults
  }

  /**
   * Validate a field value
   */
  function validateField(
    driver: string,
    fieldName: string,
    value: any
  ): { valid: boolean; error?: string } {
    const field = getField(driver, fieldName)
    
    if (!field) {
      return { valid: false, error: `Unknown field: ${fieldName}` }
    }

    // Check required
    if (field.required && (value === null || value === undefined || value === '')) {
      return { valid: false, error: `${field.description || fieldName} is required` }
    }

    // Type-specific validation
    if (value !== null && value !== undefined && value !== '') {
      switch (field.type) {
        case 'integer':
          if (!Number.isInteger(Number(value))) {
            return { valid: false, error: 'Must be an integer' }
          }
          if (field.min_value !== null && field.min_value !== undefined && Number(value) < field.min_value) {
            return { valid: false, error: `Must be at least ${field.min_value}` }
          }
          if (field.max_value !== null && field.max_value !== undefined && Number(value) > field.max_value) {
            return { valid: false, error: `Must be at most ${field.max_value}` }
          }
          break
        
        case 'file_path':
          if (typeof value !== 'string' || value.trim().length === 0) {
            return { valid: false, error: 'Must be a valid file path' }
          }
          break
      }
    }

    return { valid: true }
  }

  /**
   * Get list of all available drivers
   */
  const availableDrivers = computed(() => {
    return Object.keys(schemas.value).map(driver => ({
      value: driver,
      title: schemas.value[driver]?.display_name,
      description: schemas.value[driver]?.description,
      category: schemas.value[driver]?.category,
    }))
  })

  /**
   * Get drivers by category
   */
  function getDriversByCategory(category: 'database' | 'file') {
    return Object.values(schemas.value)
      .filter(schema => schema.category === category)
      .map(schema => ({
        value: schema.driver,
        title: schema.display_name,
        description: schema.description,
      }))
  }

  return {
    schemas,
    loading,
    error,
    initialized,
    loadSchemas,
    getSchema,
    getFieldsForDriver,
    getRequiredFields,
    getOptionalFields,
    getField,
    getFieldDefault,
    getDefaultFormValues,
    validateField,
    availableDrivers,
    getDriversByCategory,
  }
}
