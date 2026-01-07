/**
 * API service for validation and dependency analysis
 */

import type { ValidationResult, DependencyGraph, CircularDependencyCheck } from '@/types'
import { apiRequest } from './client'

/**
 * Validation and dependency API service
 */
export const validationApi = {
  /**
   * Validate specific entity
   */
  validateEntity: async (projectName: string, entityName: string): Promise<ValidationResult> => {
    return apiRequest<ValidationResult>({
      method: 'POST',
      url: `/projects/${projectName}/entities/${entityName}/validate`,
    })
  },

  /**
   * Get dependency graph for project
   */
  getDependencies: async (projectName: string): Promise<DependencyGraph> => {
    return apiRequest<DependencyGraph>({
      method: 'GET',
      url: `/projects/${projectName}/dependencies`,
    })
  },

  /**
   * Check for circular dependencies
   */
  checkCircularDependencies: async (projectName: string): Promise<CircularDependencyCheck> => {
    return apiRequest<CircularDependencyCheck>({
      method: 'POST',
      url: `/projects/${projectName}/dependencies/check`,
    })
  },
}
