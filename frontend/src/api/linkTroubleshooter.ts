import type {
  LinkExceptionRowsPage,
  LinkExceptionRowsRequest,
  LinkExperimentContextRequest,
  LinkExperimentContextResponse,
  LinkExperimentTrialRequest,
  LinkExperimentTrialResponse,
} from '@/types'
import { apiRequest } from './client'

function contextUrl(projectName: string, contextId?: string): string {
  const base = `/projects/${encodeURIComponent(projectName)}/link-experiment-contexts`
  return contextId === undefined ? base : `${base}/${encodeURIComponent(contextId)}`
}

export const linkTroubleshooterApi = {
  open: (projectName: string, request: LinkExperimentContextRequest): Promise<LinkExperimentContextResponse> =>
    apiRequest<LinkExperimentContextResponse>({
      method: 'POST',
      url: contextUrl(projectName),
      data: request,
    }),

  trial: (
    projectName: string,
    contextId: string,
    request: LinkExperimentTrialRequest
  ): Promise<LinkExperimentTrialResponse> =>
    apiRequest<LinkExperimentTrialResponse>({
      method: 'POST',
      url: `${contextUrl(projectName, contextId)}/trials`,
      data: request,
    }),

  exceptionRows: (
    projectName: string,
    contextId: string,
    request: LinkExceptionRowsRequest
  ): Promise<LinkExceptionRowsPage> =>
    apiRequest<LinkExceptionRowsPage>({
      method: 'POST',
      url: `${contextUrl(projectName, contextId)}/exception-rows`,
      data: request,
    }),

  close: (projectName: string, contextId: string): Promise<void> =>
    apiRequest<void>({
      method: 'DELETE',
      url: contextUrl(projectName, contextId),
    }),
}
