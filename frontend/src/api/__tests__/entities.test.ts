/**
 * Unit tests for entities API service
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { entitiesApi } from '../entities'
import type { EntityResponse, EntityCreateRequest, EntityUpdateRequest } from '../entities'

// Mock the API client
vi.mock('../client', () => ({
  apiRequest: vi.fn(),
}))

import { apiRequest } from '../client'

describe('entitiesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('should fetch all entities for a project', async () => {
      const mockEntities: EntityResponse[] = [
        { name: 'entity1', entity_data: { field: 'value1' } },
        { name: 'entity2', entity_data: { field: 'value2' } },
      ]

      vi.mocked(apiRequest).mockResolvedValue(mockEntities)

      const result = await entitiesApi.list('test-project')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects/test-project/entities',
      })
      expect(result).toEqual(mockEntities)
    })

    it('should handle empty entity list', async () => {
      vi.mocked(apiRequest).mockResolvedValue([])

      const result = await entitiesApi.list('empty-config')

      expect(result).toEqual([])
    })
  })

  describe('get', () => {
    it('should fetch a specific entity', async () => {
      const mockEntity: EntityResponse = {
        name: 'test-entity',
        entity_data: { table: 'users', columns: ['id', 'name'] },
      }

      vi.mocked(apiRequest).mockResolvedValue(mockEntity)

      const result = await entitiesApi.get('test-project', 'test-entity')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects/test-project/entities/test-entity',
      })
      expect(result).toEqual(mockEntity)
    })

    it('should handle entity names with special characters', async () => {
      const mockEntity: EntityResponse = {
        name: 'entity-with-dash',
        entity_data: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockEntity)

      await entitiesApi.get('config-1', 'entity-with-dash')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects/config-1/entities/entity-with-dash',
      })
    })
  })

  describe('create', () => {
    it('should create a new entity', async () => {
      const createRequest: EntityCreateRequest = {
        name: 'new-entity',
        entity_data: {
          table: 'products',
          columns: ['id', 'name', 'price'],
        },
      }

      const mockResponse: EntityResponse = {
        name: 'new-entity',
        entity_data: createRequest.entity_data,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await entitiesApi.create('test-project', createRequest)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/entities',
        data: createRequest,
      })
      expect(result).toEqual(mockResponse)
    })

    it('should create entity with empty entity_data', async () => {
      const createRequest: EntityCreateRequest = {
        name: 'minimal-entity',
        entity_data: {},
      }

      vi.mocked(apiRequest).mockResolvedValue({
        name: 'minimal-entity',
        entity_data: {},
      })

      await entitiesApi.create('test-project', createRequest)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/entities',
        data: createRequest,
      })
    })
  })

  describe('update', () => {
    it('should update an existing entity', async () => {
      const updateRequest: EntityUpdateRequest = {
        entity_data: {
          table: 'users',
          columns: ['id', 'name', 'email'],
          foreign_keys: [],
        },
      }

      const mockResponse: EntityResponse = {
        name: 'test-entity',
        entity_data: updateRequest.entity_data,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await entitiesApi.update('test-project', 'test-entity', updateRequest)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'PUT',
        url: '/projects/test-project/entities/test-entity',
        data: updateRequest,
      })
      expect(result).toEqual(mockResponse)
    })

    it('should update entity with complex nested data', async () => {
      const updateRequest: EntityUpdateRequest = {
        entity_data: {
          table: 'orders',
          foreign_keys: [
            {
              entity: 'customers',
              local_keys: ['customer_id'],
              remote_keys: ['id'],
            },
          ],
          mapping: { order_id: 'id', customer_ref: 'customer_id' },
        },
      }

      vi.mocked(apiRequest).mockResolvedValue({
        name: 'orders',
        entity_data: updateRequest.entity_data,
      })

      await entitiesApi.update('test-project', 'orders', updateRequest)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'PUT',
        url: '/projects/test-project/entities/orders',
        data: updateRequest,
      })
    })
  })

  describe('delete', () => {
    it('should delete an entity', async () => {
      vi.mocked(apiRequest).mockResolvedValue(undefined)

      await entitiesApi.delete('test-project', 'test-entity')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'DELETE',
        url: '/projects/test-project/entities/test-entity',
      })
    })

    it('should handle deletion of non-existent entity', async () => {
      vi.mocked(apiRequest).mockRejectedValue(new Error('Entity not found'))

      await expect(entitiesApi.delete('test-project', 'non-existent')).rejects.toThrow(
        'Entity not found'
      )
    })
  })

  describe('error handling', () => {
    it('should propagate API errors from list', async () => {
      const error = new Error('Network error')
      vi.mocked(apiRequest).mockRejectedValue(error)

      await expect(entitiesApi.list('test-project')).rejects.toThrow('Network error')
    })

    it('should propagate API errors from get', async () => {
      const error = new Error('Entity not found')
      vi.mocked(apiRequest).mockRejectedValue(error)

      await expect(entitiesApi.get('test-project', 'missing')).rejects.toThrow('Entity not found')
    })

    it('should propagate API errors from create', async () => {
      const error = new Error('Validation failed')
      vi.mocked(apiRequest).mockRejectedValue(error)

      const request: EntityCreateRequest = {
        name: 'invalid',
        entity_data: {},
      }

      await expect(entitiesApi.create('test-project', request)).rejects.toThrow('Validation failed')
    })

    it('should propagate API errors from update', async () => {
      const error = new Error('Update conflict')
      vi.mocked(apiRequest).mockRejectedValue(error)

      const request: EntityUpdateRequest = {
        entity_data: {},
      }

      await expect(entitiesApi.update('test-project', 'entity', request)).rejects.toThrow(
        'Update conflict'
      )
    })
  })
})
