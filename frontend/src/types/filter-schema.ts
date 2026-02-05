/**
 * Filter schema types for dynamic filter configuration.
 * 
 * These types mirror the backend FilterSchema models and enable
 * type-safe filter configuration throughout the application.
 */

export type FilterFieldType = 'string' | 'boolean' | 'entity' | 'column'

export type OptionsSource = 'entities' | 'columns'

/**
 * Metadata for a single filter configuration field.
 */
export interface FilterFieldMetadata {
  name: string
  type: FilterFieldType
  required: boolean
  default?: any
  description: string
  placeholder: string
  options_source?: OptionsSource
}

/**
 * Complete schema for a filter type.
 */
export interface FilterSchema {
  key: string
  display_name: string
  description: string
  fields: FilterFieldMetadata[]
}

/**
 * Runtime filter configuration.
 * Type is required, all other fields are dynamic based on the filter schema.
 */
export interface FilterConfig {
  type: string
  [key: string]: any
}
