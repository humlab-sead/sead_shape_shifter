/**
 * API service for entity management
 */

import { apiRequest } from './client'

export interface EntityResponse {
  name: string
  entity_data: Record<string, unknown>
}

export interface EntityCreateRequest {
  name: string
  entity_data: Record<string, unknown>
}

export interface EntityUpdateRequest {
  entity_data: Record<string, unknown>
}

/**
 * Entity API service
 */
export const entitiesApi = {
  /**
   * List all entities in a configuration
   */
  list: async (configName: string): Promise<EntityResponse[]> => {
    return apiRequest<EntityResponse[]>({
      method: 'GET',
      url: `/configurations/${configName}/entities`,
    })
  },

  /**
   * Get specific entity
   */
  get: async (configName: string, entityName: string): Promise<EntityResponse> => {
    return apiRequest<EntityResponse>({
      method: 'GET',
      url: `/configurations/${configName}/entities/${entityName}`,
    })
  },

  /**
   * Create new entity
   */
  create: async (configName: string, data: EntityCreateRequest): Promise<EntityResponse> => {
    return apiRequest<EntityResponse>({
      method: 'POST',
      url: `/configurations/${configName}/entities`,
      data,
    })
  },

  /**
   * Update entity
   */
  update: async (configName: string, entityName: string, data: EntityUpdateRequest): Promise<EntityResponse> => {
    return apiRequest<EntityResponse>({
      method: 'PUT',
      url: `/configurations/${configName}/entities/${entityName}`,
      data,
    })
  },

  /**
   * Delete entity
   */
  delete: async (configName: string, entityName: string): Promise<void> => {
    return apiRequest<void>({
      method: 'DELETE',
      url: `/configurations/${configName}/entities/${entityName}`,
    })
  },
}
