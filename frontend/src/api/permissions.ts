/**
 * API client for what the current user may do
 */

import { apiRequest } from './client'

export interface UserPermissions {
  can_read_logs: boolean
}

export const permissionsApi = {
  /**
   * Fetch which deployment-wide features the current user may use
   */
  getMyPermissions: async (): Promise<UserPermissions> => {
    return apiRequest<UserPermissions>({ method: 'GET', url: '/me/permissions' })
  },
}
