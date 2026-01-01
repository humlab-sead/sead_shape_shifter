import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDataSourceStore } from '../data-source'
import * as api from '@/api'
import * as schemaApi from '@/api/schema'
import type { DataSourceConfig, DataSourceTestResult, DataSourceStatus } from '@/types/data-source'
import type { TableMetadata, TableSchema, PreviewData } from '@/types/schema'

// Mock the API modules
vi.mock('@/api', () => ({
  api: {
    dataSources: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      testConnection: vi.fn(),
      getStatus: vi.fn(),
    },
  },
}))

vi.mock('@/api/schema', () => ({
  default: {
    listTables: vi.fn(),
    getTableSchema: vi.fn(),
    previewTableData: vi.fn(),
    invalidateCache: vi.fn(),
  },
}))

const mockApi = api.api.dataSources as any
const mockSchemaApi = (schemaApi as any).default

describe('useDataSourceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should initialize with empty state', () => {
      const store = useDataSourceStore()

      expect(store.dataSources).toEqual([])
      expect(store.selectedDataSource).toBeNull()
      expect(store.testResults).toBeInstanceOf(Map)
      expect(store.testResults.size).toBe(0)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.tables).toBeInstanceOf(Map)
      expect(store.tableSchemas).toBeInstanceOf(Map)
      expect(store.schemaLoading).toBe(false)
      expect(store.schemaError).toBeNull()
    })
  })

  describe('getters', () => {
    it('should compute dataSourceCount', () => {
      const store = useDataSourceStore()

      expect(store.dataSourceCount).toBe(0)

      store.dataSources = [
        { name: 'ds1', driver: 'postgresql' },
        { name: 'ds2', driver: 'csv' },
      ] as DataSourceConfig[]

      expect(store.dataSourceCount).toBe(2)
    })

    it('should sort data sources alphabetically', () => {
      const store = useDataSourceStore()

      store.dataSources = [
        { name: 'zebra', driver: 'postgresql' },
        { name: 'alpha', driver: 'csv' },
        { name: 'beta', driver: 'sqlite' },
      ] as DataSourceConfig[]

      expect(store.sortedDataSources.map((ds) => ds.name)).toEqual(['alpha', 'beta', 'zebra'])
    })

    it('should find data source by name', () => {
      const store = useDataSourceStore()
      const ds1: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }
      const ds2: DataSourceConfig = { name: 'ds2', driver: 'csv' }

      store.dataSources = [ds1, ds2]

      expect(store.dataSourceByName('ds1')).toEqual(ds1)
      expect(store.dataSourceByName('ds2')).toEqual(ds2)
      expect(store.dataSourceByName('nonexistent')).toBeUndefined()
    })

    it('should group data sources by type', () => {
      const store = useDataSourceStore()

      store.dataSources = [
        { name: 'pg1', driver: 'postgresql' },
        { name: 'pg2', driver: 'postgresql' },
        { name: 'csv1', driver: 'csv' },
      ] as DataSourceConfig[]

      const grouped = store.dataSourcesByType

      expect(grouped['postgresql']?.length).toBe(2)
      expect(grouped['csv']?.length).toBe(1)
    })

    it('should filter database sources', () => {
      const store = useDataSourceStore()

      store.dataSources = [
        { name: 'pg', driver: 'postgresql' },
        { name: 'sqlite', driver: 'sqlite' },
        { name: 'csv', driver: 'csv' },
        { name: 'access', driver: 'access' },
      ] as DataSourceConfig[]

      expect(store.databaseSources.length).toBe(3)
      expect(store.databaseSources.map((ds) => ds.driver)).toEqual(['postgresql', 'sqlite', 'access'])
    })

    it('should filter file sources', () => {
      const store = useDataSourceStore()

      store.dataSources = [
        { name: 'pg', driver: 'postgresql' },
        { name: 'csv1', driver: 'csv' },
        { name: 'csv2', driver: 'csv' },
      ] as DataSourceConfig[]

      expect(store.fileSources.length).toBe(2)
      expect(store.fileSources.map((ds) => ds.driver)).toEqual(['csv', 'csv'])
    })

    it('should get test result by name', () => {
      const store = useDataSourceStore()
      const testResult: DataSourceTestResult = {
        success: true,
        message: 'Connection successful',
        connection_time_ms: 0,
      }

      store.testResults.set('ds1', testResult)

      expect(store.getTestResult('ds1')).toEqual(testResult)
      expect(store.getTestResult('nonexistent')).toBeUndefined()
    })

    it('should get tables for data source', () => {
      const store = useDataSourceStore()
      const tables: TableMetadata[] = [
        { name: 'table1', row_count: 100 },
        { name: 'table2', row_count: 200 },
      ]

      store.tables.set('ds1', tables)

      expect(store.getTablesForDataSource('ds1')).toEqual(tables)
      expect(store.getTablesForDataSource('nonexistent')).toEqual([])
    })

    it('should get tables with schema', () => {
      const store = useDataSourceStore()
      const tables: TableMetadata[] = [{ name: 'table1', row_count: 100 }]

      store.tables.set('ds1:public', tables)

      expect(store.getTablesForDataSource('ds1', 'public')).toEqual(tables)
    })

    it('should get table schema', () => {
      const store = useDataSourceStore()
      const schema: TableSchema = {
        table_name: 'table1',
        columns: [{ name: 'id', data_type: 'integer', nullable: false, is_primary_key: false }],
        primary_keys: [],
      }

      store.tableSchemas.set('ds1:table1', schema)

      expect(store.getTableSchema('ds1', 'table1')).toEqual(schema)
      expect(store.getTableSchema('ds1', 'nonexistent')).toBeUndefined()
    })
  })

  describe('fetchDataSources', () => {
    it('should fetch data sources successfully', async () => {
      const store = useDataSourceStore()
      const mockDataSources: DataSourceConfig[] = [
        { name: 'ds1', driver: 'postgresql' },
        { name: 'ds2', driver: 'csv' },
      ]

      mockApi.list.mockResolvedValue(mockDataSources)

      await store.fetchDataSources()

      expect(store.dataSources).toEqual(mockDataSources)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should handle fetch errors', async () => {
      const store = useDataSourceStore()
      const error = new Error('Failed to fetch')

      mockApi.list.mockRejectedValue(error)

      await expect(store.fetchDataSources()).rejects.toThrow('Failed to fetch')

      expect(store.error).toBe('Failed to fetch')
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchDataSource', () => {
    it('should fetch a single data source', async () => {
      const store = useDataSourceStore()
      const mockDataSource: DataSourceConfig = {
        name: 'ds1',
        driver: 'postgresql',
      }

      mockApi.get.mockResolvedValue(mockDataSource)

      const result = await store.fetchDataSource('ds1')

      expect(result).toEqual(mockDataSource)
      expect(store.selectedDataSource).toEqual(mockDataSource)
      expect(store.loading).toBe(false)
    })

    it('should update data source in list if exists', async () => {
      const store = useDataSourceStore()
      const existing: DataSourceConfig = { name: 'ds1', driver: 'postgresql', host: 'old' }
      const updated: DataSourceConfig = { name: 'ds1', driver: 'postgresql', host: 'new' }

      store.dataSources = [existing]

      mockApi.get.mockResolvedValue(updated)

      await store.fetchDataSource('ds1')

      expect(store.dataSources[0]).toEqual(updated)
    })

    it('should handle fetch errors', async () => {
      const store = useDataSourceStore()
      const error = new Error('Not found')

      mockApi.get.mockRejectedValue(error)

      await expect(store.fetchDataSource('ds1')).rejects.toThrow('Not found')

      expect(store.error).toBe('Not found')
    })
  })

  describe('createDataSource', () => {
    it('should create a data source', async () => {
      const store = useDataSourceStore()
      const newDataSource: DataSourceConfig = {
        name: 'new-ds',
        driver: 'postgresql',
      }

      mockApi.create.mockResolvedValue(newDataSource)

      const result = await store.createDataSource(newDataSource)

      expect(result).toEqual(newDataSource)
      expect(store.dataSources).toContainEqual(newDataSource)
      expect(store.loading).toBe(false)
    })

    it('should handle creation errors', async () => {
      const store = useDataSourceStore()
      const newDataSource: DataSourceConfig = {
        name: 'new-ds',
        driver: 'postgresql',
      }
      const error = new Error('Creation failed')

      mockApi.create.mockRejectedValue(error)

      await expect(store.createDataSource(newDataSource)).rejects.toThrow('Creation failed')

      expect(store.error).toBe('Creation failed')
      expect(store.dataSources.length).toBe(0)
    })
  })

  describe('updateDataSource', () => {
    it('should update a data source', async () => {
      const store = useDataSourceStore()
      const existing: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }
      const updated: DataSourceConfig = { name: 'ds1', driver: 'postgresql', host: 'new' }

      store.dataSources = [existing]

      mockApi.update.mockResolvedValue(updated)

      const result = await store.updateDataSource('ds1', updated)

      expect(result).toEqual(updated)
      expect(store.dataSources[0]).toEqual(updated)
      expect(store.loading).toBe(false)
    })

    it('should handle rename (replace entry)', async () => {
      const store = useDataSourceStore()
      const existing: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }
      const renamed: DataSourceConfig = { name: 'ds2', driver: 'postgresql' }

      store.dataSources = [existing]

      mockApi.update.mockResolvedValue(renamed)

      await store.updateDataSource('ds1', renamed)

      expect(store.dataSources.find((ds) => ds.name === 'ds1')).toBeUndefined()
      expect(store.dataSources.find((ds) => ds.name === 'ds2')).toEqual(renamed)
    })

    it('should update selected data source if it matches', async () => {
      const store = useDataSourceStore()
      const existing: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }
      const updated: DataSourceConfig = { name: 'ds1', driver: 'postgresql', host: 'new' }

      store.dataSources = [existing]
      store.selectedDataSource = existing

      mockApi.update.mockResolvedValue(updated)

      await store.updateDataSource('ds1', updated)

      expect(store.selectedDataSource).toEqual(updated)
    })

    it('should handle update errors', async () => {
      const store = useDataSourceStore()
      const existing: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }
      const error = new Error('Update failed')

      store.dataSources = [existing]

      mockApi.update.mockRejectedValue(error)

      await expect(store.updateDataSource('ds1', existing)).rejects.toThrow('Update failed')

      expect(store.error).toBe('Update failed')
    })
  })

  describe('deleteDataSource', () => {
    it('should delete a data source', async () => {
      const store = useDataSourceStore()
      const ds1: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }
      const ds2: DataSourceConfig = { name: 'ds2', driver: 'csv' }

      store.dataSources = [ds1, ds2]

      mockApi.delete.mockResolvedValue(undefined)

      await store.deleteDataSource('ds1')

      expect(store.dataSources).toEqual([ds2])
      expect(store.loading).toBe(false)
    })

    it('should clear test result on delete', async () => {
      const store = useDataSourceStore()
      const ds: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }

      store.dataSources = [ds]
      store.testResults.set('ds1', { success: true, message: 'OK', connection_time_ms: 0 })

      mockApi.delete.mockResolvedValue(undefined)

      await store.deleteDataSource('ds1')

      expect(store.testResults.has('ds1')).toBe(false)
    })

    it('should clear selected data source if deleted', async () => {
      const store = useDataSourceStore()
      const ds: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }

      store.dataSources = [ds]
      store.selectedDataSource = ds

      mockApi.delete.mockResolvedValue(undefined)

      await store.deleteDataSource('ds1')

      expect(store.selectedDataSource).toBeNull()
    })

    it('should handle delete errors', async () => {
      const store = useDataSourceStore()
      const error = new Error('Delete failed')

      mockApi.delete.mockRejectedValue(error)

      await expect(store.deleteDataSource('ds1')).rejects.toThrow('Delete failed')

      expect(store.error).toBe('Delete failed')
    })
  })

  describe('testConnection', () => {
    it('should test connection successfully', async () => {
      const store = useDataSourceStore()
      const testResult: DataSourceTestResult = {
        success: true,
        message: 'Connection successful',
        connection_time_ms: 0,
      }

      mockApi.testConnection.mockResolvedValue(testResult)

      const result = await store.testConnection('ds1')

      expect(result).toEqual(testResult)
      expect(store.testResults.get('ds1')).toEqual(testResult)
      expect(store.loading).toBe(false)
    })

    it('should handle test connection errors', async () => {
      const store = useDataSourceStore()
      const error = new Error('Connection failed')

      mockApi.testConnection.mockRejectedValue(error)

      await expect(store.testConnection('ds1')).rejects.toThrow('Connection failed')

      expect(store.error).toBe('Connection failed')
    })
  })

  describe('getStatus', () => {
    it('should get data source status', async () => {
      const store = useDataSourceStore()
      const status: DataSourceStatus = {
        name: 'ds1',
        is_connected: true,
        last_test_result: null,
        in_use_by_entities: [],
      }

      mockApi.getStatus.mockResolvedValue(status)

      const result = await store.getStatus('ds1')

      expect(result).toEqual(status)
      expect(store.loading).toBe(false)
    })

    it('should handle status errors', async () => {
      const store = useDataSourceStore()
      const error = new Error('Status check failed')

      mockApi.getStatus.mockRejectedValue(error)

      await expect(store.getStatus('ds1')).rejects.toThrow('Status check failed')

      expect(store.error).toBe('Status check failed')
    })
  })

  describe('selectDataSource', () => {
    it('should select a data source', () => {
      const store = useDataSourceStore()
      const ds: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }

      store.selectDataSource(ds)

      expect(store.selectedDataSource).toEqual(ds)
    })

    it('should clear selection', () => {
      const store = useDataSourceStore()
      const ds: DataSourceConfig = { name: 'ds1', driver: 'postgresql' }

      store.selectedDataSource = ds

      store.selectDataSource(null)

      expect(store.selectedDataSource).toBeNull()
    })
  })

  describe('clearError', () => {
    it('should clear error state', () => {
      const store = useDataSourceStore()

      store.$patch({ error: 'Some error' })

      store.clearError()

      expect(store.error).toBeNull()
    })
  })

  describe('clearTestResult', () => {
    it('should clear test result for a data source', () => {
      const store = useDataSourceStore()

      store.testResults.set('ds1', { success: true, message: 'OK', connection_time_ms: 0 })

      store.clearTestResult('ds1')

      expect(store.testResults.has('ds1')).toBe(false)
    })
  })

  describe('fetchTables', () => {
    it('should fetch tables for a data source', async () => {
      const store = useDataSourceStore()
      const tables: TableMetadata[] = [
        { name: 'table1', row_count: 100 },
        { name: 'table2', row_count: 200 },
      ]

      mockSchemaApi.listTables.mockResolvedValue(tables)

      const result = await store.fetchTables('ds1')

      expect(result).toEqual(tables)
      expect(store.tables.get('ds1')).toEqual(tables)
      expect(store.schemaLoading).toBe(false)
      expect(mockSchemaApi.listTables).toHaveBeenCalledWith('ds1', {})
    })

    it('should fetch tables with schema filter', async () => {
      const store = useDataSourceStore()
      const tables: TableMetadata[] = [{ name: 'table1', row_count: 100 }]

      mockSchemaApi.listTables.mockResolvedValue(tables)

      await store.fetchTables('ds1', 'public')

      expect(store.tables.get('ds1:public')).toEqual(tables)
      expect(mockSchemaApi.listTables).toHaveBeenCalledWith('ds1', { schema: 'public' })
    })

    it('should handle fetch tables errors', async () => {
      const store = useDataSourceStore()
      const error = new Error('Fetch failed')

      mockSchemaApi.listTables.mockRejectedValue(error)

      await expect(store.fetchTables('ds1')).rejects.toThrow('Fetch failed')

      expect(store.schemaError).toBe('Fetch failed')
      expect(store.schemaLoading).toBe(false)
    })
  })

  describe('fetchTableSchema', () => {
    it('should fetch table schema', async () => {
      const store = useDataSourceStore()
      const schema: TableSchema = {
        table_name: 'table1',
        columns: [
          { name: 'id', data_type: 'integer', nullable: false, is_primary_key: false },
          { name: 'name', data_type: 'varchar', nullable: true, is_primary_key: false },
        ],
        primary_keys: [],
      }

      mockSchemaApi.getTableSchema.mockResolvedValue(schema)

      const result = await store.fetchTableSchema('ds1', 'table1')

      expect(result).toEqual(schema)
      expect(store.tableSchemas.get('ds1:table1')).toEqual(schema)
      expect(store.schemaLoading).toBe(false)
    })

    it('should fetch table schema with schema filter', async () => {
      const store = useDataSourceStore()
      const schema: TableSchema = {
        table_name: 'table1',
        columns: [{ name: 'id', data_type: 'integer', nullable: false, is_primary_key: false }],
        primary_keys: [],
      }

      mockSchemaApi.getTableSchema.mockResolvedValue(schema)

      await store.fetchTableSchema('ds1', 'table1', 'public')

      expect(store.tableSchemas.get('ds1:public:table1')).toEqual(schema)
      expect(mockSchemaApi.getTableSchema).toHaveBeenCalledWith('ds1', 'table1', { schema: 'public' })
    })

    it('should handle fetch schema errors', async () => {
      const store = useDataSourceStore()
      const error = new Error('Schema fetch failed')

      mockSchemaApi.getTableSchema.mockRejectedValue(error)

      await expect(store.fetchTableSchema('ds1', 'table1')).rejects.toThrow('Schema fetch failed')

      expect(store.schemaError).toBe('Schema fetch failed')
    })
  })

  describe('previewTable', () => {
    it('should preview table data', async () => {
      const store = useDataSourceStore()
      const previewData: PreviewData = {
        columns: ['id', 'name'],
        rows: [
          { id: 1, name: 'Alice' },
          { id: 2, name: 'Bob' },
        ],
        total_rows: 2,
        limit: 2,
        offset: 0,
      }

      mockSchemaApi.previewTableData.mockResolvedValue(previewData)

      const result = await store.previewTable('ds1', 'table1')

      expect(result).toEqual(previewData)
      expect(store.schemaLoading).toBe(false)
    })

    it('should preview with parameters', async () => {
      const store = useDataSourceStore()
      const previewData: PreviewData = {
        columns: ['id'],
        rows: [{ id: 1 }],
        total_rows: 1,
        limit: 10,
        offset: 5,
      }

      mockSchemaApi.previewTableData.mockResolvedValue(previewData)

      await store.previewTable('ds1', 'table1', { limit: 10, offset: 5, schema: 'public' })

      expect(mockSchemaApi.previewTableData).toHaveBeenCalledWith('ds1', 'table1', {
        limit: 10,
        offset: 5,
        schema: 'public',
      })
    })

    it('should handle preview errors', async () => {
      const store = useDataSourceStore()
      const error = new Error('Preview failed')

      mockSchemaApi.previewTableData.mockRejectedValue(error)

      await expect(store.previewTable('ds1', 'table1')).rejects.toThrow('Preview failed')

      expect(store.schemaError).toBe('Preview failed')
    })
  })

  describe('invalidateSchemaCache', () => {
    it('should invalidate cache and clear local cache', async () => {
      const store = useDataSourceStore()

      store.tables.set('ds1', [{ name: 'table1', row_count: 100 }])
      store.tables.set('ds2', [{ name: 'table2', row_count: 200 }])
      store.tableSchemas.set('ds1:table1', {
        table_name: 'table1',
        columns: [{ name: 'id', data_type: 'integer', nullable: false, is_primary_key: false }],
        primary_keys: [],
      })
      store.tableSchemas.set('ds2:table2', {
        table_name: 'table2',
        columns: [{ name: 'id', data_type: 'integer', nullable: false, is_primary_key: false }],
        primary_keys: [],
      })

      mockSchemaApi.invalidateCache.mockResolvedValue(undefined)

      await store.invalidateSchemaCache('ds1')

      expect(store.tables.has('ds1')).toBe(false)
      expect(store.tables.has('ds2')).toBe(true)
      expect(store.tableSchemas.has('ds1:table1')).toBe(false)
      expect(store.tableSchemas.has('ds2:table2')).toBe(true)
      expect(mockSchemaApi.invalidateCache).toHaveBeenCalledWith('ds1')
    })

    it('should clear nested schema cache', async () => {
      const store = useDataSourceStore()

      store.tables.set('ds1:public', [{ name: 'table1', row_count: 100 }])
      store.tableSchemas.set('ds1:public:table1', {
        table_name: 'table1',
        columns: [{ name: 'id', data_type: 'integer', nullable: false, is_primary_key: false }],
        primary_keys: [],
      })

      mockSchemaApi.invalidateCache.mockResolvedValue(undefined)

      await store.invalidateSchemaCache('ds1')

      expect(store.tables.has('ds1:public')).toBe(false)
      expect(store.tableSchemas.has('ds1:public:table1')).toBe(false)
    })

    it('should handle invalidation errors', async () => {
      const store = useDataSourceStore()
      const error = new Error('Invalidation failed')

      mockSchemaApi.invalidateCache.mockRejectedValue(error)

      await expect(store.invalidateSchemaCache('ds1')).rejects.toThrow('Invalidation failed')

      expect(store.schemaError).toBe('Invalidation failed')
    })
  })

  describe('clearSchemaError', () => {
    it('should clear schema error state', () => {
      const store = useDataSourceStore()

      store.$patch({ schemaError: 'Some error' })

      store.clearSchemaError()

      expect(store.schemaError).toBeNull()
    })
  })
})
