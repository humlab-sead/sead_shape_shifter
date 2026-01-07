/**
 * API service for project management
 */

import type { Project, ProjectMetadata, ValidationResult } from '@/types'
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
export const projectsApi = {
  /**
   * List all projects
   */
  list: async (): Promise<ProjectMetadata[]> => {
    return apiRequest<ProjectMetadata[]>({
      method: 'GET',
      url: '/projects',
    })
  },

  /**
   * Get specific project
   */
  get: async (name: string): Promise<Project> => {
    return apiRequest<Project>({
      method: 'GET',
      url: `/projects/${name}`,
    })
  },

  /**
   * Create new project
   */
  create: async (data: ProjectCreateRequest): Promise<Project> => {
    return apiRequest<Project>({
      method: 'POST',
      url: '/projects',
      data,
    })
  },

  /**
   * Update project
   */
  update: async (name: string, data: ProjectUpdateRequest): Promise<Project> => {
    return apiRequest<Project>({
      method: 'PUT',
      url: `/projects/${name}`,
      data,
    })
  },

  /**
   * Update project metadata
   */
  updateMetadata: async (name: string, data: MetadataUpdateRequest): Promise<Project> => {
    return apiRequest<Project>({
      method: 'PATCH',
      url: `/projects/${name}/metadata`,
      data,
    })
  },

  /**
   * Delete project
   */
  delete: async (name: string): Promise<void> => {
    return apiRequest<void>({
      method: 'DELETE',
      url: `/projects/${name}`,
    })
  },

  /**
   * Validate project
   */
  validate: async (name: string): Promise<ValidationResult> => {
    return apiRequest<ValidationResult>({
      method: 'POST',
      url: `/projects/${name}/validate`,
    })
  },

  /**
   * List backups for project
   */
  listBackups: async (name: string): Promise<BackupInfo[]> => {
    return apiRequest<BackupInfo[]>({
      method: 'GET',
      url: `/projects/${name}/backups`,
    })
  },

  /**
   * Restore project from backup
   */
  restore: async (name: string, data: RestoreBackupRequest): Promise<Project> => {
    return apiRequest<Project>({
      method: 'POST',
      url: `/projects/${name}/restore`,
      data,
    })
  },

  /**
   * Get currently active project name
   */
  getActive: async (): Promise<{ name: string | null }> => {
    return apiRequest<{ name: string | null }>({
      method: 'GET',
      url: '/projects/active/name',
    })
  },

  /**
   * Activate (load) a project
   */
  activate: async (name: string): Promise<Project> => {
    return apiRequest<Project>({
      method: 'POST',
      url: `/projects/${name}/activate`,
    })
  },

  /**
   * Get data sources connected to a project
   */
  getDataSources: async (name: string): Promise<Record<string, string>> => {
    return apiRequest<Record<string, string>>({
      method: 'GET',
      url: `/projects/${name}/data-sources`,
    })
  },

  /**
   * Connect a data source to a project
   */
  connectDataSource: async (name: string, sourceName: string, sourceFilename: string): Promise<Project> => {
    return apiRequest<Project>({
      method: 'POST',
      url: `/projects/${name}/data-sources`,
      data: {
        source_name: sourceName,
        source_filename: sourceFilename,
      },
    })
  },

  /**
   * Disconnect a data source from a project
   */
  disconnectDataSource: async (name: string, sourceName: string): Promise<Project> => {
    return apiRequest<Project>({
      method: 'DELETE',
      url: `/projects/${name}/data-sources/${sourceName}`,
    })
  },
  /**
   * Get raw YAML content
   */
  getRawYaml: async (name: string): Promise<{ yaml_content: string }> => {
    return apiRequest<{ yaml_content: string }>({
      method: 'GET',
      url: `/projects/${name}/raw-yaml`,
    })
  },

  /**
   * Update project with raw YAML content
   */
  updateRawYaml: async (name: string, yamlContent: string): Promise<Project> => {
    return apiRequest<Project>({
      method: 'PUT',
      url: `/projects/${name}/raw-yaml`,
      data: { yaml_content: yamlContent },
    })
  },}
