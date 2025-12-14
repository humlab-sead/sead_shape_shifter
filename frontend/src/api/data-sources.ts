/**
 * API service for data source management
 */

import { apiRequest } from './client'
import type {
  DataSourceConfig,
  DataSourceTestResult,
  DataSourceStatus,
} from '@/types/data-source'

/**
 * Data Source API service
 */
export const dataSourcesApi = {
  /**
   * List all data sources
   */
  list: async (): Promise<DataSourceConfig[]> => {
    return apiRequest<DataSourceConfig[]>({
      method: 'GET',
      url: '/data-sources',
    })
  },

  /**
   * Get specific data source
   */
  get: async (name: string): Promise<DataSourceConfig> => {
    return apiRequest<DataSourceConfig>({
      method: 'GET',
      url: `/data-sources/${name}`,
    })
  },

  /**
   * Create new data source
   */
  create: async (config: DataSourceConfig): Promise<DataSourceConfig> => {
    return apiRequest<DataSourceConfig>({
      method: 'POST',
      url: '/data-sources',
      data: config,
    })
  },

  /**
   * Update existing data source
   */
  update: async (name: string, config: DataSourceConfig): Promise<DataSourceConfig> => {
    return apiRequest<DataSourceConfig>({
      method: 'PUT',
      url: `/data-sources/${name}`,
      data: config,
    })
  },

  /**
   * Delete data source
   */
  delete: async (name: string): Promise<void> => {
    return apiRequest<void>({
      method: 'DELETE',
      url: `/data-sources/${name}`,
    })
  },

  /**
   * Test connection to data source
   */
  testConnection: async (name: string): Promise<DataSourceTestResult> => {
    return apiRequest<DataSourceTestResult>({
      method: 'POST',
      url: `/data-sources/${name}/test`,
    })
  },

  /**
   * Get data source status
   */
  getStatus: async (name: string): Promise<DataSourceStatus> => {
    return apiRequest<DataSourceStatus>({
      method: 'GET',
      url: `/data-sources/${name}/status`,
    })
  },
}
