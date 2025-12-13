import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import type {
  DataSourceConfig,
  DataSourceTestResult,
  DataSourceStatus,
} from '@/types/data-source'

export const useDataSourceStore = defineStore('dataSource', () => {
  // State
  const dataSources = ref<DataSourceConfig[]>([])
  const selectedDataSource = ref<DataSourceConfig | null>(null)
  const testResults = ref<Map<string, DataSourceTestResult>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)

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

  return {
    // State
    dataSources,
    selectedDataSource,
    testResults,
    loading,
    error,

    // Getters
    dataSourceCount,
    sortedDataSources,
    dataSourceByName,
    dataSourcesByType,
    databaseSources,
    fileSources,
    getTestResult,

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
  }
})
