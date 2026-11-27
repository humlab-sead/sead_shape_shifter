import { beforeEach, describe, expect, it, vi } from 'vitest'

const clientMocks = vi.hoisted(() => ({
  apiRequest: vi.fn(),
}))

vi.mock('../client', () => clientMocks)

import { permissionsApi } from '../permissions'

describe('permissionsApi', () => {
  beforeEach(() => {
    clientMocks.apiRequest.mockReset()
  })

  it('fetches what the current user may do', async () => {
    clientMocks.apiRequest.mockResolvedValue({ can_read_logs: true })

    await expect(permissionsApi.getMyPermissions()).resolves.toEqual({ can_read_logs: true })
    expect(clientMocks.apiRequest).toHaveBeenCalledWith({ method: 'GET', url: '/me/permissions' })
  })
})
