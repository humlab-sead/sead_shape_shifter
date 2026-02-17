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

      <!-- Table Selector (Combobox) -->
      <v-autocomplete
        v-model="selectedTableName"
        :items="tables"
        item-title="name"
        item-value="name"
        label="Select table"
        density="compact"
        variant="outlined"
        clearable
        :loading="loading"
        :disabled="!selectedDataSourceName || loading"
        :no-data-text="!selectedDataSourceName ? 'Select a data source first' : 'No tables found'"
        class="mb-2"
      >
        <template #prepend-inner>
          <v-icon :icon="getTableIcon()" size="small" />
        </template>

        <template #item="{ props: itemProps, item }">
          <v-list-item v-bind="itemProps" :title="item.raw.name" :subtitle="formatTableSubtitle(item.raw)">
            <template #append>
              <v-chip
                v-if="item.raw.row_count !== null && item.raw.row_count !== undefined"
                size="x-small"
                variant="tonal"
              >
                {{ formatRowCount(item.raw.row_count) }}
              </v-chip>
            </template>
          </v-list-item>
        </template>
      </v-autocomplete>
      
      <!-- Slot for additional content (e.g., column details) -->
      <slot name="details" />
    </v-card-text>

    <v-card-actions v-if="tables.length > 0">
      <v-chip size="small" variant="text">
        {{ tables.length }} table{{ tables.length !== 1 ? 's' : '' }}
      </v-chip>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
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
const selectedTableName = ref<string | null>(null)
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

const selectedTable = computed(() => {
  if (!selectedTableName.value) return null
  return tables.value.find((t) => t.name === selectedTableName.value) || null
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

function formatTableSubtitle(table: TableMetadata): string {
  const parts: string[] = []

  if (table.schema_name && table.schema_name !== 'public') {
    parts.push(table.schema_name)
  }

  if (table.comment) {
    parts.push(table.comment)
  }

  const subtitle = parts.join(' • ')
  return subtitle.length > 49 ? subtitle.substring(0, 46) + '...' : subtitle
}

function clearError() {
  error.value = null
}

// Watchers
watch(selectedDataSourceName, () => {
  selectedTableName.value = null
  if (selectedDataSourceName.value && props.autoLoad) {
    loadTables()
  }
})

watch(schemaFilter, () => {
  if (selectedDataSourceName.value && isPostgreSQL.value && props.autoLoad) {
    loadTables()
  }
})

watch(selectedTableName, () => {
  if (selectedTableName.value && selectedDataSourceName.value) {
    // Wait a tick to ensure computed selectedTable is updated
    nextTick(() => {
      if (selectedTable.value) {
        const schema = isPostgreSQL.value ? schemaFilter.value : undefined
        emit('table-selected', selectedTable.value, selectedDataSourceName.value!, schema)
      }
    })
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
