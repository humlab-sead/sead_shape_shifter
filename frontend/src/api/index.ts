/**
 * Centralized API exports
 */

export * from './client'
export * from './projects'
export * from './entities'
export * from './validation'
export * from './data-sources'
export * from './sessions'

// Convenience re-export of all API services
import { configurationsApi } from './projects'
import { entitiesApi } from './entities'
import { validationApi } from './validation'
import { dataSourcesApi } from './data-sources'
import { sessionsApi } from './sessions'

export const api = {
  configurations: configurationsApi,
  entities: entitiesApi,
  validation: validationApi,
  dataSources: dataSourcesApi,
  sessions: sessionsApi,
}
