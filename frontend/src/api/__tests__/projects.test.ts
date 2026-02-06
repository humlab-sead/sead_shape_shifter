/**
 * Unit tests for projects API service
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { projectsApi } from '../projects'
import type {
  // @ts-ignore
  Project,
  // @ts-ignore
  ProjectMetadata,
  // @ts-ignore
  ValidationResult,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  BackupInfo,
  RestoreBackupRequest,
  MetadataUpdateRequest,
} from '../projects'

// Mock the API client
vi.mock('../client', () => ({
  apiRequest: vi.fn(),
}))

import { apiRequest } from '../client'

describe('projectsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('should fetch all projects', async () => {
      const mockProjects: ProjectMetadata[] = [
        {
          name: 'project1',
          description: 'Test project 1',
          version: '1.0.0',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        {
          name: 'project2',
          description: 'Test project 2',
          version: '1.0.1',
          created_at: '2024-01-02T00:00:00Z',
          updated_at: '2024-01-02T00:00:00Z',
        },
      ]

      vi.mocked(apiRequest).mockResolvedValue(mockProjects)

      const result = await projectsApi.list()

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects',
      })
      expect(result).toEqual(mockProjects)
    })

    it('should handle empty project list', async () => {
      vi.mocked(apiRequest).mockResolvedValue([])

      const result = await projectsApi.list()

      expect(result).toEqual([])
    })
  })

  describe('get', () => {
    it('should fetch a specific project', async () => {
      const mockProject: Project = {
        name: 'test-project',
        description: 'A test project',
        version: '1.0.0',
        entities: {
          entity1: { field: 'value1' },
        },
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockProject)

      const result = await projectsApi.get('test-project')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects/test-project',
      })
      expect(result).toEqual(mockProject)
    })

    it('should handle project with special characters in name', async () => {
      const mockProject: Project = {
        name: 'test-project_123',
        description: 'Test',
        version: '1.0.0',
        entities: {},
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockProject)

      await projectsApi.get('test-project_123')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects/test-project_123',
      })
    })
  })

  describe('create', () => {
    it('should create a new project with minimal data', async () => {
      const createData: ProjectCreateRequest = {
        name: 'new-project',
      }

      const mockResponse: Project = {
        name: 'new-project',
        description: null,
        version: '1.0.0',
        entities: {},
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await projectsApi.create(createData)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects',
        data: createData,
      })
      expect(result).toEqual(mockResponse)
    })

    it('should create a new project with entities', async () => {
      const createData: ProjectCreateRequest = {
        name: 'new-project',
        entities: {
          entity1: { field: 'value' },
          entity2: { field: 'value' },
        },
      }

      const mockResponse: Project = {
        name: 'new-project',
        description: null,
        version: '1.0.0',
        entities: createData.entities!,
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await projectsApi.create(createData)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects',
        data: createData,
      })
      expect(result.entities).toEqual(createData.entities)
    })
  })

  describe('update', () => {
    it('should update a project', async () => {
      const updateData: ProjectUpdateRequest = {
        entities: {
          entity1: { updated: true },
        },
        options: {
          setting: 'value',
        },
      }

      const mockResponse: Project = {
        name: 'test-project',
        description: 'Updated',
        version: '1.0.1',
        entities: updateData.entities,
        options: updateData.options,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await projectsApi.update('test-project', updateData)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'PUT',
        url: '/projects/test-project',
        data: updateData,
      })
      expect(result).toEqual(mockResponse)
    })

    it('should update with empty entities', async () => {
      const updateData: ProjectUpdateRequest = {
        entities: {},
        options: {},
      }

      const mockResponse: Project = {
        name: 'test-project',
        description: null,
        version: '1.0.0',
        entities: {},
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      await projectsApi.update('test-project', updateData)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'PUT',
        url: '/projects/test-project',
        data: updateData,
      })
    })
  })

  describe('updateMetadata', () => {
    it('should update project metadata', async () => {
      const metadataUpdate: MetadataUpdateRequest = {
        name: 'renamed-project',
        description: 'New description',
        version: '2.0.0',
        default_entity: 'main_entity',
      }

      const mockResponse: Project = {
        name: 'renamed-project',
        description: 'New description',
        version: '2.0.0',
        entities: {},
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await projectsApi.updateMetadata('old-name', metadataUpdate)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'PATCH',
        url: '/projects/old-name/metadata',
        data: metadataUpdate,
      })
      expect(result).toEqual(mockResponse)
    })

    it('should update partial metadata', async () => {
      const metadataUpdate: MetadataUpdateRequest = {
        description: 'Updated description only',
      }

      const mockResponse: Project = {
        name: 'test-project',
        description: 'Updated description only',
        version: '1.0.0',
        entities: {},
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      await projectsApi.updateMetadata('test-project', metadataUpdate)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'PATCH',
        url: '/projects/test-project/metadata',
        data: metadataUpdate,
      })
    })

    it('should handle null values in metadata', async () => {
      const metadataUpdate: MetadataUpdateRequest = {
        description: null,
        default_entity: null,
      }

      const mockResponse: Project = {
        name: 'test-project',
        description: null,
        version: '1.0.0',
        entities: {},
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      await projectsApi.updateMetadata('test-project', metadataUpdate)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'PATCH',
        url: '/projects/test-project/metadata',
        data: metadataUpdate,
      })
    })
  })

  describe('delete', () => {
    it('should delete a project', async () => {
      vi.mocked(apiRequest).mockResolvedValue(undefined)

      await projectsApi.delete('test-project')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'DELETE',
        url: '/projects/test-project',
      })
    })

    it('should handle deletion of non-existent project', async () => {
      vi.mocked(apiRequest).mockRejectedValue(new Error('Project not found'))

      await expect(projectsApi.delete('nonexistent')).rejects.toThrow('Project not found')
    })
  })

  describe('validate', () => {
    it('should validate a project', async () => {
      const mockValidation: ValidationResult = {
        is_valid: true,
        errors: [],
        warnings: [],
        info: [],
        error_count: 0,
        warning_count: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockValidation)

      const result = await projectsApi.validate('test-project')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/validate',
      })
      expect(result).toEqual(mockValidation)
    })

    it('should return validation errors', async () => {
      const mockValidation: ValidationResult = {
        is_valid: false,
        errors: [
          {
            severity: 'error',
            message: 'Invalid entity configuration',
            entity: 'entity1',
          },
        ],
        warnings: [],
        info: [],
        error_count: 1,
        warning_count: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockValidation)

      const result = await projectsApi.validate('test-project')

      expect(result.is_valid).toBe(false)
      expect(result.errors).toHaveLength(1)
    })
  })

  describe('listBackups', () => {
    it('should list project backups', async () => {
      const mockBackups: BackupInfo[] = [
        {
          file_name: 'backup1.yml',
          file_path: '/path/to/backup1.yml',
          created_at: 1640995200,
        },
        {
          file_name: 'backup2.yml',
          file_path: '/path/to/backup2.yml',
          created_at: 1641081600,
        },
      ]

      vi.mocked(apiRequest).mockResolvedValue(mockBackups)

      const result = await projectsApi.listBackups('test-project')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects/test-project/backups',
      })
      expect(result).toEqual(mockBackups)
    })

    it('should handle project with no backups', async () => {
      vi.mocked(apiRequest).mockResolvedValue([])

      const result = await projectsApi.listBackups('test-project')

      expect(result).toEqual([])
    })
  })

  describe('restore', () => {
    it('should restore project from backup', async () => {
      const restoreData: RestoreBackupRequest = {
        backup_path: '/path/to/backup.yml',
      }

      const mockResponse: Project = {
        name: 'test-project',
        description: 'Restored from backup',
        version: '1.0.0',
        entities: {},
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await projectsApi.restore('test-project', restoreData)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/restore',
        data: restoreData,
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getActive', () => {
    it('should get active project name', async () => {
      const mockResponse = { name: 'active-project' }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await projectsApi.getActive()

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects/active/name',
      })
      expect(result).toEqual(mockResponse)
    })

    it('should handle no active project', async () => {
      const mockResponse = { name: null }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await projectsApi.getActive()

      expect(result.name).toBeNull()
    })
  })

  describe('activate', () => {
    it('should activate a project', async () => {
      const mockResponse: Project = {
        name: 'test-project',
        description: 'Activated project',
        version: '1.0.0',
        entities: {},
        options: {},
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResponse)

      const result = await projectsApi.activate('test-project')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/activate',
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getDataSources', () => {
    it('should get data sources connected to a project with string references', async () => {
      const mockDataSources: Record<string, string> = {
        'postgres-main': '@include: postgres-main.yml',
        'csv-imports': '@include: csv-imports.yml',
      }

      vi.mocked(apiRequest).mockResolvedValue(mockDataSources)

      const result = await projectsApi.getDataSources('test-project')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/projects/test-project/data-sources',
      })
      expect(result).toEqual(mockDataSources)
      expect(Object.keys(result)).toHaveLength(2)
    })

    it('should get data sources with inline configurations', async () => {
      const mockDataSources: Record<string, string | Record<string, any>> = {
        'postgres-main': {
          driver: 'postgresql',
          options: {
            host: 'localhost',
            port: 5432,
            dbname: 'testdb'
          }
        },
        'csv-imports': '@include: csv-imports.yml',
      }

      vi.mocked(apiRequest).mockResolvedValue(mockDataSources)

      const result = await projectsApi.getDataSources('test-project')

      expect(result).toEqual(mockDataSources)
      expect(Object.keys(result)).toHaveLength(2)
    })

    it('should return empty object when no data sources connected', async () => {
      vi.mocked(apiRequest).mockResolvedValue({})

      const result = await projectsApi.getDataSources('empty-project')

      expect(result).toEqual({})
    })
  })

  describe('connectDataSource', () => {
    it('should connect a data source to a project', async () => {
      const mockProject: Project = {
        name: 'test-project',
        version: '1.0.0',
        description: 'Test project',
      }

      vi.mocked(apiRequest).mockResolvedValue(mockProject)

      const result = await projectsApi.connectDataSource('test-project', 'postgres-main', 'postgres-main.yml')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/data-sources',
        data: {
          source_name: 'postgres-main',
          source_filename: 'postgres-main.yml',
        },
      })
      expect(result).toEqual(mockProject)
    })

    it('should handle source name with special characters', async () => {
      const mockProject: Project = {
        name: 'test-project',
        version: '1.0.0',
      }

      vi.mocked(apiRequest).mockResolvedValue(mockProject)

      await projectsApi.connectDataSource('test-project', 'db_source_1', 'db_source_1.yml')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/projects/test-project/data-sources',
        data: {
          source_name: 'db_source_1',
          source_filename: 'db_source_1.yml',
        },
      })
    })
  })

  describe('disconnectDataSource', () => {
    it('should disconnect a data source from a project', async () => {
      const mockProject: Project = {
        name: 'test-project',
        version: '1.0.1',
        description: 'Test project',
      }

      vi.mocked(apiRequest).mockResolvedValue(mockProject)

      const result = await projectsApi.disconnectDataSource('test-project', 'old-source')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'DELETE',
        url: '/projects/test-project/data-sources/old-source',
      })
      expect(result).toEqual(mockProject)
    })

    it('should handle disconnection of non-existent source', async () => {
      const error = new Error('Data source not found')
      vi.mocked(apiRequest).mockRejectedValue(error)

      await expect(projectsApi.disconnectDataSource('test-project', 'nonexistent')).rejects.toThrow(
        'Data source not found'
      )
    })
  })
})
