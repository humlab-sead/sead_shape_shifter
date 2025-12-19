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
   * List all global data source files
   */
  list: async (): Promise<DataSourceConfig[]> => {
    return apiRequest<DataSourceConfig[]>({
      method: 'GET',
      url: '/data-sources',
    })
  },

  /**
   * Get specific data source by filename
   */
  get: async (filename: string): Promise<DataSourceConfig> => {
    return apiRequest<DataSourceConfig>({
      method: 'GET',
      url: `/data-sources/${filename}`,
    })
  },

  /**
   * Create new global data source file
   */
  create: async (config: DataSourceConfig): Promise<DataSourceConfig> => {
    return apiRequest<DataSourceConfig>({
      method: 'POST',
      url: '/data-sources',
      data: config,
    })
  },

  /**
   * Update existing data source file
   */
  update: async (filename: string, config: DataSourceConfig): Promise<DataSourceConfig> => {
    return apiRequest<DataSourceConfig>({
      method: 'PUT',
      url: `/data-sources/${filename}`,
      data: config,
    })
  },

  /**
   * Delete data source file
   */
  delete: async (filename: string): Promise<void> => {
    return apiRequest<void>({
      method: 'DELETE',
      url: `/data-sources/${filename}`,
    })
  },

  /**
   * Test connection to data source
   */
  testConnection: async (filename: string): Promise<DataSourceTestResult> => {
    return apiRequest<DataSourceTestResult>({
      method: 'POST',
      url: `/data-sources/${filename}/test`,
    })
  },

  /**
   * Get data source status
   */
  getStatus: async (filename: string): Promise<DataSourceStatus> => {
    return apiRequest<DataSourceStatus>({
      method: 'GET',
      url: `/data-sources/${filename}/status`,
    })
  },
}
