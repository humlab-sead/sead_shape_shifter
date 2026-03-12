/**
 * Tasks API client
 */

import { apiClient } from './client'

export interface TaskInitializeResponse {
  success: boolean
  strategy: string
  todo: string[]
  message: string
}

export interface TaskNoteResponse {
  success: boolean
  entity_name: string
  note: string | null
  has_note: boolean
  message?: string | null
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

  /**
   * Get note for an entity
   */
  getNote: async (projectName: string, entityName: string): Promise<TaskNoteResponse> => {
    const response = await apiClient.get<TaskNoteResponse>(
      `/projects/${projectName}/tasks/${entityName}/note`
    )
    return response.data
  },

  /**
   * Create or update note for an entity
   */
  setNote: async (projectName: string, entityName: string, note: string): Promise<TaskNoteResponse> => {
    const response = await apiClient.put<TaskNoteResponse>(
      `/projects/${projectName}/tasks/${entityName}/note`,
      { note }
    )
    return response.data
  },

  /**
   * Remove note from an entity
   */
  removeNote: async (projectName: string, entityName: string): Promise<TaskNoteResponse> => {
    const response = await apiClient.delete<TaskNoteResponse>(
      `/projects/${projectName}/tasks/${entityName}/note`
    )
    return response.data
  },
}
