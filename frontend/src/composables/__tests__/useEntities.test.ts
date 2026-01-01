import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEntities } from '../useEntities'
import { useEntityStore } from '@/stores'
import type { EntityConfig, EntityCreateRequest, EntityUpdateRequest } from '@/api/entities'

// Mock console methods
const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

describe('useEntities', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    consoleError.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('initialization', () => {
    it('should initialize with required projectName', () => {
      const { loading, error, entities, currentProjectName } = useEntities({
        projectName: 'test-project',
        autoFetch: false,
      })

      expect(loading.value).toBe(false)
      expect(error.value).toBeNull()
      expect(entities.value).toEqual([])
      expect(currentProjectName.value).toBeNull()
    })

    it('should accept autoFetch option', () => {
      const store = useEntityStore()
      vi.spyOn(store, 'fetchEntities')

      useEntities({ projectName: 'test-project', autoFetch: false })

      expect(store.fetchEntities).not.toHaveBeenCalled()
    })

    it('should accept entityName option', () => {
      const { selectedEntity } = useEntities({
        projectName: 'test-project',
        autoFetch: false,
        entityName: 'test-entity',
      })

      expect(selectedEntity.value).toBeNull()
    })
  })

  describe('computed state', () => {
    it('should expose entities from store', () => {
      const store = useEntityStore()
      const { entities } = useEntities({ projectName: 'test-project', autoFetch: false })

      const mockEntities: EntityConfig[] = [
        {
          name: 'entity1',
          source: { type: 'table', table: 'table1' },
        },
      ]

      store.$patch({ entities: mockEntities })

      expect(entities.value).toEqual(mockEntities)
    })

    it('should expose selectedEntity from store', () => {
      const store = useEntityStore()
      const { selectedEntity } = useEntities({ projectName: 'test-project', autoFetch: false })

      const mockEntity: EntityConfig = {
        name: 'selected',
        source: { type: 'table', table: 'table1' },
      }

      store.$patch({ selectedEntity: mockEntity })

      expect(selectedEntity.value).toEqual(mockEntity)
    })

    it('should expose currentProjectName from store', () => {
      const store = useEntityStore()
      const { currentProjectName } = useEntities({ projectName: 'test-project', autoFetch: false })

      store.$patch({ currentProjectName: 'test-project' })

      expect(currentProjectName.value).toBe('test-project')
    })

    it('should expose loading state from store', () => {
      const store = useEntityStore()
      const { loading } = useEntities({ projectName: 'test-project', autoFetch: false })

      store.$patch({ loading: true })
      expect(loading.value).toBe(true)

      store.$patch({ loading: false })
      expect(loading.value).toBe(false)
    })

    it('should expose error state from store', () => {
      const store = useEntityStore()
      const { error } = useEntities({ projectName: 'test-project', autoFetch: false })

      store.$patch({ error: 'Test error' })
      expect(error.value).toBe('Test error')

      store.$patch({ error: null })
      expect(error.value).toBeNull()
    })

    it('should expose hasUnsavedChanges from store', () => {
      const store = useEntityStore()
      const { hasUnsavedChanges } = useEntities({ projectName: 'test-project', autoFetch: false })

      store.$patch({ hasUnsavedChanges: true })
      expect(hasUnsavedChanges.value).toBe(true)
    })
  })

  describe('computed getters', () => {
    it('should expose entitiesByType from store', () => {
      const store = useEntityStore()
      const { entitiesByType } = useEntities({ projectName: 'test-project', autoFetch: false })

      const mockEntitiesByType = {
        table: [{ name: 'entity1', source: { type: 'table', table: 'table1' } }],
      }

      vi.spyOn(store, 'entitiesByType', 'get').mockReturnValue(mockEntitiesByType)

      expect(entitiesByType.value).toEqual(mockEntitiesByType)
    })

    it('should compute entityCount correctly', () => {
      const store = useEntityStore()
      const { entityCount } = useEntities({ projectName: 'test-project', autoFetch: false })

      store.$patch({
        entities: [
          { name: 'entity1', source: { type: 'table', table: 'table1' } },
          { name: 'entity2', source: { type: 'table', table: 'table2' } },
        ],
      })

      expect(entityCount.value).toBe(2)
    })

    it('should expose rootEntities from store', () => {
      const store = useEntityStore()
      const { rootEntities } = useEntities({ projectName: 'test-project', autoFetch: false })

      const mockRootEntities = [{ name: 'root', source: { type: 'table', table: 'table1' } }]

      vi.spyOn(store, 'rootEntities', 'get').mockReturnValue(mockRootEntities)

      expect(rootEntities.value).toEqual(mockRootEntities)
    })

    it('should check if entities are empty', () => {
      const { isEmpty } = useEntities({ projectName: 'test-project', autoFetch: false })

      expect(isEmpty.value).toBe(true)
    })
  })

  describe('fetch action', () => {
    it('should fetch entities successfully', async () => {
      const store = useEntityStore()
      vi.spyOn(store, 'fetchEntities').mockResolvedValue()

      const { fetch, initialized } = useEntities({ projectName: 'test-project', autoFetch: false })

      expect(initialized.value).toBe(false)

      await fetch()

      expect(store.fetchEntities).toHaveBeenCalledWith('test-project')
      expect(initialized.value).toBe(true)
    })

    it('should handle fetch errors', async () => {
      const store = useEntityStore()
      const error = new Error('Fetch failed')
      vi.spyOn(store, 'fetchEntities').mockRejectedValue(error)

      const { fetch } = useEntities({ projectName: 'test-project', autoFetch: false })

      await expect(fetch()).rejects.toThrow('Fetch failed')
    })
  })

  describe('select action', () => {
    it('should select an entity', async () => {
      const store = useEntityStore()
      const mockEntity: EntityConfig = {
        name: 'selected',
        source: { type: 'table', table: 'table1' },
      }

      vi.spyOn(store, 'selectEntity').mockResolvedValue(mockEntity)

      const { select } = useEntities({ projectName: 'test-project', autoFetch: false })
      const result = await select('selected')

      expect(store.selectEntity).toHaveBeenCalledWith('test-project', 'selected')
      expect(result).toEqual(mockEntity)
    })

    it('should handle select errors', async () => {
      const store = useEntityStore()
      const error = new Error('Select failed')
      vi.spyOn(store, 'selectEntity').mockRejectedValue(error)

      const { select } = useEntities({ projectName: 'test-project', autoFetch: false })

      await expect(select('nonexistent')).rejects.toThrow('Select failed')
    })
  })

  describe('create action', () => {
    it('should create an entity', async () => {
      const store = useEntityStore()
      const createRequest: EntityCreateRequest = {
        name: 'new-entity',
        source: { type: 'table', table: 'new_table' },
      }
      const mockEntity: EntityConfig = {
        name: 'new-entity',
        source: { type: 'table', table: 'new_table' },
      }

      vi.spyOn(store, 'createEntity').mockResolvedValue(mockEntity)

      const { create } = useEntities({ projectName: 'test-project', autoFetch: false })
      const result = await create(createRequest)

      expect(store.createEntity).toHaveBeenCalledWith('test-project', createRequest)
      expect(result).toEqual(mockEntity)
    })

    it('should handle create errors', async () => {
      const store = useEntityStore()
      const error = new Error('Create failed')
      vi.spyOn(store, 'createEntity').mockRejectedValue(error)

      const { create } = useEntities({ projectName: 'test-project', autoFetch: false })
      const createRequest: EntityCreateRequest = {
        name: 'invalid',
        source: { type: 'table', table: 'invalid_table' },
      }

      await expect(create(createRequest)).rejects.toThrow('Create failed')
    })
  })

  describe('update action', () => {
    it('should update an entity', async () => {
      const store = useEntityStore()
      const updateRequest: EntityUpdateRequest = {
        source: { type: 'table', table: 'updated_table' },
      }
      const mockEntity: EntityConfig = {
        name: 'test-entity',
        source: { type: 'table', table: 'updated_table' },
      }

      vi.spyOn(store, 'updateEntity').mockResolvedValue(mockEntity)

      const { update } = useEntities({ projectName: 'test-project', autoFetch: false })
      const result = await update('test-entity', updateRequest)

      expect(store.updateEntity).toHaveBeenCalledWith('test-project', 'test-entity', updateRequest)
      expect(result).toEqual(mockEntity)
    })

    it('should handle update errors', async () => {
      const store = useEntityStore()
      const error = new Error('Update failed')
      vi.spyOn(store, 'updateEntity').mockRejectedValue(error)

      const { update } = useEntities({ projectName: 'test-project', autoFetch: false })
      const updateRequest: EntityUpdateRequest = { source: { type: 'table', table: 'new' } }

      await expect(update('test-entity', updateRequest)).rejects.toThrow('Update failed')
    })
  })

  describe('remove action', () => {
    it('should delete an entity', async () => {
      const store = useEntityStore()
      vi.spyOn(store, 'deleteEntity').mockResolvedValue()

      const { remove } = useEntities({ projectName: 'test-project', autoFetch: false })
      await remove('test-entity')

      expect(store.deleteEntity).toHaveBeenCalledWith('test-project', 'test-entity')
    })

    it('should handle delete errors', async () => {
      const store = useEntityStore()
      const error = new Error('Delete failed')
      vi.spyOn(store, 'deleteEntity').mockRejectedValue(error)

      const { remove } = useEntities({ projectName: 'test-project', autoFetch: false })

      await expect(remove('test-entity')).rejects.toThrow('Delete failed')
    })
  })

  describe('helper methods', () => {
    it('should get entity by name', () => {
      const store = useEntityStore()
      const mockEntity: EntityConfig = {
        name: 'test-entity',
        source: { type: 'table', table: 'table1' },
      }

      store.$patch({ entities: [mockEntity] })

      const { entityByName } = useEntities({ projectName: 'test-project', autoFetch: false })
      const result = entityByName('test-entity')

      expect(result).toEqual(mockEntity)
    })
  })

  describe('clearError action', () => {
    it('should clear error state', () => {
      const store = useEntityStore()
      vi.spyOn(store, 'clearError')

      const { clearError } = useEntities({ projectName: 'test-project', autoFetch: false })
      clearError()

      expect(store.clearError).toHaveBeenCalled()
    })
  })

  describe('project change handling', () => {
    it('should refetch when projectName changes', async () => {
      const store = useEntityStore()
      vi.spyOn(store, 'fetchEntities').mockResolvedValue()

      const { fetch } = useEntities({ projectName: 'project1', autoFetch: false })

      await fetch()
      expect(store.fetchEntities).toHaveBeenCalledWith('project1')
    })
  })
})
