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

export interface SubmissionContextInput {
  submission_name: string
  project_name: string
  timestamp: string
  datatype: string
  identifier: string
  description?: string | null
  issue_number?: string | null
  author?: string | null
}

export interface PendingConfirmationReport {
  submission_name: string
  project_name: string
  binding_set_uuid?: string | null
  binding_set_state?: string | null
  blocked_entities: string[]
  blocked_rows: number
  outstanding_step: string
  operator_action: string
  rerun_instruction: string
}

export interface DeployArtifact {
  metadata?: Record<string, any>
  metadata_artifact?: Record<string, any>
  bundle_files?: Record<string, string>
}

export interface ValidateRequest {
  source: string
  config?: Record<string, any>
  submission_context?: SubmissionContextInput
  deploy_strategy?: string
}

export interface ValidateResponse {
  is_valid: boolean
  errors: string[]
  warnings: string[]
  infos: string[]
  pending_confirmation_report?: PendingConfirmationReport
}

export interface IngestRequest {
  source: string
  config?: Record<string, any>
  submission_name: string
  data_types: string
  output_folder?: string
  do_register?: boolean
  explode?: boolean
  submission_context?: SubmissionContextInput
  deploy_strategy?: string
}

export interface IngestResponse {
  success: boolean
  records_processed: number
  message: string
  submission_id?: number
  output_path?: string
  error_details?: string
  deploy_artifact?: DeployArtifact
  pending_confirmation_report?: PendingConfirmationReport
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
