/**
 * API service for configuration management
 */

import type {
  Project,
  ConfigMetadata,
  ValidationResult,
} from '@/types'
import { apiRequest } from './client'

export interface ProjectCreateRequest {
  name: string
  entities?: Record<string, unknown>
}

export interface ProjectUpdateRequest {
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

export interface MetadataUpdateRequest {
  name?: string | null
  description?: string | null
  version?: string | null
  default_entity?: string | null
}

/**
 * Project API service
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
  get: async (name: string): Promise<Project> => {
    return apiRequest<Project>({
      method: 'GET',
      url: `/configurations/${name}`,
    })
  },

  /**
   * Create new configuration
   */
  create: async (data: ProjectCreateRequest): Promise<Project> => {
    return apiRequest<Project>({
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
    data: ProjectUpdateRequest
  ): Promise<Project> => {
    return apiRequest<Project>({
      method: 'PUT',
      url: `/configurations/${name}`,
      data,
    })
  },

  /**
   * Update configuration metadata
   */
  updateMetadata: async (
    name: string,
    data: MetadataUpdateRequest
  ): Promise<Project> => {
    return apiRequest<Project>({
      method: 'PATCH',
      url: `/configurations/${name}/metadata`,
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
  ): Promise<Project> => {
    return apiRequest<Project>({
      method: 'POST',
      url: `/configurations/${name}/restore`,
      data,
    })
  },

  /**
   * Get currently active configuration name
   */
  getActive: async (): Promise<{ name: string | null }> => {
    return apiRequest<{ name: string | null }>({
      method: 'GET',
      url: '/configurations/active/name',
    })
  },

  /**
   * Activate (load) a configuration
   */
  activate: async (name: string): Promise<Project> => {
    return apiRequest<Project>({
      method: 'POST',
      url: `/configurations/${name}/activate`,
    })
  },

  /**
   * Get data sources connected to a configuration
   */
  getDataSources: async (name: string): Promise<Record<string, string>> => {
    return apiRequest<Record<string, string>>({
      method: 'GET',
      url: `/configurations/${name}/data-sources`,
    })
  },

  /**
   * Connect a data source to a configuration
   */
  connectDataSource: async (
    name: string,
    sourceName: string,
    sourceFilename: string
  ): Promise<Project> => {
    return apiRequest<Project>({
      method: 'POST',
      url: `/configurations/${name}/data-sources`,
      data: {
        source_name: sourceName,
        source_filename: sourceFilename,
      },
    })
  },

  /**
   * Disconnect a data source from a configuration
   */
  disconnectDataSource: async (
    name: string,
    sourceName: string
  ): Promise<Project> => {
    return apiRequest<Project>({
      method: 'DELETE',
      url: `/configurations/${name}/data-sources/${sourceName}`,
    })
  },
}
