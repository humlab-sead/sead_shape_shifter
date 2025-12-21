<template>
  <v-container fluid class="pa-6">
    <v-row>
      <v-col>
        <h1 class="text-h4 mb-2">Global Data Sources</h1>
        <p class="text-body-2 text-grey">
          Manage global data source files. These can be connected to configurations via @include references.
        </p>
      </v-col>
    </v-row>

    <!-- Info Banner -->
    <v-row class="mt-2">
      <v-col>
        <v-alert
          type="info"
          variant="tonal"
          density="compact"
          border="start"
        >
          <strong>Shared Data Sources</strong> - Data sources are stored as separate YAML files
          and can be connected to multiple configurations. To connect a data source to a
          configuration, go to the configuration's "Data Sources" tab.
        </v-alert>
      </v-col>
    </v-row>

    <!-- Toolbar -->
    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="searchQuery"
          prepend-inner-icon="mdi-magnify"
          label="Search data sources"
          variant="outlined"
          density="compact"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="filterType"
          :items="filterOptions"
          label="Filter by type"
          variant="outlined"
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="3" class="text-right">
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="handleCreate"
        >
          New Data Source
        </v-btn>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="loading" class="mt-4">
      <v-col cols="12" class="text-center py-12">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-grey">Loading data sources...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" variant="tonal" class="mt-4">
      <v-alert-title>Error Loading Data Sources</v-alert-title>
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="handleRefresh">Retry</v-btn>
      </template>
    </v-alert>

    <!-- Empty State -->
    <v-row v-else-if="isEmpty" class="mt-4">
      <v-col cols="12">
        <v-card variant="outlined" class="text-center py-12">
          <v-icon icon="mdi-database-off-outline" size="64" color="grey" />
          <h3 class="text-h6 mt-4 mb-2">No Data Sources Configured</h3>
          <p class="text-grey mb-4">
            Add a database or file connection to start working with data
          </p>
          <v-btn
            color="primary"
            prepend-icon="mdi-plus"
            @click="handleCreate"
          >
            Add Data Source
          </v-btn>
        </v-card>
      </v-col>
    </v-row>

    <!-- Data Source Cards -->
    <v-row v-else class="mt-4">
      <v-col
        v-for="dataSource in filteredDataSources"
        :key="dataSource.name"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card variant="outlined" class="h-100" hover>
          <v-card-title class="d-flex align-center">
            <v-icon :icon="getDriverIcon(dataSource.driver)" class="mr-2" />
            {{ dataSource.name }}
            <v-spacer />
            <v-chip
              :color="getDriverColor(dataSource.driver)"
              size="small"
              label
            >
              {{ getDriverDisplayName(dataSource.driver) }}
            </v-chip>
          </v-card-title>

          <v-card-text>
            <div v-if="isDatabaseSource(dataSource.driver)" class="text-body-2">
              <div class="d-flex align-center mb-1">
                <v-icon icon="mdi-server" size="small" class="mr-2" />
                <span class="text-grey">Host:</span>
                <span class="ml-1 font-weight-medium">{{ dataSource.host }}</span>
              </div>
              <div class="d-flex align-center mb-1">
                <v-icon icon="mdi-database" size="small" class="mr-2" />
                <span class="text-grey">Database:</span>
                <span class="ml-1 font-weight-medium">
                  {{ dataSource.database || dataSource.dbname }}
                </span>
              </div>
              <div class="d-flex align-center">
                <v-icon icon="mdi-account" size="small" class="mr-2" />
                <span class="text-grey">User:</span>
                <span class="ml-1 font-weight-medium">{{ dataSource.username }}</span>
              </div>
            </div>
            <div v-else class="text-body-2">
              <div class="d-flex align-center">
                <v-icon icon="mdi-file" size="small" class="mr-2" />
                <span class="text-grey">File:</span>
                <span class="ml-1 font-weight-medium text-truncate">
                  {{ dataSource.filename || dataSource.file_path }}
                </span>
              </div>
            </div>

            <div v-if="dataSource.description" class="mt-3 text-body-2 text-grey">
              {{ dataSource.description }}
            </div>

            <!-- Test Result -->
            <div v-if="getTestResult(dataSource.name)" class="mt-3">
              <v-alert
                :type="getTestResult(dataSource.name)?.success ? 'success' : 'error'"
                density="compact"
                variant="tonal"
              >
                <div class="d-flex align-center">
                  <v-icon
                    :icon="
                      getTestResult(dataSource.name)?.success
                        ? 'mdi-check-circle'
                        : 'mdi-alert-circle'
                    "
                    size="small"
                    class="mr-2"
                  />
                  <div class="flex-grow-1">
                    <div class="text-caption">
                      {{ getTestResult(dataSource.name)?.message }}
                    </div>
                    <div v-if="getTestResult(dataSource.name)?.success" class="text-caption">
                      {{ getTestResult(dataSource.name)?.connection_time_ms }}ms
                    </div>
                  </div>
                </div>
              </v-alert>
            </div>
          </v-card-text>

          <v-card-actions>
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-connection"
              :loading="testingConnection === dataSource.name"
              @click="handleTestConnection(dataSource)"
            >
              Test
            </v-btn>
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-pencil"
              @click="handleEdit(dataSource)"
            >
              Edit
            </v-btn>
            <v-spacer />
            <v-btn
              size="small"
              variant="text"
              color="error"
              icon="mdi-delete"
              @click="handleDeleteConfirm(dataSource)"
            />
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Create/Edit Dialog -->
    <DataSourceFormDialog
      v-model="showFormDialog"
      :data-source="editingDataSource"
      @save="handleSave"
    />

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="500">
      <v-card>
        <v-card-title>Delete Data Source</v-card-title>
        <v-card-text>
          <p>
            Are you sure you want to delete data source
            <strong>{{ deletingDataSource?.name }}</strong>?
          </p>
          <v-alert
            v-if="deleteError"
            type="error"
            density="compact"
            variant="tonal"
            class="mt-3"
          >
            {{ deleteError }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn
            color="error"
            variant="flat"
            :loading="deleting"
            @click="handleDelete"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDataSourceStore } from '@/stores/data-source'
