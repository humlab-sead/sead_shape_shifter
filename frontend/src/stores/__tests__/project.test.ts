import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectStore } from '../project'
import type { Project, ProjectMetadata, ValidationResult } from '@/types'
import type { ProjectCreateRequest, ProjectUpdateRequest, BackupInfo, MetadataUpdateRequest } from '@/api/projects'

// Mock the API module
vi.mock('@/api', () => ({
  api: {
    projects: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      updateMetadata: vi.fn(),
      delete: vi.fn(),
      validate: vi.fn(),
      listBackups: vi.fn(),
      restore: vi.fn(),
      getActive: vi.fn(),
      activate: vi.fn(),
      getDataSources: vi.fn(),
      connectDataSource: vi.fn(),
      disconnectDataSource: vi.fn(),
    },
  },
}))

// Mock the session store
vi.mock('../session', () => ({
  useSessionStore: vi.fn(() => ({
    hasActiveSession: false,
    version: 1,
    markModified: vi.fn(),
    incrementVersion: vi.fn(),
  })),
}))

import { api } from '@/api'

describe('useProjectStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should initialize with empty state', () => {
      const store = useProjectStore()

      expect(store.projects).toEqual([])
      expect(store.selectedProject).toBeNull()
      expect(store.validationResult).toBeNull()
      expect(store.backups).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.hasUnsavedChanges).toBe(false)
    })
  })

  describe('computed getters', () => {
    it('should compute current project name', () => {
      const store = useProjectStore()

      expect(store.currentProjectName).toBeNull()

      store.selectedProject = {
        metadata: { name: 'test-project' },
      } as Project

      expect(store.currentProjectName).toBe('test-project')
    })

    it('should sort projects alphabetically', () => {
      const store = useProjectStore()
      store.projects = [
        { name: 'zebra' } as ProjectMetadata,
        { name: 'alpha' } as ProjectMetadata,
        { name: 'beta' } as ProjectMetadata,
      ]

      expect(store.sortedProjects.map((p) => p.name)).toEqual(['alpha', 'beta', 'zebra'])
    })

    it('should find project by name', () => {
      const store = useProjectStore()
      const project = { name: 'test-project' } as ProjectMetadata
      store.projects = [project]

      expect(store.projectByName('test-project')).toEqual(project)
      expect(store.projectByName('nonexistent')).toBeUndefined()
    })

    it('should detect validation errors', () => {
      const store = useProjectStore()

      expect(store.hasErrors).toBe(false)

      store.validationResult = { error_count: 1 } as ValidationResult
      expect(store.hasErrors).toBe(true)

      store.validationResult = { error_count: 0 } as ValidationResult
      expect(store.hasErrors).toBe(false)
    })

    it('should detect validation warnings', () => {
      const store = useProjectStore()

      expect(store.hasWarnings).toBe(false)

      store.validationResult = { warning_count: 1 } as ValidationResult
      expect(store.hasWarnings).toBe(true)

      store.validationResult = { warning_count: 0 } as ValidationResult
      expect(store.hasWarnings).toBe(false)
    })
  })

  describe('fetchProjects', () => {
    it('should fetch projects successfully', async () => {
      const store = useProjectStore()
      const mockProjects = [
        { name: 'project1' } as ProjectMetadata,
        { name: 'project2' } as ProjectMetadata,
      ]

      vi.mocked(api.projects.list).mockResolvedValue(mockProjects)

      await store.fetchProjects()

      expect(api.projects.list).toHaveBeenCalled()
      expect(store.projects).toEqual(mockProjects)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should handle fetch errors', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.list).mockRejectedValue(new Error('Fetch failed'))

      await expect(store.fetchProjects()).rejects.toThrow('Fetch failed')

      expect(store.error).toBe('Fetch failed')
      expect(store.loading).toBe(false)
    })
  })

  describe('selectProject', () => {
    it('should select a project successfully', async () => {
      const store = useProjectStore()
      const mockProject = {
        metadata: { name: 'test-project' },
        entities: {},
      } as Project

      vi.mocked(api.projects.get).mockResolvedValue(mockProject)

      const result = await store.selectProject('test-project')

      expect(api.projects.get).toHaveBeenCalledWith('test-project')
      expect(store.selectedProject).toEqual(mockProject)
      expect(store.hasUnsavedChanges).toBe(false)
      expect(result).toEqual(mockProject)
    })

    it('should handle select errors', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.get).mockRejectedValue(new Error('Not found'))

      await expect(store.selectProject('nonexistent')).rejects.toThrow('Not found')

      expect(store.error).toBe('Not found')
    })
  })

  describe('createProject', () => {
    it('should create a project successfully', async () => {
      const store = useProjectStore()
      const createData: ProjectCreateRequest = {
        name: 'new-project',
        entities: {},
      }
      const mockProject = {
        metadata: {
          name: 'new-project',
          entity_count: 0,
        },
        entities: {},
      } as Project

      vi.mocked(api.projects.create).mockResolvedValue(mockProject)

      const result = await store.createProject(createData)

      expect(api.projects.create).toHaveBeenCalledWith(createData)
      expect(store.projects).toHaveLength(1)
      expect(store.projects[0]?.name).toBe('new-project')
      expect(store.selectedProject).toEqual(mockProject)
      expect(store.hasUnsavedChanges).toBe(false)
      expect(result).toEqual(mockProject)
    })

    it('should handle create errors', async () => {
      const store = useProjectStore()
      const createData: ProjectCreateRequest = {
        name: 'new-project',
        entities: {},
      }

      vi.mocked(api.projects.create).mockRejectedValue(new Error('Create failed'))

      await expect(store.createProject(createData)).rejects.toThrow('Create failed')

      expect(store.error).toBe('Create failed')
      expect(store.projects).toHaveLength(0)
    })
  })

  describe('updateProject', () => {
    it('should update a project successfully', async () => {
      const store = useProjectStore()
      store.projects = [{ name: 'test-project' } as ProjectMetadata]

      const updateData: ProjectUpdateRequest = {
        entities: { entity1: { name: 'entity1' } },
        options: {},
      }
      const updated = {
        metadata: {
          name: 'test-project',
          entity_count: 1,
        },
        entities: { entity1: { name: 'entity1' } },
      } as Project

      vi.mocked(api.projects.update).mockResolvedValue(updated)

      const result = await store.updateProject('test-project', updateData)

      expect(api.projects.update).toHaveBeenCalledWith('test-project', updateData)
      expect(store.projects[0]?.entity_count).toBe(1)
      expect(store.selectedProject).toEqual(updated)
      expect(store.hasUnsavedChanges).toBe(false)
      expect(result).toEqual(updated)
    })

    it('should handle update errors', async () => {
      const store = useProjectStore()
      const updateData: ProjectUpdateRequest = {
        entities: {},
        options: {},
      }

      vi.mocked(api.projects.update).mockRejectedValue(new Error('Update failed'))

      await expect(store.updateProject('test-project', updateData)).rejects.toThrow('Update failed')

      expect(store.error).toBe('Update failed')
    })
  })

  describe('updateMetadata', () => {
    it('should update metadata successfully', async () => {
      const store = useProjectStore()
      store.projects = [{ name: 'old-name' } as ProjectMetadata]

      const metadataUpdate: MetadataUpdateRequest = {
        name: 'new-name',
        description: 'Updated description',
      }
      const updated = {
        metadata: {
          name: 'new-name',
          description: 'Updated description',
          entity_count: 5,
        },
      } as Project

      vi.mocked(api.projects.updateMetadata).mockResolvedValue(updated)

      const result = await store.updateMetadata('old-name', metadataUpdate)

      expect(api.projects.updateMetadata).toHaveBeenCalledWith('old-name', metadataUpdate)
      expect(store.projects[0]?.name).toBe('new-name')
      expect(store.projects[0]?.description).toBe('Updated description')
      expect(store.selectedProject).toEqual(updated)
      expect(result).toEqual(updated)
    })

    it('should handle metadata update errors', async () => {
      const store = useProjectStore()
      const metadataUpdate: MetadataUpdateRequest = { name: 'new-name' }

      vi.mocked(api.projects.updateMetadata).mockRejectedValue(new Error('Update failed'))

      await expect(store.updateMetadata('test-project', metadataUpdate)).rejects.toThrow('Update failed')

      expect(store.error).toBe('Update failed')
    })
  })

  describe('deleteProject', () => {
    it('should delete a project successfully', async () => {
      const store = useProjectStore()
      const project1 = { name: 'project1' } as ProjectMetadata
      const project2 = { name: 'project2' } as ProjectMetadata
      store.projects = [project1, project2]
      store.selectedProject = { metadata: { name: 'project1' } } as Project

      vi.mocked(api.projects.delete).mockResolvedValue(undefined)

      await store.deleteProject('project1')

      expect(api.projects.delete).toHaveBeenCalledWith('project1')
      expect(store.projects).toHaveLength(1)
      expect(store.projects[0]).toEqual(project2)
      expect(store.selectedProject).toBeNull()
    })

    it('should not clear selectedProject if different project deleted', async () => {
      const store = useProjectStore()
      const project1 = { name: 'project1' } as ProjectMetadata
      const project2 = { name: 'project2' } as ProjectMetadata
      store.projects = [project1, project2]
      store.selectedProject = { metadata: { name: 'project1' } } as Project

      vi.mocked(api.projects.delete).mockResolvedValue(undefined)

      await store.deleteProject('project2')

      expect(store.selectedProject).not.toBeNull()
      expect(store.selectedProject?.metadata?.name).toBe('project1')
    })

    it('should handle delete errors', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.delete).mockRejectedValue(new Error('Delete failed'))

      await expect(store.deleteProject('test-project')).rejects.toThrow('Delete failed')

      expect(store.error).toBe('Delete failed')
    })
  })

  describe('validateProject', () => {
    it('should validate a project successfully', async () => {
      const store = useProjectStore()
      const mockResult = {
        is_valid: true,
        error_count: 0,
        warning_count: 0,
      } as ValidationResult

      vi.mocked(api.projects.validate).mockResolvedValue(mockResult)

      const result = await store.validateProject('test-project')

      expect(api.projects.validate).toHaveBeenCalledWith('test-project')
      expect(store.validationResult).toEqual(mockResult)
      expect(result).toEqual(mockResult)
    })

    it('should handle validation errors', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.validate).mockRejectedValue(new Error('Validation failed'))

      await expect(store.validateProject('test-project')).rejects.toThrow('Validation failed')

      expect(store.error).toBe('Validation failed')
    })
  })

  describe('fetchBackups', () => {
    it('should fetch backups successfully', async () => {
      const store = useProjectStore()
      const mockBackups = [
        { file_name: 'backup1.yml', file_path: '/tmp/backup1.yml', created_at: Date.now() } as BackupInfo,
        { file_name: 'backup2.yml', file_path: '/tmp/backup2.yml', created_at: Date.now() } as BackupInfo,
      ]

      vi.mocked(api.projects.listBackups).mockResolvedValue(mockBackups)

      const result = await store.fetchBackups('test-project')

      expect(api.projects.listBackups).toHaveBeenCalledWith('test-project')
      expect(store.backups).toEqual(mockBackups)
      expect(result).toEqual(mockBackups)
    })

    it('should handle fetch backups errors', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.listBackups).mockRejectedValue(new Error('Fetch failed'))

      await expect(store.fetchBackups('test-project')).rejects.toThrow('Fetch failed')

      expect(store.error).toBe('Fetch failed')
    })
  })

  describe('restoreBackup', () => {
    it('should restore from backup successfully', async () => {
      const store = useProjectStore()
      store.projects = [{ name: 'test-project' } as ProjectMetadata]

      const restored = {
        metadata: {
          name: 'test-project',
          entity_count: 10,
        },
      } as Project

      vi.mocked(api.projects.restore).mockResolvedValue(restored)

      const result = await store.restoreBackup('test-project', 'backup.yml')

      expect(api.projects.restore).toHaveBeenCalledWith('test-project', { backup_path: 'backup.yml' })
      expect(store.selectedProject).toEqual(restored)
      expect(store.projects[0]?.entity_count).toBe(10)
      expect(store.hasUnsavedChanges).toBe(false)
      expect(result).toEqual(restored)
    })

    it('should handle restore errors', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.restore).mockRejectedValue(new Error('Restore failed'))

      await expect(store.restoreBackup('test-project', 'backup.yml')).rejects.toThrow('Restore failed')

      expect(store.error).toBe('Restore failed')
    })
  })

  describe('getActiveProject', () => {
    it('should get active project name', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.getActive).mockResolvedValue({ name: 'active-project' } as any)

      const result = await store.getActiveProject()

      expect(api.projects.getActive).toHaveBeenCalled()
      expect(result).toBe('active-project')
    })

    it('should handle errors when getting active project', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.getActive).mockRejectedValue(new Error('Failed'))

      const result = await store.getActiveProject()

      expect(result).toBeNull()
      expect(store.error).toBe('Failed')
    })
  })

  describe('activateProject', () => {
    it('should activate a project successfully', async () => {
      const store = useProjectStore()
      const mockProject = {
        metadata: { name: 'test-project' },
      } as Project

      vi.mocked(api.projects.activate).mockResolvedValue(mockProject)

      const result = await store.activateProject('test-project')

      expect(api.projects.activate).toHaveBeenCalledWith('test-project')
      expect(store.selectedProject).toEqual(mockProject)
      expect(result).toEqual(mockProject)
    })

    it('should handle activation errors', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.activate).mockRejectedValue(new Error('Activation failed'))

      await expect(store.activateProject('test-project')).rejects.toThrow('Activation failed')

      expect(store.error).toBe('Activation failed')
    })
  })

  describe('getProjectDataSources', () => {
    it('should get project data sources', async () => {
      const store = useProjectStore()
      const mockDataSources = [{ name: 'ds1' }, { name: 'ds2' }]

      vi.mocked(api.projects.getDataSources).mockResolvedValue(mockDataSources as any)

      const result = await store.getProjectDataSources('test-project')

      expect(api.projects.getDataSources).toHaveBeenCalledWith('test-project')
      expect(result).toEqual(mockDataSources)
    })

    it('should handle errors getting data sources', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.getDataSources).mockRejectedValue(new Error('Failed'))

      await expect(store.getProjectDataSources('test-project')).rejects.toThrow('Failed')

      expect(store.error).toBe('Failed')
    })
  })

  describe('connectDataSource', () => {
    it('should connect data source successfully', async () => {
      const store = useProjectStore()
      const mockProject = {
        metadata: { name: 'test-project' },
      } as Project

      vi.mocked(api.projects.connectDataSource).mockResolvedValue(mockProject)

      const result = await store.connectDataSource('test-project', 'ds1', 'file.csv')

      expect(api.projects.connectDataSource).toHaveBeenCalledWith('test-project', 'ds1', 'file.csv')
      expect(store.selectedProject).toEqual(mockProject)
      expect(result).toEqual(mockProject)
    })

    it('should handle connection errors', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.connectDataSource).mockRejectedValue(new Error('Connection failed'))

      await expect(store.connectDataSource('test-project', 'ds1', 'file.csv')).rejects.toThrow('Connection failed')

      expect(store.error).toBe('Connection failed')
    })
  })

  describe('disconnectDataSource', () => {
    it('should disconnect data source successfully', async () => {
      const store = useProjectStore()
      const mockProject = {
        metadata: { name: 'test-project' },
      } as Project

      vi.mocked(api.projects.disconnectDataSource).mockResolvedValue(mockProject)

      const result = await store.disconnectDataSource('test-project', 'ds1')

      expect(api.projects.disconnectDataSource).toHaveBeenCalledWith('test-project', 'ds1')
      expect(store.selectedProject).toEqual(mockProject)
      expect(result).toEqual(mockProject)
    })

    it('should handle disconnection errors', async () => {
      const store = useProjectStore()

      vi.mocked(api.projects.disconnectDataSource).mockRejectedValue(new Error('Disconnection failed'))

      await expect(store.disconnectDataSource('test-project', 'ds1')).rejects.toThrow('Disconnection failed')

      expect(store.error).toBe('Disconnection failed')
    })
  })

  describe('markAsChanged', () => {
    it('should mark as having unsaved changes', () => {
      const store = useProjectStore()

      expect(store.hasUnsavedChanges).toBe(false)

      store.markAsChanged()

      expect(store.hasUnsavedChanges).toBe(true)
    })
  })

  describe('clearError', () => {
    it('should clear error state', () => {
      const store = useProjectStore()
      store.error = 'Some error'

      store.clearError()

      expect(store.error).toBeNull()
    })
  })

  describe('clearValidation', () => {
    it('should clear validation result', () => {
      const store = useProjectStore()
      store.validationResult = { error_count: 1 } as ValidationResult

      store.clearValidation()

      expect(store.validationResult).toBeNull()
    })
  })

  describe('reset', () => {
    it('should reset all state to initial values', () => {
      const store = useProjectStore()
      store.projects = [{ name: 'test' } as ProjectMetadata]
      store.selectedProject = { metadata: { name: 'test' } } as Project
      store.validationResult = { error_count: 0 } as ValidationResult
      store.backups = [
        { file_name: 'backup.yml', file_path: '/tmp/backup.yml', created_at: Date.now() } as BackupInfo,
      ]
      store.loading = true
      store.error = 'Some error'
      store.hasUnsavedChanges = true

      store.reset()

      expect(store.projects).toEqual([])
      expect(store.selectedProject).toBeNull()
      expect(store.validationResult).toBeNull()
      expect(store.backups).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.hasUnsavedChanges).toBe(false)
    })
  })
})
