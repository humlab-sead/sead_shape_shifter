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
  validateEntity: async (
    configName: string,
    entityName: string
  ): Promise<ValidationResult> => {
    return apiRequest<ValidationResult>({
      method: 'POST',
      url: `/configurations/${configName}/entities/${entityName}/validate`,
    })
  },

  /**
   * Get dependency graph for configuration
   */
  getDependencies: async (configName: string): Promise<DependencyGraph> => {
    return apiRequest<DependencyGraph>({
      method: 'GET',
      url: `/configurations/${configName}/dependencies`,
    })
  },

  /**
   * Check for circular dependencies
   */
  checkCircularDependencies: async (
    configName: string
  ): Promise<CircularDependencyCheck> => {
    return apiRequest<CircularDependencyCheck>({
      method: 'POST',
      url: `/configurations/${configName}/dependencies/check`,
    })
  },
}
