import type { IntegrityTroubleshootRequest, IntegrityTroubleshootResponse } from '@/types'
import { apiRequest } from './client'

export const integrityTroubleshooterApi = {
  inspect: (projectName: string, request: IntegrityTroubleshootRequest): Promise<IntegrityTroubleshootResponse> =>
    apiRequest<IntegrityTroubleshootResponse>({
      method: 'POST',
      url: `/projects/${encodeURIComponent(projectName)}/integrity-troubleshooter`,
      data: request,
    }),
}
