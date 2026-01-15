/**
 * Tasks API client
 */

import { apiClient } from './client'

export interface TaskInitializeResponse {
  success: boolean
  strategy: string
  required_entities: string[]
  message: string
}

export const tasksApi = {
  /**
   * Initialize task list for a project
   */
  initialize: async (projectName: string, strategy: string = 'dependency-order'): Promise<TaskInitializeResponse> => {
    const response = await apiClient.post<TaskInitializeResponse>(
      `/projects/${projectName}/tasks/initialize`,
      null,
      {
        params: { strategy }
      }
    )
    return response.data
  },
}
