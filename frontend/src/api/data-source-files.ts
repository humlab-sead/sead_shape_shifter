/**
 * API service for global data source files management
 */

import type { ProjectFileInfo } from '@/types'
import { apiRequest } from './client'

/**
 * Data source files API service (global, not project-specific)
 */
export const dataSourceFilesApi = {
  /**
   * List files available for data sources
   */
  listFiles: async (extensions?: string[], projectName?: string): Promise<ProjectFileInfo[]> => {
    const params = new URLSearchParams()
    if (extensions && extensions.length > 0) {
      extensions.forEach((ext) => params.append('ext', ext))
    }
    if (projectName) {
      params.append('project_name', projectName)
    }

    const query = params.toString()
    const url = query ? `/data-sources/files?${query}` : '/data-sources/files'

    return apiRequest<ProjectFileInfo[]>({
      method: 'GET',
      url,
    })
  },

  /**
   * Upload a file for use in data source configurations
   */
  uploadFile: async (file: File): Promise<ProjectFileInfo> => {
    const formData = new FormData()
    formData.append('file', file)

    return apiRequest<ProjectFileInfo>({
      method: 'POST',
      url: '/data-sources/files',
      data: formData,
      headers: {
        'Content-Type': undefined, // Remove default header so axios sets multipart/form-data with boundary
      },
    })
  },
}
