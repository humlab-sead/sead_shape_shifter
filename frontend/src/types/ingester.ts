/**
 * TypeScript types for ingester functionality
 */

export interface IngesterMetadata {
  key: string
  name: string
  description: string
  version: string
  supported_formats: string[]
}

export interface ValidateRequest {
  source: string
  config?: Record<string, any>
}

export interface ValidateResponse {
  is_valid: boolean
  errors: string[]
  warnings: string[]
}

export interface IngestRequest {
  source: string
  config?: Record<string, any>
  submission_name: string
  data_types: string
  output_folder?: string
  do_register?: boolean
  explode?: boolean
}

export interface IngestResponse {
  success: boolean
  records_processed: number
  message: string
  submission_id?: number
  output_path?: string
}

export interface DatabaseConfig {
  host: string
  port: number
  dbname: string
  user: string
}

export interface IngesterConfig {
  database?: DatabaseConfig
  ignore_columns?: string[]
  [key: string]: any // Allow additional custom config
}
