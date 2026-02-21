/**
 * Health check API
 */

import { apiClient } from './client'

export interface HealthResponse {
  status: string
  version: string
  environment: string
  timestamp: string
  projects_dir: string
  backups_dir: string
}

export const healthApi = {
  /**
   * Get application health and version information
   */
  getHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/health')
    return response.data
  },
}
