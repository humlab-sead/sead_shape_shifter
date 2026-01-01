import { apiClient } from './client'

export interface DispatcherMetadata {
  key: string
  target_type: 'file' | 'folder' | 'database'
  description: string
}

export interface ExecuteRequest {
  dispatcher_key: string
  target: string
  run_validation?: boolean
  translate?: boolean
  drop_foreign_keys?: boolean
  default_entity?: string | null
}

export interface ExecuteResult {
  success: boolean
  message: string
  target: string
  dispatcher_key: string
  entity_count: number
  validation_passed: boolean | null
  error_details: string | null
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
    const response = await apiClient.post<ExecuteResult>(
      `/projects/${projectName}/execute`,
      request
    )
    return response.data
  }
}
