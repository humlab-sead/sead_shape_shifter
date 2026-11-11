import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiClientMocks = vi.hoisted(() => ({
  get: vi.fn(),
}))

vi.mock('../client', () => ({
  apiClient: apiClientMocks,
}))

import { whatsNewApi } from '../whats-new'

describe('whatsNewApi', () => {
  beforeEach(() => {
    apiClientMocks.get.mockReset()
  })

  it('fetches the release manifest', async () => {
    const manifest = { latest_version: '2.5.0', items: [], pending_available: true }
    apiClientMocks.get.mockResolvedValue({ data: manifest })

    await expect(whatsNewApi.getManifest()).resolves.toEqual(manifest)
    expect(apiClientMocks.get).toHaveBeenCalledWith('/whats-new')
  })

  it('fetches versioned and pending notes as markdown text', async () => {
    apiClientMocks.get.mockResolvedValueOnce({ data: '# Release' }).mockResolvedValueOnce({ data: '# Pending' })

    await expect(whatsNewApi.getNote('2.5.0')).resolves.toBe('# Release')
    await expect(whatsNewApi.getPendingContent()).resolves.toBe('# Pending')

    expect(apiClientMocks.get).toHaveBeenNthCalledWith(1, '/whats-new/2.5.0/content', { responseType: 'text' })
    expect(apiClientMocks.get).toHaveBeenNthCalledWith(2, '/whats-new/pending', { responseType: 'text' })
  })
})
