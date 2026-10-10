/**
 * API service for entity management
 */

import { apiRequest } from './client'

export interface MaterializedMetadata {
  enabled: boolean
  source_state?: Record<string, unknown>
  materialized_at?: string
}

export interface FixedSchema {
  full_columns: string[]
  editable_columns: string[]
  identity_columns: string[]
  key_columns: string[]
  order_source: 'stored' | 'derived'
}

export interface EntityResponse {
  name: string
  entity_data: Record<string, unknown>
  etag: string
  materialized?: MaterializedMetadata
  fixed_schema?: FixedSchema | null
  warnings?: string[]
}

export interface EntityCreateRequest {
  name: string
  entity_data: Record<string, unknown>
}

export interface EntityUpdateRequest {
  new_name?: string
  entity_data: Record<string, unknown>
}

export interface ColumnAvailabilityRequest {
  entity_draft: Record<string, unknown>
  source_columns?: string[] | null
}

export interface ForeignKeyColumnCandidates {
  index: number
  entity: string
  local_keys_before_unnest: string[]
  local_keys_after_unnest: string[]
  remote_keys: string[]
  extra_column_sources: string[]
}

export interface ColumnAvailabilityResponse {
  columns: string[]
  business_keys: string[]
  replacements: string[]
  drop_duplicates: string[]
  drop_empty_rows: string[]
  extra_columns: { sources: string[] }
  filters: Record<string, string[]>
  foreign_keys: ForeignKeyColumnCandidates[]
  unnest: { id_vars: string[]; value_vars: string[] }
}

export interface GenerateFromTableRequest {
  data_source: string
  table_name: string
  entity_name?: string
  schema_name?: string
}

export interface EntityValuesResponse {
  columns: string[]
  values: unknown[][]
  format: string
  row_count: number
  etag: string
}

export interface EntityValuesUpdateRequest {
  columns: string[]
  values: unknown[][]
  format?: string
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
   * Get operation-specific column candidates for an unsaved entity draft.
   */
  getColumnAvailability: async (
    projectName: string,
    entityName: string,
    data: ColumnAvailabilityRequest
  ): Promise<ColumnAvailabilityResponse> => {
    return apiRequest<ColumnAvailabilityResponse>({
      method: 'POST',
      url: `/projects/${projectName}/entities/${entityName}/column-availability`,
      data,
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
   * Update entity (conditional when ifMatch is supplied)
   */
  update: async (
    projectName: string,
    entityName: string,
    data: EntityUpdateRequest,
    ifMatch?: string
  ): Promise<EntityResponse> => {
    return apiRequest<EntityResponse>({
      method: 'PUT',
      url: `/projects/${projectName}/entities/${entityName}`,
      data,
      headers: ifMatch ? { 'If-Match': ifMatch } : undefined,
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

  /**
   * Get external values for entity with @load: directive
   *
   * @param format - Optional format negotiation (parquet/csv)
   */
  getValues: async (projectName: string, entityName: string, format?: string): Promise<EntityValuesResponse> => {
    const params = format ? { format } : undefined
    return apiRequest<EntityValuesResponse>({
      method: 'GET',
      url: `/projects/${projectName}/entities/${entityName}/values`,
      params,
    })
  },

  /**
   * Update external values for entity with @load: directive
   *
   * @param ifMatch - Optional etag for optimistic locking
   */
  updateValues: async (
    projectName: string,
    entityName: string,
    data: EntityValuesUpdateRequest,
    ifMatch?: string
  ): Promise<EntityValuesResponse> => {
    const headers = ifMatch ? { 'If-Match': ifMatch } : undefined
    return apiRequest<EntityValuesResponse>({
      method: 'PUT',
      url: `/projects/${projectName}/entities/${entityName}/values`,
      data,
      headers,
    })
  },
}
