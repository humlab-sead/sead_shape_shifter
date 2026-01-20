/**
 * Composable for managing driver schemas
 *
 * Provides access to data source driver metadata including:
 * - Field definitions
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
      .filter((f) => f.required)
      .map((f) => f.name)
  }

  /**
   * Get optional field names for a driver
   */
  function getOptionalFields(driver: string): string[] {
    return getFieldsForDriver(driver)
      .filter((f) => !f.required)
      .map((f) => f.name)
  }

  /**
   * Get field by name for a driver
   */
  function getField(driver: string, fieldName: string): FieldMetadata | undefined {
    return getFieldsForDriver(driver).find((f) => f.name === fieldName)
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

    fields.forEach((field) => {
      if (field.default !== undefined && field.default !== null) {
        defaults[field.name] = field.default
      }
    })

    return defaults
  }

  /**
   * Validate a field value
   */
  function validateField(driver: string, fieldName: string, value: any): { valid: boolean; error?: string } {
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
    // Deduplicate drivers by display name to collapse aliases (e.g., csv/tsv, xlsx/xls)
    const unique = new Map<
      string,
      { value: string; title?: string; description?: string; category?: string; aliases: string[] }
    >()

    Object.entries(schemas.value).forEach(([key, schema]) => {
      const dedupeKey = schema.display_name || schema.driver || key
      const value = schema.driver || key

      if (!unique.has(dedupeKey)) {
        unique.set(dedupeKey, {
          value,
          title: schema.display_name,
          description: schema.description,
          category: schema.category,
          aliases: Array.from(new Set([key, schema.driver].filter(Boolean) as string[])),
        })
      } else {
        const entry = unique.get(dedupeKey)
        if (entry) {
          entry.aliases = Array.from(new Set([...entry.aliases, key, schema.driver].filter(Boolean) as string[]))
        }
      }
    })

    return Array.from(unique.values())
  })

  function getCanonicalDriver(driver: string): string {
    // Prefer canonical value for the deduped entry that contains this driver as value or alias
    const match = availableDrivers.value.find((entry) => entry.value === driver || entry.aliases.includes(driver))
    return match?.value || driver
  }

  /**
   * Get drivers by category
   */
  function getDriversByCategory(category: 'database' | 'file') {
    return Object.values(schemas.value)
      .filter((schema) => schema.category === category)
      .map((schema) => ({
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
    getCanonicalDriver,
    getDriversByCategory,
  }
}
