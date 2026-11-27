import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const apiMocks = vi.hoisted(() => ({
  getMyPermissions: vi.fn(),
}))

vi.mock('@/api/permissions', () => ({ permissionsApi: apiMocks }))

import { usePermissionsStore } from '../permissions'

describe('permissions store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('denies log access until the backend allows it', () => {
    expect(usePermissionsStore().canReadLogs).toBe(false)
  })

  it.each([true, false])('uses the backend answer (%s) for log access', async (allowed) => {
    apiMocks.getMyPermissions.mockResolvedValue({ can_read_logs: allowed })
    const store = usePermissionsStore()

    await store.loadPermissions()

    expect(store.canReadLogs).toBe(allowed)
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('denies log access when the request fails', async () => {
    apiMocks.getMyPermissions.mockResolvedValueOnce({ can_read_logs: true }).mockRejectedValueOnce(new Error('offline'))
    const store = usePermissionsStore()
    await store.loadPermissions()

    await store.loadPermissions()

    expect(store.canReadLogs).toBe(false)
    expect(store.error).toBe('offline')
    expect(store.loading).toBe(false)
  })
})
