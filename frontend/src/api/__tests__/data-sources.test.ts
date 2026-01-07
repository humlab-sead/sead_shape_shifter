/**
 * Unit tests for data sources API service
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { dataSourcesApi } from '../data-sources'
import type { DataSourceConfig, DataSourceTestResult, DataSourceStatus } from '@/types/data-source'

// Mock the API client
vi.mock('../client', () => ({
  apiRequest: vi.fn(),
}))

import { apiRequest } from '../client'

describe('dataSourcesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('should list all data sources', async () => {
      const mockDataSources: DataSourceConfig[] = [
        {
          name: 'postgres-db',
          driver: 'postgresql',
          host: 'localhost',
          port: 5432,
          database: 'testdb',
          username: 'user',
          description: 'PostgreSQL database',
        },
        {
          name: 'csv-file',
          driver: 'csv',
          file_path: '/data/test.csv',
        },
      ]

      vi.mocked(apiRequest).mockResolvedValue(mockDataSources)

      const result = await dataSourcesApi.list()

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/data-sources',
      })
      expect(result).toEqual(mockDataSources)
      expect(result).toHaveLength(2)
    })

    it('should return empty array when no data sources exist', async () => {
      vi.mocked(apiRequest).mockResolvedValue([])

      const result = await dataSourcesApi.list()

      expect(result).toEqual([])
      expect(result).toHaveLength(0)
    })

    it('should handle multiple data sources with different drivers', async () => {
      const mockDataSources: DataSourceConfig[] = [
        { name: 'db1', driver: 'postgresql' },
        { name: 'db2', driver: 'postgresql' },
        { name: 'file1', driver: 'csv' },
        { name: 'file2', driver: 'csv' },
      ]

      vi.mocked(apiRequest).mockResolvedValue(mockDataSources)

      const result = await dataSourcesApi.list()

      expect(result).toHaveLength(4)
      expect(result.map((ds) => ds.driver)).toEqual(['postgresql', 'postgresql', 'csv', 'csv'])
    })
  })

  describe('get', () => {
    it('should get a specific data source by filename', async () => {
      const mockDataSource: DataSourceConfig = {
        name: 'postgres-db',
        driver: 'postgresql',
        host: 'localhost',
        port: 5432,
        database: 'testdb',
        username: 'user',
        description: 'Main database',
      }

      vi.mocked(apiRequest).mockResolvedValue(mockDataSource)

      const result = await dataSourcesApi.get('postgres-db.yml')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/data-sources/postgres-db.yml',
      })
      expect(result).toEqual(mockDataSource)
    })

    it('should handle data source with environment variables', async () => {
      const mockDataSource: DataSourceConfig = {
        name: 'prod-db',
        driver: 'postgresql',
        host: '${DB_HOST}',
        port: 5432,
        database: '${DB_NAME}',
        username: '${DB_USER}',
        password: '${DB_PASSWORD}',
      }

      vi.mocked(apiRequest).mockResolvedValue(mockDataSource)

      const result = await dataSourcesApi.get('prod-db.yml')

      expect(result.host).toBe('${DB_HOST}')
      expect(result.password).toBe('${DB_PASSWORD}')
    })

    it('should handle filename with special characters', async () => {
      const mockDataSource: DataSourceConfig = {
        name: 'data_source_1',
        driver: 'csv',
        file_path: '/data/test.csv',
      }

      vi.mocked(apiRequest).mockResolvedValue(mockDataSource)

      await dataSourcesApi.get('data_source_1.yml')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/data-sources/data_source_1.yml',
      })
    })
  })

  describe('create', () => {
    it('should create a new data source', async () => {
      const input: DataSourceConfig = {
        name: 'new-db',
        driver: 'postgresql',
        host: 'localhost',
        port: 5432,
        database: 'newdb',
        username: 'user',
        description: 'New database',
      }

      vi.mocked(apiRequest).mockResolvedValue(input)

      const result = await dataSourcesApi.create(input)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/data-sources',
        data: input,
      })
      expect(result).toEqual(input)
    })

    it('should create CSV data source', async () => {
      const input: DataSourceConfig = {
        name: 'csv-source',
        driver: 'csv',
        file_path: '/data/import.csv',
        options: {
          delimiter: ',',
          encoding: 'utf-8',
        },
      }

      vi.mocked(apiRequest).mockResolvedValue(input)

      const result = await dataSourcesApi.create(input)

      expect(result.options?.delimiter).toBe(',')
      expect(result.options?.encoding).toBe('utf-8')
    })

    it('should create data source without description', async () => {
      const input: DataSourceConfig = {
        name: 'simple-db',
        driver: 'sqlite',
        database: ':memory:',
      }

      vi.mocked(apiRequest).mockResolvedValue(input)

      const result = await dataSourcesApi.create(input)

      expect(result.description).toBeUndefined()
    })
  })

  describe('update', () => {
    it('should update an existing data source', async () => {
      const config: DataSourceConfig = {
        name: 'postgres-db',
        driver: 'postgresql',
        host: 'new-host',
        port: 5433,
        database: 'testdb',
        username: 'user',
        description: 'Updated description',
      }

      vi.mocked(apiRequest).mockResolvedValue(config)

      const result = await dataSourcesApi.update('postgres-db.yml', config)

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'PUT',
        url: '/data-sources/postgres-db.yml',
        data: config,
      })
      expect(result.host).toBe('new-host')
      expect(result.description).toBe('Updated description')
    })

    it('should update only config fields', async () => {
      const config: DataSourceConfig = {
        name: 'db',
        driver: 'postgresql',
        database: 'newdb',
        host: 'localhost',
      }

      vi.mocked(apiRequest).mockResolvedValue(config)

      const result = await dataSourcesApi.update('db.yml', config)

      expect(result.database).toBe('newdb')
    })

    it('should update description', async () => {
      const config: DataSourceConfig = {
        name: 'db',
        driver: 'postgresql',
        host: 'localhost',
        description: 'New description',
      }

      vi.mocked(apiRequest).mockResolvedValue(config)

      const result = await dataSourcesApi.update('db.yml', config)

      expect(result.description).toBe('New description')
    })
  })

  describe('delete', () => {
    it('should delete a data source', async () => {
      vi.mocked(apiRequest).mockResolvedValue(undefined)

      await dataSourcesApi.delete('old-db.yml')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'DELETE',
        url: '/data-sources/old-db.yml',
      })
    })

    it('should handle deletion of non-existent data source', async () => {
      const error = new Error('Data source not found')
      vi.mocked(apiRequest).mockRejectedValue(error)

      await expect(dataSourcesApi.delete('nonexistent.yml')).rejects.toThrow('Data source not found')
    })
  })

  describe('testConnection', () => {
    it('should test connection successfully', async () => {
      const mockResult: DataSourceTestResult = {
        success: true,
        message: 'Connection successful',
        connection_time_ms: 150,
        metadata: {
          server_version: 'PostgreSQL 14.5',
          database: 'testdb',
        },
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResult)

      const result = await dataSourcesApi.testConnection('postgres-db.yml')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'POST',
        url: '/data-sources/postgres-db.yml/test',
      })
      expect(result.success).toBe(true)
      expect(result.message).toBe('Connection successful')
    })

    it('should handle connection failure', async () => {
      const mockResult: DataSourceTestResult = {
        success: false,
        message: 'Connection refused',
        connection_time_ms: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResult)

      const result = await dataSourcesApi.testConnection('bad-db.yml')

      expect(result.success).toBe(false)
      expect(result.message).toContain('Connection refused')
    })

    it('should handle authentication failure', async () => {
      const mockResult: DataSourceTestResult = {
        success: false,
        message: 'Authentication failed',
        connection_time_ms: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResult)

      const result = await dataSourcesApi.testConnection('db.yml')

      expect(result.success).toBe(false)
      expect(result.message).toContain('Authentication failed')
    })

    it('should handle timeout', async () => {
      const mockResult: DataSourceTestResult = {
        success: false,
        message: 'Connection timeout',
        connection_time_ms: 0,
      }

      vi.mocked(apiRequest).mockResolvedValue(mockResult)

      const result = await dataSourcesApi.testConnection('slow-db.yml')

      expect(result.success).toBe(false)
      expect(result.message).toContain('Connection timeout')
    })
  })

  describe('getStatus', () => {
    it('should get connection status for active connection', async () => {
      const mockStatus: DataSourceStatus = {
        name: 'postgres-db',
        is_connected: true,
        last_test_result: {
          success: true,
          message: 'Connected',
          connection_time_ms: 100,
        },
        in_use_by_entities: [],
      }

      vi.mocked(apiRequest).mockResolvedValue(mockStatus)

      const result = await dataSourcesApi.getStatus('postgres-db.yml')

      expect(apiRequest).toHaveBeenCalledWith({
        method: 'GET',
        url: '/data-sources/postgres-db.yml/status',
      })
      expect(result.is_connected).toBe(true)
      expect(result.last_test_result).toBeDefined()
    })

    it('should get status for inactive connection', async () => {
      const mockStatus: DataSourceStatus = {
        name: 'inactive-db',
        is_connected: false,
        last_test_result: null,
        in_use_by_entities: [],
      }

      vi.mocked(apiRequest).mockResolvedValue(mockStatus)

      const result = await dataSourcesApi.getStatus('inactive-db.yml')

      expect(result.is_connected).toBe(false)
    })

    it('should handle status with connection details', async () => {
      const mockStatus: DataSourceStatus = {
        name: 'db',
        is_connected: true,
        last_test_result: {
          success: true,
          message: 'Connected',
          connection_time_ms: 85,
          metadata: {
            server_version: 'PostgreSQL 15.1',
            uptime: '5 days',
            active_connections: 42,
          },
        },
        in_use_by_entities: ['sample', 'analysis'],
      }

      vi.mocked(apiRequest).mockResolvedValue(mockStatus)

      const result = await dataSourcesApi.getStatus('db.yml')

      expect(result.last_test_result?.metadata?.server_version).toBe('PostgreSQL 15.1')
      expect(result.last_test_result?.metadata?.active_connections).toBe(42)
      expect(result.in_use_by_entities).toEqual(['sample', 'analysis'])
    })
  })

  describe('error handling', () => {
    it('should propagate network errors', async () => {
      const error = new Error('Network error')
      vi.mocked(apiRequest).mockRejectedValue(error)

      await expect(dataSourcesApi.list()).rejects.toThrow('Network error')
    })

    it('should handle 404 errors', async () => {
      const error = new Error('Not found')
      vi.mocked(apiRequest).mockRejectedValue(error)

      await expect(dataSourcesApi.get('nonexistent.yml')).rejects.toThrow('Not found')
    })

    it('should handle validation errors on create', async () => {
      const error = new Error('Invalid configuration')
      vi.mocked(apiRequest).mockRejectedValue(error)

      const input: DataSourceConfig = {
        name: 'bad-config',
        driver: 'postgresql',
      }

      await expect(dataSourcesApi.create(input)).rejects.toThrow('Invalid configuration')
    })
  })
})
