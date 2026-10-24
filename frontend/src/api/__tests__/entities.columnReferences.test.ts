import { beforeEach, describe, expect, it, vi } from 'vitest'
import { entitiesApi } from '../entities'
import type {
  ColumnReferenceCompleteRequest,
  ColumnReferenceResolveRequest,
  ColumnReferenceResolveResponse,
} from '../entities'

vi.mock('../client', () => ({
  apiRequest: vi.fn(),
}))

import { apiRequest } from '../client'

describe('entity column reference API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('posts typed completion requests with the current draft and field context', async () => {
    const request: ColumnReferenceCompleteRequest = {
      entity_draft: { columns: ['sample_name'] },
      prefix: '@value: entities.site.k',
      edited_field_path: 'entities.sample.keys',
      preferred_entity: 'site',
    }
    const response = { candidates: ['@value: entities.site.keys'] }
    vi.mocked(apiRequest).mockResolvedValue(response)

    await expect(entitiesApi.completeColumnReferences('demo', 'sample', request)).resolves.toEqual(response)
    expect(apiRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/projects/demo/entities/sample/column-references/complete',
      data: request,
    })
  })

  it('preserves typed unresolved responses from the resolve route', async () => {
    const request: ColumnReferenceResolveRequest = {
      entity_draft: { columns: ['sample_name'] },
      directive: '@value: entities.site.keys',
    }
    const response: ColumnReferenceResolveResponse = {
      directive: request.directive,
      path: 'entities.site.keys',
      status: 'unresolved',
      reason_code: 'dependency_failure',
      reason: 'A file or nested directive required by this reference could not be resolved.',
    }
    vi.mocked(apiRequest).mockResolvedValue(response)

    await expect(entitiesApi.resolveColumnReference('demo', 'sample', request)).resolves.toEqual(response)
    expect(apiRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/projects/demo/entities/sample/column-references/resolve',
      data: request,
    })
  })
})
