import { apiClient } from './client'

export interface DispatcherMetadata {
  key: string
  target_type: 'file' | 'folder' | 'database'
  description: string
  extension: string | null
}

export interface ExecuteRequest {
  dispatcher_key: string
  target: string // Managed output name/relative path, or data source name for database targets.
  run_validation?: boolean
  translate?: boolean
  drop_foreign_keys?: boolean
  default_entity?: string | null
}

export interface OutputExpectationResult {
  name: string
  entity: string
  metric: string
  // Configured group value; null for scalar metrics and for an explicitly configured null group.
  group_value: string | boolean | number | null
  // Measured count, or null when the expected entity was absent or incomplete.
  measured_value: number | null
  expected_limit: Record<string, number>
  status: 'pass' | 'fail'
  failure_reason: string | null
}

export interface ExecuteResult {
  success: boolean
  message: string
  target: string
  dispatcher_key: string
  target_type: 'file' | 'folder' | 'database' | 'unknown'
  entity_count: number
  validation_passed: boolean | null
  error_details: string | null
  download_path: string | null
  output_expectation_results: OutputExpectationResult[]
}

export const executeApi = {
  /**
   * Get list of available dispatchers
   */
  async getDispatchers(): Promise<DispatcherMetadata[]> {
    const response = await apiClient.get<DispatcherMetadata[]>('/dispatchers')
    return response.data
  },

  /**
   * Execute full workflow for a project
   */
  async executeWorkflow(projectName: string, request: ExecuteRequest): Promise<ExecuteResult> {
    const response = await apiClient.post<ExecuteResult>(`/projects/${projectName}/execute`, request)
    return response.data
  },
}
