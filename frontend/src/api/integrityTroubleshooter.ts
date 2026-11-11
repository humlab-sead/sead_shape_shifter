import type {
  IntegrityTroubleshootPageRequest,
  IntegrityTroubleshootRequest,
  IntegrityTroubleshootResponse,
} from '@/types'
import { apiRequest } from './client'

function contextUrl(projectName: string, contextId?: string): string {
  const base = `/projects/${encodeURIComponent(projectName)}/integrity-troubleshooter`
  return contextId === undefined ? base : `${base}/${encodeURIComponent(contextId)}`
}

export const integrityTroubleshooterApi = {
  inspect: (projectName: string, request: IntegrityTroubleshootRequest): Promise<IntegrityTroubleshootResponse> =>
    apiRequest<IntegrityTroubleshootResponse>({
      method: 'POST',
      url: contextUrl(projectName),
      data: request,
    }),

  page: (
    projectName: string,
    contextId: string,
    request: IntegrityTroubleshootPageRequest
  ): Promise<IntegrityTroubleshootResponse> =>
    apiRequest<IntegrityTroubleshootResponse>({
      method: 'POST',
      url: `${contextUrl(projectName, contextId)}/page`,
      data: request,
    }),

  close: (projectName: string, contextId: string): Promise<void> =>
    apiRequest<void>({
      method: 'DELETE',
      url: contextUrl(projectName, contextId),
    }),
}
