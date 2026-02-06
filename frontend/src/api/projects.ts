/**
 * API service for project management
 */

import type { CustomGraphLayout, Project, ProjectFileInfo, ProjectMetadata, ValidationResult } from '@/types'
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
   * Copy project to new name
   */
  copy: async (sourceName: string, targetName: string): Promise<Project> => {
    return apiRequest<Project>({
      method: 'POST',
      url: `/projects/${sourceName}/copy`,
      data: { target_name: targetName },
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
   * Returns a map of data source names to their configurations.
   * Configurations can be either:
   * - String references: "@include: filename.yml"
   * - Inline objects: {driver: "postgresql", options: {...}}
   */
  getDataSources: async (name: string): Promise<Record<string, string | Record<string, any>>> => {
    return apiRequest<Record<string, string | Record<string, any>>>({
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
   * List files available for a project (uploads directory)
   */
  listFiles: async (name: string, extensions?: string[]): Promise<ProjectFileInfo[]> => {
    return apiRequest<ProjectFileInfo[]>({
      method: 'GET',
      url: `/projects/${name}/files`,
      params: extensions && extensions.length > 0 ? { ext: extensions } : undefined,
    })
  },

  /**
   * Upload a file into the project's uploads directory
   */
  uploadFile: async (name: string, file: File): Promise<ProjectFileInfo> => {
    const formData = new FormData()
    formData.append('file', file)

    return apiRequest<ProjectFileInfo>({
      method: 'POST',
      url: `/projects/${name}/files`,
      data: formData,
      // Let axios set Content-Type header automatically for FormData
    })
  },

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
  },

  /**
   * Get custom graph layout for project
   */
  getLayout: async (name: string): Promise<{ layout: CustomGraphLayout; has_custom_layout: boolean }> => {
    return apiRequest<{ layout: CustomGraphLayout; has_custom_layout: boolean }>({
      method: 'GET',
      url: `/projects/${name}/layout`,
    })
  },

  /**
   * Save custom graph layout for project
   */
  saveLayout: async (name: string, layout: CustomGraphLayout): Promise<{ entities_positioned: number }> => {
    return apiRequest<{ entities_positioned: number }>({
      method: 'PUT',
      url: `/projects/${name}/layout`,
      data: { layout },
    })
  },

  /**
   * Clear custom graph layout for project
   */
  clearLayout: async (name: string): Promise<void> => {
    return apiRequest<void>({
      method: 'DELETE',
      url: `/projects/${name}/layout`,
    })
  },
}
