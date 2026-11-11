/**
 * Centralized API exports
 */

export * from './client'
export * from './projects'
export * from './entities'
export * from './validation'
export * from './linkTroubleshooter'
export * from './integrityTroubleshooter'
export * from './data-sources'
export * from './data-providers'
export * from './data-source-files'
export * from './sessions'
export * from './reconciliation'
export * from './excel-metadata'
export * from './tasks'
export * from './logs'
export * from './health'
export * from './whats-new'

// Convenience re-export of all API services
import { projectsApi } from './projects'
import { entitiesApi } from './entities'
import { validationApi } from './validation'
import { linkTroubleshooterApi } from './linkTroubleshooter'
import { integrityTroubleshooterApi } from './integrityTroubleshooter'
import { dataSourcesApi } from './data-sources'
import { dataProvidersApi } from './data-providers'
import { dataSourceFilesApi } from './data-source-files'
import { sessionsApi } from './sessions'
import { reconciliationSpecApi } from './reconciliation'
import { excelMetadataApi } from './excel-metadata'
import { tasksApi } from './tasks'
import { logsApi } from './logs'
import { healthApi } from './health'
import { whatsNewApi } from './whats-new'

export const api = {
  projects: projectsApi,
  entities: entitiesApi,
  validation: validationApi,
  linkTroubleshooter: linkTroubleshooterApi,
  integrityTroubleshooter: integrityTroubleshooterApi,
  dataSources: dataSourcesApi,
  dataProviders: dataProvidersApi,
  dataSourceFiles: dataSourceFilesApi,
  sessions: sessionsApi,
  reconciliationSpec: reconciliationSpecApi,
  excelMetadata: excelMetadataApi,
  tasks: tasksApi,
  logs: logsApi,
  health: healthApi,
  whatsNew: whatsNewApi,
}
