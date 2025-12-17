/**
 * Driver schema types for data source configuration
 */

export type FieldType = 'string' | 'integer' | 'boolean' | 'password' | 'file_path'

export interface FieldMetadata {
  name: string
  type: FieldType
  required: boolean
  default?: any
  description: string
  min_value?: number | null
  max_value?: number | null
  placeholder: string
}

export interface DriverSchema {
  driver: string
  display_name: string
  description: string
  category: 'database' | 'file'
  fields: FieldMetadata[]
}

export type DriverSchemas = Record<string, DriverSchema>
