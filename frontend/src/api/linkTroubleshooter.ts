import type { LinkTroubleshootRequest, LinkTroubleshootResponse } from '@/types'
import { apiRequest } from './client'

export const linkTroubleshooterApi = {
  run: (projectName: string, request: LinkTroubleshootRequest): Promise<LinkTroubleshootResponse> =>
    apiRequest<LinkTroubleshootResponse>({
      method: 'POST',
      url: `/projects/${encodeURIComponent(projectName)}/link-troubleshooter`,
      data: request,
    }),
}
