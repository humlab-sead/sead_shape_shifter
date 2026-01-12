/**
 * API client for ingester operations
 */

import { apiClient } from './client'
import type {
  IngesterMetadata,
  ValidateRequest,
  ValidateResponse,
  IngestRequest,
  IngestResponse
} from '@/types/ingester'

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
    const response = await apiClient.post<ValidateResponse>(
      `/ingesters/${key}/validate`,
      request
    )
    return response.data
  },

  /**
   * Ingest data using specified ingester
   */
  async ingest(key: string, request: IngestRequest): Promise<IngestResponse> {
    const response = await apiClient.post<IngestResponse>(
      `/ingesters/${key}/ingest`,
      request
    )
    return response.data
  }
}
