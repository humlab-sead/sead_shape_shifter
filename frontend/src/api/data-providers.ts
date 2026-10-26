/**
 * API service for curated data providers and their registered schemas.
 */

import { apiRequest } from './client'

export interface DataProviderSchema {
  provider_schema: string
  scope_name: string
}

export interface DataProvider {
  code: string
  name: string
  schemas: DataProviderSchema[]
}

export const dataProvidersApi = {
  list: async (): Promise<DataProvider[]> => {
    return apiRequest<DataProvider[]>({
      method: 'GET',
      url: '/data-providers',
    })
  },
}
