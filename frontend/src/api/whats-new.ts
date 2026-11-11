import { apiClient } from './client'

export interface WhatsNewManifestItem {
  version: string
  title: string
  date: string | null
  path: string
}

export interface WhatsNewManifestResponse {
  latest_version: string | null
  items: WhatsNewManifestItem[]
  pending_available: boolean
}

export const whatsNewApi = {
  getManifest: async (): Promise<WhatsNewManifestResponse> => {
    const response = await apiClient.get<WhatsNewManifestResponse>('/whats-new')
    return response.data
  },

  getNote: async (version: string): Promise<string> => {
    const response = await apiClient.get<string>(`/whats-new/${version}/content`, { responseType: 'text' })
    return response.data
  },

  getPendingContent: async (): Promise<string> => {
    const response = await apiClient.get<string>('/whats-new/pending', { responseType: 'text' })
    return response.data
  },
}
