import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import schemaApi from '@/api/schema'
import type { DataSourceConfig, DataSourceTestResult, DataSourceStatus } from '@/types/data-source'
import type { TableMetadata, TableSchema, PreviewData, PreviewTableDataParams } from '@/types/schema'

export const useDataSourceStore = defineStore('dataSource', () => {
  // State
  const dataSources = ref<DataSourceConfig[]>([])
  const selectedDataSource = ref<DataSourceConfig | null>(null)
  const testResults = ref<Map<string, DataSourceTestResult>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Schema state
  const tables = ref<Map<string, TableMetadata[]>>(new Map())
  const tableSchemas = ref<Map<string, TableSchema>>(new Map())
  const schemaLoading = ref(false)
  const schemaError = ref<string | null>(null)

  // Getters
  const dataSourceCount = computed(() => dataSources.value.length)

  const sortedDataSources = computed(() => {
    return [...dataSources.value].sort((a, b) => a.name.localeCompare(b.name))
  })

  const dataSourceByName = computed(() => {
    return (name: string) => dataSources.value.find((ds) => ds.name === name)
  })

  const dataSourcesByType = computed(() => {
    const grouped: Record<string, DataSourceConfig[]> = {}
    dataSources.value.forEach((ds) => {
      const type = ds.driver
      if (!grouped[type]) {
        grouped[type] = []
      }
      grouped[type].push(ds)
    })
    return grouped
  })

  const databaseSources = computed(() => {
    return dataSources.value.filter((ds) =>
      ['postgresql', 'postgres', 'access', 'ucanaccess', 'sqlite'].includes(ds.driver)
    )
  })

  const fileSources = computed(() => {
    return dataSources.value.filter((ds) => ds.driver === 'csv')
  })

  const getTestResult = computed(() => {
    return (name: string) => testResults.value.get(name)
  })

  // Actions
  async function fetchDataSources() {
    loading.value = true
    error.value = null
    try {
      dataSources.value = await api.dataSources.list()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch data sources'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchDataSource(name: string) {
    loading.value = true
    error.value = null
    try {
      const dataSource = await api.dataSources.get(name)
      selectedDataSource.value = dataSource
      // Update in list if exists
      const index = dataSources.value.findIndex((ds) => ds.name === name)
      if (index !== -1) {
        dataSources.value[index] = dataSource
      }
      return dataSource
    } catch (e) {
      error.value = e instanceof Error ? e.message : `Failed to fetch data source '${name}'`
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createDataSource(config: DataSourceConfig) {
    loading.value = true
    error.value = null
    try {
      const created = await api.dataSources.create(config)
      dataSources.value.push(created)
      return created
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create data source'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateDataSource(name: string, config: DataSourceConfig) {
    loading.value = true
    error.value = null
    try {
      const updated = await api.dataSources.update(name, config)

      // Update in list
      const index = dataSources.value.findIndex((ds) => ds.name === name)
      if (index !== -1) {
        // If renamed, replace entry; otherwise update
        if (name !== config.name) {
          dataSources.value.splice(index, 1)
          dataSources.value.push(updated)
        } else {
          dataSources.value[index] = updated
        }
      }

      // Update selected if it's the current one
      if (selectedDataSource.value?.name === name) {
        selectedDataSource.value = updated
      }

      return updated
    } catch (e) {
      error.value = e instanceof Error ? e.message : `Failed to update data source '${name}'`
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteDataSource(name: string) {
    loading.value = true
    error.value = null
    try {
      await api.dataSources.delete(name)

      // Remove from list
      const index = dataSources.value.findIndex((ds) => ds.name === name)
      if (index !== -1) {
        dataSources.value.splice(index, 1)
      }

      // Clear test result
      testResults.value.delete(name)

      // Clear selected if it's the deleted one
      if (selectedDataSource.value?.name === name) {
        selectedDataSource.value = null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : `Failed to delete data source '${name}'`
      throw e
    } finally {
      loading.value = false
    }
  }

  async function testConnection(name: string): Promise<DataSourceTestResult> {
    loading.value = true
    error.value = null
    try {
      const result = await api.dataSources.testConnection(name)
      testResults.value.set(name, result)
      return result
    } catch (e) {
      error.value = e instanceof Error ? e.message : `Failed to test connection to '${name}'`
      throw e
    } finally {
      loading.value = false
    }
  }

  async function getStatus(name: string): Promise<DataSourceStatus> {
    loading.value = true
    error.value = null
    try {
      return await api.dataSources.getStatus(name)
    } catch (e) {
      error.value = e instanceof Error ? e.message : `Failed to get status for '${name}'`
      throw e
    } finally {
      loading.value = false
    }
  }

  function selectDataSource(dataSource: DataSourceConfig | null) {
    selectedDataSource.value = dataSource
  }

  function clearError() {
    error.value = null
  }

  function clearTestResult(name: string) {
    testResults.value.delete(name)
  }

  // Schema Actions
  async function fetchTables(dataSourceName: string, schema?: string) {
    schemaLoading.value = true
    schemaError.value = null
    try {
      const result = await schemaApi.listTables(dataSourceName, { schema })
      const key = schema ? `${dataSourceName}:${schema}` : dataSourceName
      tables.value.set(key, result)
      return result
    } catch (e) {
      schemaError.value = e instanceof Error ? e.message : `Failed to fetch tables for '${dataSourceName}'`
      throw e
    } finally {
      schemaLoading.value = false
    }
  }

  async function fetchTableSchema(dataSourceName: string, tableName: string, schema?: string) {
    schemaLoading.value = true
    schemaError.value = null
    try {
      const result = await schemaApi.getTableSchema(dataSourceName, tableName, { schema })
      const key = schema ? `${dataSourceName}:${schema}:${tableName}` : `${dataSourceName}:${tableName}`
      tableSchemas.value.set(key, result)
      return result
    } catch (e) {
      schemaError.value = e instanceof Error ? e.message : `Failed to fetch schema for '${tableName}'`
      throw e
    } finally {
      schemaLoading.value = false
    }
  }

  async function previewTable(
    dataSourceName: string,
    tableName: string,
    params?: PreviewTableDataParams
  ): Promise<PreviewData> {
    schemaLoading.value = true
    schemaError.value = null
    try {
      return await schemaApi.previewTableData(dataSourceName, tableName, params)
    } catch (e) {
      schemaError.value = e instanceof Error ? e.message : `Failed to preview '${tableName}'`
      throw e
    } finally {
      schemaLoading.value = false
    }
  }

  async function invalidateSchemaCache(dataSourceName: string) {
    schemaLoading.value = true
    schemaError.value = null
    try {
      await schemaApi.invalidateCache(dataSourceName)
      // Clear local cache
      const keysToDelete: string[] = []
      tables.value.forEach((_, key) => {
        if (key.startsWith(dataSourceName)) {
          keysToDelete.push(key)
        }
      })
      keysToDelete.forEach((key) => tables.value.delete(key))

      const schemaKeysToDelete: string[] = []
      tableSchemas.value.forEach((_, key) => {
        if (key.startsWith(dataSourceName)) {
          schemaKeysToDelete.push(key)
        }
      })
      schemaKeysToDelete.forEach((key) => tableSchemas.value.delete(key))
    } catch (e) {
      schemaError.value = e instanceof Error ? e.message : `Failed to invalidate cache for '${dataSourceName}'`
      throw e
    } finally {
      schemaLoading.value = false
    }
  }

  function clearSchemaError() {
    schemaError.value = null
  }

  // Schema Getters
  const getTablesForDataSource = computed(() => {
    return (dataSourceName: string, schema?: string) => {
      const key = schema ? `${dataSourceName}:${schema}` : dataSourceName
      return tables.value.get(key) || []
    }
  })

  const getTableSchema = computed(() => {
    return (dataSourceName: string, tableName: string, schema?: string) => {
      const key = schema ? `${dataSourceName}:${schema}:${tableName}` : `${dataSourceName}:${tableName}`
      return tableSchemas.value.get(key)
    }
  })

  return {
    // State
    dataSources,
    selectedDataSource,
    testResults,
    loading,
    error,
    tables,
    tableSchemas,
    schemaLoading,
    schemaError,

    // Getters
    dataSourceCount,
    sortedDataSources,
    dataSourceByName,
    dataSourcesByType,
    databaseSources,
    fileSources,
    getTestResult,
    getTablesForDataSource,
    getTableSchema,

    // Actions
    fetchDataSources,
    fetchDataSource,
    createDataSource,
    updateDataSource,
    deleteDataSource,
    testConnection,
    getStatus,
    selectDataSource,
    clearError,
    clearTestResult,
    fetchTables,
    fetchTableSchema,
    previewTable,
    invalidateSchemaCache,
    clearSchemaError,
  }
})
