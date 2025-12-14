/**
 * Centralized API exports
 */

export * from './client'
export * from './configurations'
export * from './entities'
export * from './validation'
export * from './data-sources'

// Convenience re-export of all API services
import { configurationsApi } from './configurations'
import { entitiesApi } from './entities'
import { validationApi } from './validation'
import { dataSourcesApi } from './data-sources'

export const api = {
  configurations: configurationsApi,
  entities: entitiesApi,
  validation: validationApi,
  dataSources: dataSourcesApi,
}
