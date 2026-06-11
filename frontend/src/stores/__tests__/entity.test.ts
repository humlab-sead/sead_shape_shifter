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

function makeEntity(
  name: string,
  entity_data: Record<string, unknown> = {},
  overrides: Partial<EntityResponse> = {},
): EntityResponse {
  return {
    name,
    entity_data,
    etag: `${name}-etag`,
    ...overrides,
  }
}

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
        makeEntity('entity1', { type: 'table' }),
        makeEntity('entity2', { type: 'view' }),
        makeEntity('entity3', { type: 'table' }),
      ]

      expect(store.entitiesByType).toEqual({
        table: [
          makeEntity('entity1', { type: 'table' }),
          makeEntity('entity3', { type: 'table' }),
        ],
        view: [makeEntity('entity2', { type: 'view' })],
      })
    })

    it('should handle entities without type', () => {
      const store = useEntityStore()
      store.entities = [makeEntity('entity1')]

      expect(store.entitiesByType.unknown).toBeDefined()
      expect(store.entitiesByType.unknown).toHaveLength(1)
    })

    it('should compute entity count', () => {
      const store = useEntityStore()
      store.entities = [
        makeEntity('entity1'),
        makeEntity('entity2'),
      ]

      expect(store.entityCount).toBe(2)
    })

    it('should sort entities alphabetically', () => {
      const store = useEntityStore()
      store.entities = [
        makeEntity('zebra'),
        makeEntity('alpha'),
        makeEntity('beta'),
      ]

      expect(store.sortedEntities.map((e) => e.name)).toEqual(['alpha', 'beta', 'zebra'])
    })

    it('should find entity by name', () => {
      const store = useEntityStore()
      const entity = makeEntity('test-entity')
      store.entities = [entity]

      expect(store.entityByName('test-entity')).toEqual(entity)
      expect(store.entityByName('nonexistent')).toBeUndefined()
    })

    it('should filter root entities (no source)', () => {
      const store = useEntityStore()
      store.entities = [
        makeEntity('root1'),
        makeEntity('child1', { source: 'root1' }),
        makeEntity('root2'),
      ]

      expect(store.rootEntities).toHaveLength(2)
      expect(store.rootEntities.map((e) => e.name)).toEqual(['root1', 'root2'])
    })

    it('should find children of an entity', () => {
      const store = useEntityStore()
      store.entities = [
        makeEntity('parent'),
        makeEntity('child1', { source: 'parent' }),
        makeEntity('child2', { source: 'parent' }),
        makeEntity('other'),
      ]

      const children = store.childrenOf('parent')
      expect(children).toHaveLength(2)
      expect(children.map((e) => e.name)).toEqual(['child1', 'child2'])
    })

    it('should detect entities with foreign keys', () => {
      const store = useEntityStore()
      store.entities = [
        makeEntity('withKeys', { foreign_keys: [{ table: 'other', column: 'id' }] }),
        makeEntity('withoutKeys'),
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
        makeEntity('entity1'),
        makeEntity('entity2'),
      ]

      vi.mocked(api.entities.list).mockResolvedValue(mockEntities)

      await store.fetchEntities('test-project')

      expect(api.entities.list).toHaveBeenCalledWith('test-project')
      expect(store.entities).toEqual(mockEntities)
      expect(store.currentProjectName).toBe('test-project')
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should resync selectedEntity to refreshed entity data', async () => {
      const store = useEntityStore()
      store.entities = [makeEntity('test-entity', {}, { etag: 'stale-etag' })]
      store.selectedEntity = makeEntity('test-entity', {}, { etag: 'stale-etag' })

      const refreshedEntity = makeEntity('test-entity', {}, { etag: 'fresh-etag' })
      vi.mocked(api.entities.list).mockResolvedValue([refreshedEntity])

      await store.fetchEntities('test-project')

      expect(store.selectedEntity).toEqual(refreshedEntity)
    })

    it('should handle fetch errors', async () => {
      const store = useEntityStore()

      vi.mocked(api.entities.list).mockRejectedValue(new Error('Fetch failed'))

      await expect(store.fetchEntities('test-project')).rejects.toThrow('Fetch failed')

      expect(store.error).toBe('Fetch failed')
      expect(store.loading).toBe(false)
    })
  })

  describe('syncCachedEntity', () => {
    it('should replace a cached entity and keep selectedEntity in sync', () => {
      const store = useEntityStore()
      store.entities = [makeEntity('test-entity', { type: 'sql' }, { etag: 'stale-etag' })]
      store.selectedEntity = makeEntity('test-entity', { type: 'sql' }, { etag: 'stale-etag' })

      const refreshedEntity = makeEntity('test-entity', { type: 'fixed' }, { etag: 'fresh-etag' })

      store.syncCachedEntity(refreshedEntity)

      expect(store.entities).toEqual([refreshedEntity])
      expect(store.selectedEntity).toEqual(refreshedEntity)
    })

    it('should cache a missing entity', () => {
      const store = useEntityStore()
      const refreshedEntity = makeEntity('new-entity', { type: 'sql' }, { etag: 'fresh-etag' })

      store.syncCachedEntity(refreshedEntity)

      expect(store.entities).toEqual([refreshedEntity])
    })
  })

  describe('selectEntity', () => {
    it('should select an entity successfully', async () => {
      const store = useEntityStore()
      const mockEntity = makeEntity('test-entity')
      store.entities = [mockEntity]

      const result = await store.selectEntity('test-project', 'test-entity')

      expect(api.entities.get).not.toHaveBeenCalled()
      expect(store.selectedEntity).toEqual(mockEntity)
      expect(store.hasUnsavedChanges).toBe(false)
      expect(result).toEqual(mockEntity)
    })

    it('should handle select errors', async () => {
      const store = useEntityStore()

      await expect(store.selectEntity('test-project', 'nonexistent')).rejects.toThrow(
        "Entity 'nonexistent' not found in cache",
      )

      expect(api.entities.get).not.toHaveBeenCalled()
      expect(store.error).toBe("Entity 'nonexistent' not found in cache")
    })
  })

  describe('createEntity', () => {
    it('should create an entity successfully', async () => {
      const store = useEntityStore()
      const createData: EntityCreateRequest = {
        name: 'new-entity',
        entity_data: { type: 'table' },
      }
      const mockEntity = makeEntity('new-entity', { type: 'table' })

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
      const existing = makeEntity('test-entity', { type: 'table' })
      store.entities = [existing]

      const updateData: EntityUpdateRequest = {
        entity_data: { type: 'view', description: 'Updated' },
      }
      const updated = makeEntity('test-entity', { type: 'view', description: 'Updated' })

      vi.mocked(api.entities.update).mockResolvedValue(updated)

      const result = await store.updateEntity('test-project', 'test-entity', updateData)

      expect(api.entities.update).toHaveBeenCalledWith('test-project', 'test-entity', updateData, 'test-entity-etag')
      expect(store.entities[0]).toEqual(updated)
      expect(store.selectedEntity).toEqual(updated)
      expect(store.hasUnsavedChanges).toBe(false)
      expect(result).toEqual(updated)
    })

    it('should use the freshest cached entity etag for updates', async () => {
      const store = useEntityStore()
      store.entities = [makeEntity('test-entity', { type: 'table' }, { etag: 'fresh-etag' })]
      store.selectedEntity = makeEntity('test-entity', { type: 'table' }, { etag: 'stale-etag' })

      const updateData: EntityUpdateRequest = {
        entity_data: { type: 'view', description: 'Updated' },
      }
      const updated = makeEntity('test-entity', { type: 'view', description: 'Updated' }, { etag: 'new-etag' })

      vi.mocked(api.entities.update).mockResolvedValue(updated)

      await store.updateEntity('test-project', 'test-entity', updateData)

      expect(api.entities.update).toHaveBeenCalledWith('test-project', 'test-entity', updateData, 'fresh-etag')
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
      const entity1 = makeEntity('entity1')
      const entity2 = makeEntity('entity2')
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
      const entity1 = makeEntity('entity1')
      const entity2 = makeEntity('entity2')
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
      store.entities = [makeEntity('test')]
      store.selectedEntity = makeEntity('test')
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
