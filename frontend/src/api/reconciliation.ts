/**
 * API service for reconciliation specification management
 */

import type {
  EntityResolutionCatalog,
  EntityResolutionListItem,
  EntityResolutionCatalogCreateRequest,
  EntityResolutionCatalogUpdateRequest,
  ExportToMappingResult,
  AutoReconcileResult,
  DecisionUpdateRequest,
  EntityResolutionCatalog as EntityResolutionCatalogResponse,
  MappingEntityResponse,
  MappingLinkRecordResponse,
  MappingLinkUpsertRequest,
  ReconciliationCandidate,
  ReconciliationPreviewRow,
} from '@/types/reconciliation'
import { apiRequest } from './client'

/**
 * Reconciliation Specification API service
 */
export const reconciliationSpecApi = {
  /**
   * List all reconciliation specifications for a project
   */
  listSpecifications: async (projectName: string): Promise<EntityResolutionListItem[]> => {
    return apiRequest<EntityResolutionListItem[]>({
      method: 'GET',
      url: `/projects/${projectName}/reconciliation/mapping-registry`,
    })
  },

  /**
   * Create a new reconciliation specification
   */
  createSpecification: async (
    projectName: string,
    request: EntityResolutionCatalogCreateRequest
  ): Promise<EntityResolutionCatalog> => {
    return apiRequest<EntityResolutionCatalog>({
      method: 'POST',
      url: `/projects/${projectName}/reconciliation/mapping-registry`,
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
    request: EntityResolutionCatalogUpdateRequest
  ): Promise<EntityResolutionCatalog> => {
    return apiRequest<EntityResolutionCatalog>({
      method: 'PUT',
      url: `/projects/${projectName}/reconciliation/mapping-registry/${entityName}/${targetField}`,
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
  ): Promise<EntityResolutionCatalog> => {
    return apiRequest<EntityResolutionCatalog>({
      method: 'DELETE',
      url: `/projects/${projectName}/reconciliation/mapping-registry/${entityName}/${targetField}`,
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
  getMappingCount: async (projectName: string, entityName: string, targetField: string): Promise<number> => {
    const response = await apiRequest<{ count: number }>({
      method: 'GET',
      url: `/projects/${projectName}/reconciliation/mapping-registry/${entityName}/${targetField}/mapping-count`,
    })
    return response.count
  },
}

/**
 * Reconciliation Service API
 */
export const reconciliationServiceApi = {
  /**
   * Get preview rows and their saved decisions for one reconciliation target.
   */
  getPreview: async (
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<ReconciliationPreviewRow[]> => {
    return apiRequest<ReconciliationPreviewRow[]>({
      method: 'GET',
      url: `/projects/${projectName}/reconciliation/${entityName}/${targetField}/preview`,
    })
  },

  /**
   * Run candidate search without accepting any candidates.
   */
  autoReconcile: async (
    projectName: string,
    entityName: string,
    targetField: string,
    threshold: number,
    reviewThreshold?: number
  ): Promise<AutoReconcileResult> => {
    return apiRequest<AutoReconcileResult>({
      method: 'POST',
      url: `/projects/${projectName}/reconciliation/${entityName}/${targetField}/auto-reconcile-sync`,
      params: { threshold, review_threshold: reviewThreshold },
    })
  },

  /**
   * Save one explicit decision for a row's encoded business key.
   */
  updateDecision: async (
    projectName: string,
    entityName: string,
    targetField: string,
    request: DecisionUpdateRequest
  ): Promise<EntityResolutionCatalogResponse> => {
    return apiRequest<EntityResolutionCatalogResponse>({
      method: 'POST',
      url: `/projects/${projectName}/reconciliation/${entityName}/${targetField}/mapping`,
      data: request,
    })
  },

  /**
   * Delete one saved decision by encoded business key.
   */
  deleteDecision: async (
    projectName: string,
    entityName: string,
    targetField: string,
    localKeyValue: string
  ): Promise<EntityResolutionCatalogResponse> => {
    return apiRequest<EntityResolutionCatalogResponse>({
      method: 'DELETE',
      url: `/projects/${projectName}/reconciliation/${entityName}/${targetField}/mapping`,
      params: { local_key_value: localKeyValue },
    })
  },

  /**
   * Load mapping sidecar links for one entity.
   */
  getEntityMapping: async (projectName: string, entityName: string): Promise<MappingEntityResponse> => {
    return apiRequest<MappingEntityResponse>({
      method: 'GET',
      url: `/projects/${projectName}/mapping/${entityName}`,
    })
  },

  /**
   * Create or replace a manual mapping sidecar link for one encoded key.
   */
  putManualMapping: async (
    projectName: string,
    entityName: string,
    localKeyValue: string,
    request: MappingLinkUpsertRequest
  ): Promise<MappingLinkRecordResponse> => {
    return apiRequest<MappingLinkRecordResponse>({
      method: 'PUT',
      url: `/projects/${projectName}/mapping/${entityName}/${encodeURIComponent(localKeyValue)}`,
      data: request,
    })
  },

  /**
   * Search for target entities that may match the supplied label.
   */
  suggestEntities: async (
    projectName: string,
    entityName: string,
    targetField: string,
    query: string
  ): Promise<ReconciliationCandidate[]> => {
    return apiRequest<ReconciliationCandidate[]>({
      method: 'GET',
      url: `/projects/${projectName}/reconciliation/${entityName}/${targetField}/suggest`,
      params: { query },
    })
  },

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

  /**
   * Export reconciliation links for one entity field into the mapping sidecar
   */
  exportToMapping: async (
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<ExportToMappingResult> => {
    return apiRequest<ExportToMappingResult>({
      method: 'POST',
      url: `/projects/${projectName}/reconciliation/${entityName}/${targetField}/export-to-mapping`,
    })
  },
}
