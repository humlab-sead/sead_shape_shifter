import { describe, it, expect, vi, beforeEach } from 'vitest'
import { schemaApi } from '../schema'
import { apiClient } from '../client'
import type { TableMetadata, TableSchema, PreviewData, TypeMapping } from '@/types/schema'

// Mock the API client
vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const mockApiClient = apiClient as any

describe('schemaApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listTables', () => {
    it('should list tables for a data source', async () => {
      const mockTables: TableMetadata[] = [
        { name: 'users', row_count: 100 },
        { name: 'posts', row_count: 250 },
        { name: 'comments', row_count: 500 },
      ]

      mockApiClient.get.mockResolvedValue({ data: mockTables })

      const result = await schemaApi.listTables('my-database')

      expect(result).toEqual(mockTables)
      expect(mockApiClient.get).toHaveBeenCalledWith('/data-sources/my-database/tables', {
        params: undefined,
      })
    })

    it('should list tables with schema filter', async () => {
      const mockTables: TableMetadata[] = [{ name: 'table1', row_count: 10 }]

      mockApiClient.get.mockResolvedValue({ data: mockTables })

      await schemaApi.listTables('my-database', { schema: 'public' })

      expect(mockApiClient.get).toHaveBeenCalledWith('/data-sources/my-database/tables', {
        params: { schema: 'public' },
      })
    })

    it('should handle URL encoding for data source names', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] })

      await schemaApi.listTables('my database with spaces')

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my%20database%20with%20spaces/tables',
        { params: undefined }
      )
    })

    it('should propagate API errors', async () => {
      const error = new Error('Network error')

      mockApiClient.get.mockRejectedValue(error)

      await expect(schemaApi.listTables('my-database')).rejects.toThrow('Network error')
    })
  })

  describe('getTableSchema', () => {
    it('should get table schema', async () => {
      const mockSchema: TableSchema = {
        name: 'users',
        columns: [
          { name: 'id', type: 'integer', nullable: false },
          { name: 'email', type: 'varchar', nullable: false },
          { name: 'name', type: 'varchar', nullable: true },
        ],
      }

      mockApiClient.get.mockResolvedValue({ data: mockSchema })

      const result = await schemaApi.getTableSchema('my-database', 'users')

      expect(result).toEqual(mockSchema)
      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my-database/tables/users/schema',
        { params: undefined }
      )
    })

    it('should get table schema with schema filter', async () => {
      const mockSchema: TableSchema = {
        name: 'table1',
        columns: [{ name: 'id', type: 'integer', nullable: false }],
      }

      mockApiClient.get.mockResolvedValue({ data: mockSchema })

      await schemaApi.getTableSchema('my-database', 'table1', { schema: 'public' })

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my-database/tables/table1/schema',
        { params: { schema: 'public' } }
      )
    })

    it('should handle URL encoding for table names', async () => {
      const mockSchema: TableSchema = {
        name: 'my table',
        columns: [],
      }

      mockApiClient.get.mockResolvedValue({ data: mockSchema })

      await schemaApi.getTableSchema('my-database', 'my table')

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my-database/tables/my%20table/schema',
        { params: undefined }
      )
    })

    it('should handle special characters in names', async () => {
      mockApiClient.get.mockResolvedValue({
        data: { name: 'test', columns: [] },
      })

      await schemaApi.getTableSchema('db/with/slashes', 'table&with&ampersands')

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/db%2Fwith%2Fslashes/tables/table%26with%26ampersands/schema',
        { params: undefined }
      )
    })

    it('should propagate API errors', async () => {
      const error = new Error('Table not found')

      mockApiClient.get.mockRejectedValue(error)

      await expect(schemaApi.getTableSchema('my-database', 'nonexistent')).rejects.toThrow(
        'Table not found'
      )
    })
  })

  describe('previewTableData', () => {
    it('should preview table data', async () => {
      const mockPreview: PreviewData = {
        columns: ['id', 'name', 'email'],
        rows: [
          [1, 'Alice', 'alice@example.com'],
          [2, 'Bob', 'bob@example.com'],
        ],
        total_rows: 2,
      }

      mockApiClient.get.mockResolvedValue({ data: mockPreview })

      const result = await schemaApi.previewTableData('my-database', 'users')

      expect(result).toEqual(mockPreview)
      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my-database/tables/users/preview',
        { params: undefined }
      )
    })

    it('should preview with limit parameter', async () => {
      const mockPreview: PreviewData = {
        columns: ['id'],
        rows: [[1]],
        total_rows: 1,
      }

      mockApiClient.get.mockResolvedValue({ data: mockPreview })

      await schemaApi.previewTableData('my-database', 'users', { limit: 10 })

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my-database/tables/users/preview',
        { params: { limit: 10 } }
      )
    })

    it('should preview with offset parameter', async () => {
      const mockPreview: PreviewData = {
        columns: ['id'],
        rows: [[11]],
        total_rows: 1,
      }

      mockApiClient.get.mockResolvedValue({ data: mockPreview })

      await schemaApi.previewTableData('my-database', 'users', { offset: 10 })

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my-database/tables/users/preview',
        { params: { offset: 10 } }
      )
    })

    it('should preview with all parameters', async () => {
      const mockPreview: PreviewData = {
        columns: ['id'],
        rows: [[1]],
        total_rows: 1,
      }

      mockApiClient.get.mockResolvedValue({ data: mockPreview })

      await schemaApi.previewTableData('my-database', 'users', {
        limit: 10,
        offset: 5,
        schema: 'public',
      })

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my-database/tables/users/preview',
        {
          params: {
            limit: 10,
            offset: 5,
            schema: 'public',
          },
        }
      )
    })

    it('should handle URL encoding in preview', async () => {
      mockApiClient.get.mockResolvedValue({
        data: { columns: [], rows: [], total_rows: 0 },
      })

      await schemaApi.previewTableData('my database', 'my table')

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my%20database/tables/my%20table/preview',
        { params: undefined }
      )
    })

    it('should propagate API errors', async () => {
      const error = new Error('Preview failed')

      mockApiClient.get.mockRejectedValue(error)

      await expect(schemaApi.previewTableData('my-database', 'users')).rejects.toThrow(
        'Preview failed'
      )
    })
  })

  describe('invalidateCache', () => {
    it('should invalidate cache for a data source', async () => {
      mockApiClient.post.mockResolvedValue({ data: null })

      await schemaApi.invalidateCache('my-database')

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/data-sources/my-database/cache/invalidate'
      )
    })

    it('should handle URL encoding for cache invalidation', async () => {
      mockApiClient.post.mockResolvedValue({ data: null })

      await schemaApi.invalidateCache('my database with spaces')

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/data-sources/my%20database%20with%20spaces/cache/invalidate'
      )
    })

    it('should propagate API errors', async () => {
      const error = new Error('Cache invalidation failed')

      mockApiClient.post.mockRejectedValue(error)

      await expect(schemaApi.invalidateCache('my-database')).rejects.toThrow(
        'Cache invalidation failed'
      )
    })

    it('should not return data', async () => {
      mockApiClient.post.mockResolvedValue({ data: null })

      const result = await schemaApi.invalidateCache('my-database')

      expect(result).toBeUndefined()
    })
  })

  describe('getTypeMappings', () => {
    it('should get type mappings for a table', async () => {
      const mockMappings: Record<string, TypeMapping> = {
        id: { source_type: 'integer', target_type: 'int', nullable: false },
        email: { source_type: 'varchar', target_type: 'string', nullable: false },
        age: { source_type: 'integer', target_type: 'int', nullable: true },
      }

      mockApiClient.get.mockResolvedValue({ data: mockMappings })

      const result = await schemaApi.getTypeMappings('my-database', 'users')

      expect(result).toEqual(mockMappings)
      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my-database/tables/users/type-mappings',
        { params: undefined }
      )
    })

    it('should get type mappings with schema filter', async () => {
      const mockMappings: Record<string, TypeMapping> = {
        id: { source_type: 'integer', target_type: 'int', nullable: false },
      }

      mockApiClient.get.mockResolvedValue({ data: mockMappings })

      await schemaApi.getTypeMappings('my-database', 'table1', { schema: 'public' })

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my-database/tables/table1/type-mappings',
        { params: { schema: 'public' } }
      )
    })

    it('should handle URL encoding for type mappings', async () => {
      mockApiClient.get.mockResolvedValue({ data: {} })

      await schemaApi.getTypeMappings('my database', 'my table')

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/my%20database/tables/my%20table/type-mappings',
        { params: undefined }
      )
    })

    it('should propagate API errors', async () => {
      const error = new Error('Type mapping failed')

      mockApiClient.get.mockRejectedValue(error)

      await expect(schemaApi.getTypeMappings('my-database', 'users')).rejects.toThrow(
        'Type mapping failed'
      )
    })

    it('should return empty object for tables with no columns', async () => {
      mockApiClient.get.mockResolvedValue({ data: {} })

      const result = await schemaApi.getTypeMappings('my-database', 'empty-table')

      expect(result).toEqual({})
    })
  })

  describe('edge cases', () => {
    it('should handle empty table name', async () => {
      mockApiClient.get.mockResolvedValue({
        data: { name: '', columns: [] },
      })

      await schemaApi.getTableSchema('my-database', '')

      expect(mockApiClient.get).toHaveBeenCalledWith('/data-sources/my-database/tables//schema', {
        params: undefined,
      })
    })

    it('should handle Unicode characters in names', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] })

      await schemaApi.listTables('データベース')

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/data-sources/%E3%83%87%E3%83%BC%E3%82%BF%E3%83%99%E3%83%BC%E3%82%B9/tables',
        { params: undefined }
      )
    })

    it('should handle very long data source names', async () => {
      const longName = 'a'.repeat(200)

      mockApiClient.get.mockResolvedValue({ data: [] })

      await schemaApi.listTables(longName)

      expect(mockApiClient.get).toHaveBeenCalledWith(`/data-sources/${longName}/tables`, {
        params: undefined,
      })
    })

    it('should handle undefined params gracefully', async () => {
      mockApiClient.get.mockResolvedValue({
        data: { columns: [], rows: [], total_rows: 0 },
      })

      await schemaApi.previewTableData('db', 'table', undefined)

      expect(mockApiClient.get).toHaveBeenCalledWith('/data-sources/db/tables/table/preview', {
        params: undefined,
      })
    })
  })

  describe('error handling', () => {
    it('should handle 404 errors', async () => {
      const error = {
        response: { status: 404 },
        message: 'Not found',
      }

      mockApiClient.get.mockRejectedValue(error)

      await expect(schemaApi.getTableSchema('db', 'nonexistent')).rejects.toEqual(error)
    })

    it('should handle 500 errors', async () => {
      const error = {
        response: { status: 500 },
        message: 'Internal server error',
      }

      mockApiClient.get.mockRejectedValue(error)

      await expect(schemaApi.listTables('db')).rejects.toEqual(error)
    })

    it('should handle timeout errors', async () => {
      const error = {
        code: 'ECONNABORTED',
        message: 'Request timeout',
      }

      mockApiClient.get.mockRejectedValue(error)

      await expect(schemaApi.previewTableData('db', 'table')).rejects.toEqual(error)
    })

    it('should handle network errors', async () => {
      const error = {
        code: 'ENETUNREACH',
        message: 'Network unreachable',
      }

      mockApiClient.post.mockRejectedValue(error)

      await expect(schemaApi.invalidateCache('db')).rejects.toEqual(error)
    })
  })
})
