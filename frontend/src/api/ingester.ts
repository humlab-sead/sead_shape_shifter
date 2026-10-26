/**
 * API client for ingester operations
 */

import { apiClient } from './client'
import type {
  IngesterMetadata,
  ValidateRequest,
  ValidateResponse,
  IngestRequest,
  IngestResponse,
  ProjectIngesterRequest,
} from '@/types/ingester'

const projectChangeRequestPath = '/ingesters/sead_change_request/from-project'

export const ingesterApi = {
  /**
   * List all available ingesters
   */
  async listIngesters(): Promise<IngesterMetadata[]> {
    const response = await apiClient.get<IngesterMetadata[]>('/ingesters')
    return response.data
  },

  /**
   * Validate data using specified ingester
   */
  async validate(key: string, request: ValidateRequest): Promise<ValidateResponse> {
    const response = await apiClient.post<ValidateResponse>(`/ingesters/${key}/validate`, request)
    return response.data
  },

  /**
   * Ingest data using specified ingester
   */
  async ingest(key: string, request: IngestRequest): Promise<IngestResponse> {
    const response = await apiClient.post<IngestResponse>(`/ingesters/${key}/ingest`, request)
    return response.data
  },

  /**
   * Validate normalized tables from a saved project for a Change Request
   */
  async validateProject(request: ProjectIngesterRequest): Promise<ValidateResponse> {
    const response = await apiClient.post<ValidateResponse>(`${projectChangeRequestPath}/validate`, request)
    return response.data
  },

  /**
   * Generate a Change Request from normalized tables in a saved project
   */
  async ingestProject(request: ProjectIngesterRequest): Promise<IngestResponse> {
    const response = await apiClient.post<IngestResponse>(`${projectChangeRequestPath}/ingest`, request)
    return response.data
  },
}
