import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEntityStore } from '../entity'
import type { EntityResponse, EntityCreateRequest, EntityUpdateRequest } from '@/api/entities'

// Mock the API module
vi.mock('@/api', () => ({
  api: {
    entities: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
  },
}))

import { api } from '@/api'

describe('useEntityStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should initialize with empty state', () => {
      const store = useEntityStore()

      expect(store.entities).toEqual([])
      expect(store.selectedEntity).toBeNull()
      expect(store.currentProjectName).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.hasUnsavedChanges).toBe(false)
    })
  })

  describe('computed getters', () => {
    it('should group entities by type', () => {
      const store = useEntityStore()
      store.entities = [
        { name: 'entity1', entity_data: { type: 'table' } } as EntityResponse,
        { name: 'entity2', entity_data: { type: 'view' } } as EntityResponse,
        { name: 'entity3', entity_data: { type: 'table' } } as EntityResponse,
      ]

      expect(store.entitiesByType).toEqual({
        table: [
          { name: 'entity1', entity_data: { type: 'table' } },
          { name: 'entity3', entity_data: { type: 'table' } },
        ],
        view: [{ name: 'entity2', entity_data: { type: 'view' } }],
      })
    })

    it('should handle entities without type', () => {
      const store = useEntityStore()
      store.entities = [{ name: 'entity1', entity_data: {} } as EntityResponse]

      expect(store.entitiesByType.unknown).toBeDefined()
      expect(store.entitiesByType.unknown).toHaveLength(1)
    })

    it('should compute entity count', () => {
      const store = useEntityStore()
      store.entities = [
        { name: 'entity1', entity_data: {} } as EntityResponse,
        { name: 'entity2', entity_data: {} } as EntityResponse,
      ]

      expect(store.entityCount).toBe(2)
    })

    it('should sort entities alphabetically', () => {
      const store = useEntityStore()
      store.entities = [
        { name: 'zebra', entity_data: {} } as EntityResponse,
        { name: 'alpha', entity_data: {} } as EntityResponse,
        { name: 'beta', entity_data: {} } as EntityResponse,
      ]

      expect(store.sortedEntities.map((e) => e.name)).toEqual(['alpha', 'beta', 'zebra'])
    })

    it('should find entity by name', () => {
      const store = useEntityStore()
      const entity = { name: 'test-entity', entity_data: {} } as EntityResponse
      store.entities = [entity]

      expect(store.entityByName('test-entity')).toEqual(entity)
      expect(store.entityByName('nonexistent')).toBeUndefined()
    })

    it('should filter root entities (no source)', () => {
      const store = useEntityStore()
      store.entities = [
        { name: 'root1', entity_data: {} } as EntityResponse,
        { name: 'child1', entity_data: { source: 'root1' } } as EntityResponse,
        { name: 'root2', entity_data: {} } as EntityResponse,
      ]

      expect(store.rootEntities).toHaveLength(2)
      expect(store.rootEntities.map((e) => e.name)).toEqual(['root1', 'root2'])
    })

    it('should find children of an entity', () => {
      const store = useEntityStore()
      store.entities = [
        { name: 'parent', entity_data: {} } as EntityResponse,
        { name: 'child1', entity_data: { source: 'parent' } } as EntityResponse,
        { name: 'child2', entity_data: { source: 'parent' } } as EntityResponse,
        { name: 'other', entity_data: {} } as EntityResponse,
      ]

      const children = store.childrenOf('parent')
      expect(children).toHaveLength(2)
      expect(children.map((e) => e.name)).toEqual(['child1', 'child2'])
    })

    it('should detect entities with foreign keys', () => {
      const store = useEntityStore()
      store.entities = [
        { name: 'withKeys', entity_data: { foreign_keys: [{ table: 'other', column: 'id' }] } } as EntityResponse,
        { name: 'withoutKeys', entity_data: {} } as EntityResponse,
      ]

      expect(store.hasForeignKeys('withKeys')).toBe(true)
      expect(store.hasForeignKeys('withoutKeys')).toBe(false)
      expect(store.hasForeignKeys('nonexistent')).toBe(false)
    })
  })

  describe('fetchEntities', () => {
    it('should fetch entities successfully', async () => {
      const store = useEntityStore()
      const mockEntities = [
        { name: 'entity1', entity_data: {} } as EntityResponse,
        { name: 'entity2', entity_data: {} } as EntityResponse,
      ]

      vi.mocked(api.entities.list).mockResolvedValue(mockEntities)

      await store.fetchEntities('test-project')

      expect(api.entities.list).toHaveBeenCalledWith('test-project')
      expect(store.entities).toEqual(mockEntities)
      expect(store.currentProjectName).toBe('test-project')
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should handle fetch errors', async () => {
      const store = useEntityStore()

      vi.mocked(api.entities.list).mockRejectedValue(new Error('Fetch failed'))

      await expect(store.fetchEntities('test-project')).rejects.toThrow('Fetch failed')

      expect(store.error).toBe('Fetch failed')
      expect(store.loading).toBe(false)
    })
  })

  describe('selectEntity', () => {
    it('should select an entity successfully', async () => {
      const store = useEntityStore()
      const mockEntity = { name: 'test-entity', entity_data: {} } as EntityResponse

      vi.mocked(api.entities.get).mockResolvedValue(mockEntity)

      const result = await store.selectEntity('test-project', 'test-entity')

      expect(api.entities.get).toHaveBeenCalledWith('test-project', 'test-entity')
      expect(store.selectedEntity).toEqual(mockEntity)
      expect(store.hasUnsavedChanges).toBe(false)
      expect(result).toEqual(mockEntity)
    })

    it('should handle select errors', async () => {
      const store = useEntityStore()

      vi.mocked(api.entities.get).mockRejectedValue(new Error('Not found'))

      await expect(store.selectEntity('test-project', 'nonexistent')).rejects.toThrow('Not found')

      expect(store.error).toBe('Not found')
    })
  })

  describe('createEntity', () => {
    it('should create an entity successfully', async () => {
      const store = useEntityStore()
      const createData: EntityCreateRequest = {
        name: 'new-entity',
        entity_data: { type: 'table' },
      }
      const mockEntity = { name: 'new-entity', entity_data: { type: 'table' } } as EntityResponse

      vi.mocked(api.entities.create).mockResolvedValue(mockEntity)

      const result = await store.createEntity('test-project', createData)

      expect(api.entities.create).toHaveBeenCalledWith('test-project', createData)
      expect(store.entities).toContainEqual(mockEntity)
      expect(store.selectedEntity).toEqual(mockEntity)
      expect(store.hasUnsavedChanges).toBe(false)
      expect(result).toEqual(mockEntity)
    })

    it('should handle create errors', async () => {
      const store = useEntityStore()
      const createData: EntityCreateRequest = {
        name: 'new-entity',
        entity_data: {},
      }

      vi.mocked(api.entities.create).mockRejectedValue(new Error('Create failed'))

      await expect(store.createEntity('test-project', createData)).rejects.toThrow('Create failed')

      expect(store.error).toBe('Create failed')
      expect(store.entities).toHaveLength(0)
    })
  })

  describe('updateEntity', () => {
    it('should update an entity successfully', async () => {
      const store = useEntityStore()
      const existing = { name: 'test-entity', entity_data: { type: 'table' } } as EntityResponse
      store.entities = [existing]

      const updateData: EntityUpdateRequest = {
        entity_data: { type: 'view', description: 'Updated' },
      }
      const updated = { name: 'test-entity', entity_data: { type: 'view', description: 'Updated' } } as EntityResponse

      vi.mocked(api.entities.update).mockResolvedValue(updated)

      const result = await store.updateEntity('test-project', 'test-entity', updateData)

      expect(api.entities.update).toHaveBeenCalledWith('test-project', 'test-entity', updateData)
      expect(store.entities[0]).toEqual(updated)
      expect(store.selectedEntity).toEqual(updated)
      expect(store.hasUnsavedChanges).toBe(false)
      expect(result).toEqual(updated)
    })

    it('should handle update errors', async () => {
      const store = useEntityStore()
      const updateData: EntityUpdateRequest = { entity_data: {} }

      vi.mocked(api.entities.update).mockRejectedValue(new Error('Update failed'))

      await expect(store.updateEntity('test-project', 'test-entity', updateData)).rejects.toThrow('Update failed')

      expect(store.error).toBe('Update failed')
    })
  })

  describe('deleteEntity', () => {
    it('should delete an entity successfully', async () => {
      const store = useEntityStore()
      const entity1 = { name: 'entity1', entity_data: {} } as EntityResponse
      const entity2 = { name: 'entity2', entity_data: {} } as EntityResponse
      store.entities = [entity1, entity2]
      store.selectedEntity = entity1

      vi.mocked(api.entities.delete).mockResolvedValue(undefined)

      await store.deleteEntity('test-project', 'entity1')

      expect(api.entities.delete).toHaveBeenCalledWith('test-project', 'entity1')
      expect(store.entities).toHaveLength(1)
      expect(store.entities[0]).toEqual(entity2)
      expect(store.selectedEntity).toBeNull()
    })

    it('should not clear selectedEntity if different entity deleted', async () => {
      const store = useEntityStore()
      const entity1 = { name: 'entity1', entity_data: {} } as EntityResponse
      const entity2 = { name: 'entity2', entity_data: {} } as EntityResponse
      store.entities = [entity1, entity2]
      store.selectedEntity = entity1

      vi.mocked(api.entities.delete).mockResolvedValue(undefined)

      await store.deleteEntity('test-project', 'entity2')

      expect(store.selectedEntity).toEqual(entity1)
    })

    it('should handle delete errors', async () => {
      const store = useEntityStore()

      vi.mocked(api.entities.delete).mockRejectedValue(new Error('Delete failed'))

      await expect(store.deleteEntity('test-project', 'test-entity')).rejects.toThrow('Delete failed')

      expect(store.error).toBe('Delete failed')
    })
  })

  describe('markAsChanged', () => {
    it('should mark as having unsaved changes', () => {
      const store = useEntityStore()

      expect(store.hasUnsavedChanges).toBe(false)

      store.markAsChanged()

      expect(store.hasUnsavedChanges).toBe(true)
    })
  })

  describe('clearError', () => {
    it('should clear error state', () => {
      const store = useEntityStore()
      store.error = 'Some error'

      store.clearError()

      expect(store.error).toBeNull()
    })
  })

  describe('reset', () => {
    it('should reset all state to initial values', () => {
      const store = useEntityStore()
      store.entities = [{ name: 'test', entity_data: {} } as EntityResponse]
      store.selectedEntity = { name: 'test', entity_data: {} } as EntityResponse
      store.currentProjectName = 'test-project'
      store.loading = true
      store.error = 'Some error'
      store.hasUnsavedChanges = true

      store.reset()

      expect(store.entities).toEqual([])
      expect(store.selectedEntity).toBeNull()
      expect(store.currentProjectName).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.hasUnsavedChanges).toBe(false)
    })
  })
})
