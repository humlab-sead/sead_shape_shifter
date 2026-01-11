/**
 * API service for reconciliation specification management
 */

import type {
  ReconciliationConfig,
  SpecificationListItem,
  SpecificationCreateRequest,
  SpecificationUpdateRequest,
} from '@/types/reconciliation'
import { apiRequest } from './client'

/**
 * Reconciliation Specification API service
 */
export const reconciliationSpecApi = {
  /**
   * List all reconciliation specifications for a project
   */
  listSpecifications: async (projectName: string): Promise<SpecificationListItem[]> => {
    return apiRequest<SpecificationListItem[]>({
      method: 'GET',
      url: `/projects/${projectName}/reconciliation/specifications`,
    })
  },

  /**
   * Create a new reconciliation specification
   */
  createSpecification: async (
    projectName: string,
    request: SpecificationCreateRequest
  ): Promise<ReconciliationConfig> => {
    return apiRequest<ReconciliationConfig>({
      method: 'POST',
      url: `/projects/${projectName}/reconciliation/specifications`,
      data: request,
    })
  },

  /**
   * Update an existing reconciliation specification
   */
  updateSpecification: async (
    projectName: string,
    entityName: string,
    targetField: string,
    request: SpecificationUpdateRequest
  ): Promise<ReconciliationConfig> => {
    return apiRequest<ReconciliationConfig>({
      method: 'PUT',
      url: `/projects/${projectName}/reconciliation/specifications/${entityName}/${targetField}`,
      data: request,
    })
  },

  /**
   * Delete a reconciliation specification
   */
  deleteSpecification: async (
    projectName: string,
    entityName: string,
    targetField: string,
    force: boolean = false
  ): Promise<ReconciliationConfig> => {
    return apiRequest<ReconciliationConfig>({
      method: 'DELETE',
      url: `/projects/${projectName}/reconciliation/specifications/${entityName}/${targetField}`,
      params: { force },
    })
  },

  /**
   * Get available target fields for an entity
   */
  getAvailableFields: async (projectName: string, entityName: string): Promise<string[]> => {
    return apiRequest<string[]>({
      method: 'GET',
      url: `/projects/${projectName}/reconciliation/available-fields/${entityName}`,
    })
  },

  /**
   * Get mapping count for a specification
   */
  getMappingCount: async (
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<number> => {
    const response = await apiRequest<{ count: number }>({
      method: 'GET',
      url: `/projects/${projectName}/reconciliation/specifications/${entityName}/${targetField}/mapping-count`,
    })
    return response.count
  },
}

/**
 * Reconciliation Service API
 */
export const reconciliationServiceApi = {
  /**
   * Get reconciliation service manifest
   * Returns the service metadata including available entity types
   */
  getManifest: async (): Promise<any> => {
    return apiRequest<any>({
      method: 'GET',
      url: '/reconciliation/manifest',
    })
  },

  /**
   * Check reconciliation service health
   */
  checkHealth: async (): Promise<{ status: string; service_name?: string; error?: string }> => {
    return apiRequest<{ status: string; service_name?: string; error?: string }>({
      method: 'GET',
      url: '/reconciliation/health',
    })
  },
}
