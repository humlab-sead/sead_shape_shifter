/**
 * API service for entity management
 */

import { apiRequest } from './client'

export interface MaterializedMetadata {
  enabled: boolean
  source_state?: Record<string, unknown>
  materialized_at?: string
  materialized_by?: string
  data_file?: string
}

export interface EntityResponse {
  name: string
  entity_data: Record<string, unknown>
  materialized?: MaterializedMetadata
}

export interface EntityCreateRequest {
  name: string
  entity_data: Record<string, unknown>
}

export interface EntityUpdateRequest {
  entity_data: Record<string, unknown>
}

export interface GenerateFromTableRequest {
  data_source: string
  table_name: string
  entity_name?: string
  schema_name?: string
}

/**
 * Entity API service
 */
export const entitiesApi = {
  /**
   * List all entities in a Project
   */
  list: async (projectName: string): Promise<EntityResponse[]> => {
    return apiRequest<EntityResponse[]>({
      method: 'GET',
      url: `/projects/${projectName}/entities`,
    })
  },

  /**
   * Get specific entity
   */
  get: async (projectName: string, entityName: string): Promise<EntityResponse> => {
    return apiRequest<EntityResponse>({
      method: 'GET',
      url: `/projects/${projectName}/entities/${entityName}`,
    })
  },

  /**
   * Create new entity
   */
  create: async (projectName: string, data: EntityCreateRequest): Promise<EntityResponse> => {
    return apiRequest<EntityResponse>({
      method: 'POST',
      url: `/projects/${projectName}/entities`,
      data,
    })
  },

  /**
   * Update entity
   */
  update: async (projectName: string, entityName: string, data: EntityUpdateRequest): Promise<EntityResponse> => {
    return apiRequest<EntityResponse>({
      method: 'PUT',
      url: `/projects/${projectName}/entities/${entityName}`,
      data,
    })
  },

  /**
   * Delete entity
   */
  delete: async (projectName: string, entityName: string): Promise<void> => {
    return apiRequest<void>({
      method: 'DELETE',
      url: `/projects/${projectName}/entities/${entityName}`,
    })
  },

  /**
   * Generate entity from database table
   */
  generateFromTable: async (projectName: string, data: GenerateFromTableRequest): Promise<EntityResponse> => {
    return apiRequest<EntityResponse>({
      method: 'POST',
      url: `/projects/${projectName}/entities/generate-from-table`,
      data,
    })
  },
}
