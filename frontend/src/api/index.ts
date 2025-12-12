/**
 * Centralized API exports
 */

export * from './client'
export * from './configurations'
export * from './entities'
export * from './validation'

// Convenience re-export of all API services
import { configurationsApi } from './configurations'
import { entitiesApi } from './entities'
import { validationApi } from './validation'

export const api = {
  configurations: configurationsApi,
  entities: entitiesApi,
  validation: validationApi,
}
