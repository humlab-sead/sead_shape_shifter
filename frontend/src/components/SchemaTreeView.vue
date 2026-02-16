<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon icon="mdi-file-tree" class="mr-2" />
      Tables
      <v-spacer />
      <v-btn icon="mdi-refresh" size="small" variant="text" :loading="loading" @click="refreshTables" />
    </v-card-title>

    <v-card-text>
      <!-- Data Source Selector -->
      <v-select
        v-model="selectedDataSourceName"
        :items="databaseSources"
        item-title="name"
        item-value="name"
        label="Data Source"
        density="compact"
        variant="outlined"
        :disabled="loading"
        class="mb-2"
      >
        <template #prepend-inner>
          <v-icon icon="mdi-database" size="small" />
        </template>
      </v-select>

      <!-- Schema Selector (PostgreSQL only) -->
      <v-text-field
        v-if="isPostgreSQL"
        v-model="schemaFilter"
        label="Schema"
        density="compact"
        variant="outlined"
        clearable
        class="mb-2"
      >
        <template #prepend-inner>
          <v-icon icon="mdi-folder-outline" size="small" />
        </template>
      </v-text-field>

      <!-- Search -->
      <v-text-field
        v-model="searchQuery"
        label="Search tables"
        density="compact"
        variant="outlined"
        clearable
        class="mb-2"
      >
        <template #prepend-inner>
          <v-icon icon="mdi-magnify" size="small" />
        </template>
      </v-text-field>

      <!-- Error Display -->
      <v-alert
        v-if="error"
        type="error"
        variant="tonal"
        density="compact"
        closable
        class="mb-2"
        @click:close="clearError"
      >
        {{ error }}
      </v-alert>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" />
        <p class="text-caption mt-2">Loading tables...</p>
      </div>

      <!-- Empty State -->
      <v-alert v-else-if="!selectedDataSourceName" type="info" variant="tonal" density="compact">
        Select a data source to browse tables
      </v-alert>

      <v-alert v-else-if="filteredTables.length === 0 && !loading" type="info" variant="tonal" density="compact">
        No tables found
      </v-alert>

      <!-- Tables List -->
      <v-list v-else density="compact" class="pa-0">
        <v-list-item
          v-for="table in filteredTables"
          :key="table.name"
          :active="selectedTable?.name === table.name"
          :title="table.name"
          :subtitle="formatTableSubtitle(table)"
          @click="selectTable(table)"
        >
          <template #prepend>
            <v-icon :icon="getTableIcon()" size="small" />
          </template>

          <template #append>
            <v-chip v-if="table.row_count !== null && table.row_count !== undefined" size="x-small" variant="tonal">
              {{ formatRowCount(table.row_count) }}
            </v-chip>
          </template>
        </v-list-item>
      </v-list>
    </v-card-text>

    <v-card-actions v-if="filteredTables.length > 0">
      <v-chip size="small" variant="text">
        {{ filteredTables.length }} table{{ filteredTables.length !== 1 ? 's' : '' }}
      </v-chip>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useDataSourceStore } from '@/stores/data-source'
import type { TableMetadata } from '@/types/schema'
import { getTableIcon, formatRowCount } from '@/types/schema'

// Props
interface Props {
  autoLoad?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  autoLoad: true,
})

// Emits
const emit = defineEmits<{
  (e: 'table-selected', table: TableMetadata, dataSource: string, schema?: string): void
}>()

// Store
const dataSourceStore = useDataSourceStore()

// State
const selectedDataSourceName = ref<string | null>(null)
const schemaFilter = ref<string>('public')
const searchQuery = ref('')
const selectedTable = ref<TableMetadata | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// Computed
const databaseSources = computed(() => dataSourceStore.databaseSources)

const selectedDataSource = computed(() => {
  if (!selectedDataSourceName.value) return null
  return dataSourceStore.dataSourceByName(selectedDataSourceName.value)
})

const isPostgreSQL = computed(() => {
  const driver = selectedDataSource.value?.driver.toLowerCase()
  return driver === 'postgresql' || driver === 'postgres'
})

const tables = computed(() => {
  if (!selectedDataSourceName.value) return []
  const schema = isPostgreSQL.value ? schemaFilter.value : undefined
  return dataSourceStore.getTablesForDataSource(selectedDataSourceName.value, schema)
})

const filteredTables = computed(() => {
  if (!searchQuery.value) return tables.value

  const query = searchQuery.value.toLowerCase()
  return tables.value.filter(
    (table) =>
      table.name.toLowerCase().includes(query) || (table.comment && table.comment.toLowerCase().includes(query))
  )
})

// Methods
async function loadTables() {
  if (!selectedDataSourceName.value) return

  loading.value = true
  error.value = null

  try {
    const schema = isPostgreSQL.value ? schemaFilter.value : undefined
    await dataSourceStore.fetchTables(selectedDataSourceName.value, schema)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load tables'
  } finally {
    loading.value = false
  }
}

function refreshTables() {
  if (selectedDataSourceName.value) {
    // Invalidate cache and reload
    dataSourceStore
      .invalidateSchemaCache(selectedDataSourceName.value)
      .then(() => loadTables())
      .catch((e) => {
        error.value = e instanceof Error ? e.message : 'Failed to refresh tables'
      })
  }
}

function selectTable(table: TableMetadata) {
  selectedTable.value = table
  const schema = isPostgreSQL.value ? schemaFilter.value : undefined
  emit('table-selected', table, selectedDataSourceName.value!, schema)
}

function formatTableSubtitle(table: TableMetadata): string {
  const parts: string[] = []

  if (table.schema_name && table.schema_name !== 'public') {
    parts.push(table.schema_name)
  }

  if (table.comment) {
    parts.push(table.comment)
  }

  return parts.join(' • ')
}

function clearError() {
  error.value = null
}

// Watchers
watch(selectedDataSourceName, () => {
  selectedTable.value = null
  if (selectedDataSourceName.value && props.autoLoad) {
    loadTables()
  }
})

watch(schemaFilter, () => {
  if (selectedDataSourceName.value && isPostgreSQL.value && props.autoLoad) {
    loadTables()
  }
})

// Initialize - Fetch data sources on mount if autoLoad is true
onMounted(async () => {
  if (props.autoLoad && databaseSources.value.length === 0) {
    try {
      await dataSourceStore.fetchDataSources()
      if (databaseSources.value.length > 0) {
        selectedDataSourceName.value = databaseSources.value[0]?.name ?? null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load data sources'
    }
  } else if (props.autoLoad && databaseSources.value.length > 0 && !selectedDataSourceName.value) {
    selectedDataSourceName.value = databaseSources.value[0]?.name ?? null
  }
})
</script>

<style scoped>
.v-list-item {
  cursor: pointer;
}

.v-list-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
}
</style>