import { useConfigurationStore } from '@/stores/configuration'
import {
  getDriverDisplayName,
  getDriverIcon,
  isDatabaseSource,
  type DataSourceConfig,
} from '@/types/data-source'
import DataSourceFormDialog from '@/components/DataSourceFormDialog.vue'

const dataSourceStore = useDataSourceStore()

// State
const searchQuery = ref('')
const filterType = ref('all')
const showFormDialog = ref(false)
const editingDataSource = ref<DataSourceConfig | null>(null)
const showDeleteDialog = ref(false)
const deletingDataSource = ref<DataSourceConfig | null>(null)
const deleting = ref(false)
const deleteError = ref<string | null>(null)
const testingConnection = ref<string | null>(null)

// Filter options
const filterOptions = [
  { title: 'All Types', value: 'all' },
  { title: 'PostgreSQL', value: 'postgresql' },
  { title: 'MS Access', value: 'access' },
  { title: 'SQLite', value: 'sqlite' },
  { title: 'CSV Files', value: 'csv' },
]

// Computed
const loading = computed(() => dataSourceStore.loading)
const error = computed(() => dataSourceStore.error)
const dataSources = computed(() => dataSourceStore.sortedDataSources)

const filteredDataSources = computed(() => {
  let filtered = dataSources.value

  // Apply type filter
  if (filterType.value !== 'all') {
    filtered = filtered.filter((ds) => {
      const driver = ds.driver.toLowerCase()
      const filter = filterType.value.toLowerCase()
      return driver === filter || (filter === 'access' && driver === 'ucanaccess')
    })
  }

  // Apply search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter((ds) => {
      return (
        ds.name.toLowerCase().includes(query) ||
        ds.description?.toLowerCase().includes(query) ||
        ds.host?.toLowerCase().includes(query) ||
        ds.database?.toLowerCase().includes(query) ||
        ds.dbname?.toLowerCase().includes(query)
      )
    })
  }

  return filtered
})

const isEmpty = computed(() => {
  return !loading.value && !error.value && dataSources.value.length === 0
})

const getTestResult = computed(() => dataSourceStore.getTestResult)

// Methods
function getDriverColor(driver: string): string {
  const colors: Record<string, string> = {
    postgresql: 'blue',
    postgres: 'blue',
    access: 'orange',
    ucanaccess: 'orange',
    sqlite: 'green',
    csv: 'purple',
  }
  return colors[driver] || 'grey'
}

function handleCreate() {
  editingDataSource.value = null
  showFormDialog.value = true
}

function handleEdit(dataSource: DataSourceConfig) {
  editingDataSource.value = dataSource
  showFormDialog.value = true
}

async function handleSave() {
  showFormDialog.value = false
  editingDataSource.value = null
  await dataSourceStore.fetchDataSources()
}

function handleDeleteConfirm(dataSource: DataSourceConfig) {
  deletingDataSource.value = dataSource
  deleteError.value = null
  showDeleteDialog.value = true
}

async function handleDelete() {
  if (!deletingDataSource.value) return

  deleting.value = true
  deleteError.value = null

  try {
    await dataSourceStore.deleteDataSource(deletingDataSource.value.name)
    showDeleteDialog.value = false
    deletingDataSource.value = null
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : 'Failed to delete data source'
  } finally {
    deleting.value = false
  }
}

async function handleTestConnection(dataSource: DataSourceConfig) {
  testingConnection.value = dataSource.name
  try {
    await dataSourceStore.testConnection(dataSource.name)
  } catch (e) {
    console.error('Connection test failed:', e)
  } finally {
    testingConnection.value = null
  }
}

async function handleRefresh() {
  await dataSourceStore.fetchDataSources()
}

// Lifecycle
onMounted(async () => {
  // Fetch global data source files
  await dataSourceStore.fetchDataSources()
})
</script>
