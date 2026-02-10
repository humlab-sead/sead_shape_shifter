/**
 * API client for entity materialization operations
 */

import { apiClient } from './client'

export interface MaterializeRequest {
  storage_format: 'parquet' | 'csv' | 'inline'
}

export interface MaterializationResult {
  success: boolean
  entity_name: string
  rows_materialized?: number
  storage_file?: string
  storage_format?: string
  errors?: string[]
}

export interface UnmaterializeRequest {
  cascade: boolean
}

export interface UnmaterializationResult {
  success: boolean
  entity_name: string
  unmaterialized_entities?: string[]
  requires_cascade?: boolean
  affected_entities?: string[]
  errors?: string[]
}

export interface CanMaterializeResponse {
  can_materialize: boolean
  errors: string[]
}

export const materializationApi = {
  /**
   * Check if an entity can be materialized
   */
  async canMaterialize(
    projectName: string,
    entityName: string
  ): Promise<CanMaterializeResponse> {
    const response = await apiClient.get<CanMaterializeResponse>(
      `/projects/${projectName}/entities/${entityName}/can-materialize`
    )
    return response.data
  },

  /**
   * Materialize an entity to fixed values
   */
  async materialize(
    projectName: string,
    entityName: string,
    request: MaterializeRequest
  ): Promise<MaterializationResult> {
    const response = await apiClient.post<MaterializationResult>(
      `/projects/${projectName}/entities/${entityName}/materialize`,
      request
    )
    return response.data
  },

  /**
   * Restore entity to dynamic state
   */
  async unmaterialize(
    projectName: string,
    entityName: string,
    cascade: boolean = false
  ): Promise<UnmaterializationResult> {
    const response = await apiClient.post<UnmaterializationResult>(
      `/projects/${projectName}/entities/${entityName}/unmaterialize`,
      { cascade }
    )
    return response.data
  },
}
