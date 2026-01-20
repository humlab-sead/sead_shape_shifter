/**
 * Centralized API exports
 */

export * from './client'
export * from './projects'
export * from './entities'
export * from './validation'
export * from './data-sources'
export * from './data-source-files'
export * from './sessions'
export * from './reconciliation'
export * from './tasks'

// Convenience re-export of all API services
import { projectsApi } from './projects'
import { entitiesApi } from './entities'
import { validationApi } from './validation'
import { dataSourcesApi } from './data-sources'
import { dataSourceFilesApi } from './data-source-files'
import { sessionsApi } from './sessions'
import { reconciliationSpecApi } from './reconciliation'
import { tasksApi } from './tasks'

export const api = {
  projects: projectsApi,
  entities: entitiesApi,
  validation: validationApi,
  dataSources: dataSourcesApi,
  dataSourceFiles: dataSourceFilesApi,
  sessions: sessionsApi,
  reconciliationSpec: reconciliationSpecApi,
  tasks: tasksApi,
}
