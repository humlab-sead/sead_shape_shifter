/**
 * API service for configuration management
 */

import type {
  Configuration,
  ConfigMetadata,
  ValidationResult,
} from '@/types'
import { apiRequest } from './client'

export interface ConfigurationCreateRequest {
  name: string
  entities?: Record<string, unknown>
}

export interface ConfigurationUpdateRequest {
  entities: Record<string, unknown>
  options: Record<string, unknown>
}

export interface BackupInfo {
  file_name: string
  file_path: string
  created_at: number
}

export interface RestoreBackupRequest {
  backup_path: string
}

/**
 * Configuration API service
 */
export const configurationsApi = {
  /**
   * List all configurations
   */
  list: async (): Promise<ConfigMetadata[]> => {
    return apiRequest<ConfigMetadata[]>({
      method: 'GET',
      url: '/configurations',
    })
  },

  /**
   * Get specific configuration
   */
  get: async (name: string): Promise<Configuration> => {
    return apiRequest<Configuration>({
      method: 'GET',
      url: `/configurations/${name}`,
    })
  },

  /**
   * Create new configuration
   */
  create: async (data: ConfigurationCreateRequest): Promise<Configuration> => {
    return apiRequest<Configuration>({
      method: 'POST',
      url: '/configurations',
      data,
    })
  },

  /**
   * Update configuration
   */
  update: async (
    name: string,
    data: ConfigurationUpdateRequest
  ): Promise<Configuration> => {
    return apiRequest<Configuration>({
      method: 'PUT',
      url: `/configurations/${name}`,
      data,
    })
  },

  /**
   * Delete configuration
   */
  delete: async (name: string): Promise<void> => {
    return apiRequest<void>({
      method: 'DELETE',
      url: `/configurations/${name}`,
    })
  },

  /**
   * Validate configuration
   */
  validate: async (name: string): Promise<ValidationResult> => {
    return apiRequest<ValidationResult>({
      method: 'POST',
      url: `/configurations/${name}/validate`,
    })
  },

  /**
   * List backups for configuration
   */
  listBackups: async (name: string): Promise<BackupInfo[]> => {
    return apiRequest<BackupInfo[]>({
      method: 'GET',
      url: `/configurations/${name}/backups`,
    })
  },

  /**
   * Restore configuration from backup
   */
  restore: async (
    name: string,
    data: RestoreBackupRequest
  ): Promise<Configuration> => {
    return apiRequest<Configuration>({
      method: 'POST',
      url: `/configurations/${name}/restore`,
      data,
    })
  },
}
