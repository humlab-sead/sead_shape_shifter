import { beforeEach, describe, expect, it, vi } from 'vitest'
import { dataProvidersApi, type DataProvider } from '../data-providers'

vi.mock('../client', () => ({
  apiRequest: vi.fn(),
}))

import { apiRequest } from '../client'

describe('dataProvidersApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads registered providers and schemas from the read-only endpoint', async () => {
    const providers: DataProvider[] = [
      {
        code: 'test-provider',
        name: 'Test Provider',
        schemas: [
          { provider_schema: 'schema-one', scope_name: 'provider://test-provider/schema-one' },
          { provider_schema: 'schema-two', scope_name: 'provider://test-provider/schema-two' },
        ],
      },
    ]
    vi.mocked(apiRequest).mockResolvedValue(providers)

    await expect(dataProvidersApi.list()).resolves.toEqual(providers)
    expect(apiRequest).toHaveBeenCalledWith({ method: 'GET', url: '/data-providers' })
  })
})
