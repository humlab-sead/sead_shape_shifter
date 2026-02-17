<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon icon="mdi-table-eye" class="mr-2" />
      Data Preview
      <v-spacer />
      <v-btn
        icon="mdi-refresh"
        size="small"
        variant="text"
        :loading="loading"
        :disabled="!dataSource || !tableName"
        @click="refreshData"
      />
    </v-card-title>

    <v-card-text>
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" />
        <p class="text-caption mt-2">Loading data...</p>
      </div>

      <!-- Error Display -->
      <v-alert v-else-if="error" type="error" variant="tonal" density="compact" closable @click:close="clearError">
        {{ error }}
      </v-alert>

      <!-- Empty State -->
      <v-alert v-else-if="!previewData" type="info" variant="tonal" density="compact">
        Select a table to preview its data
      </v-alert>

      <!-- Data Table -->
      <div v-else>
        <!-- Info Bar -->
        <div class="d-flex align-center mb-3">
          <v-chip size="small" variant="text"> {{ previewData.total_rows.toLocaleString() }} total rows </v-chip>
          <v-chip size="small" variant="text"> Showing {{ previewData.rows.length }} rows </v-chip>
          <v-spacer />
          <v-select
            v-model="limit"
            :items="[10, 25, 50, 100]"
            label="Rows per page"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width: 150px"
            @update:model-value="loadPreview"
          />
        </div>

        <!-- Table -->
        <div class="data-table-container">
          <v-table density="compact" fixed-header height="400px">
            <thead>
              <tr>
                <th v-for="column in previewData.columns" :key="column" class="text-left">
                  {{ column }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in previewData.rows" :key="index">
                <td v-for="column in previewData.columns" :key="column">
                  <span :class="getCellClass(row[column])">
                    {{ formatCellValue(row[column]) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </v-table>
        </div>

        <!-- Pagination -->
        <div class="d-flex align-center justify-center mt-3">
          <v-btn
            icon="mdi-chevron-left"
            size="small"
            variant="text"
            :disabled="offset === 0 || loading"
            @click="previousPage"
          />
          <v-chip size="small" variant="text" class="mx-2">
            {{ Math.floor(offset / limit) + 1 }} / {{ totalPages }}
          </v-chip>
          <v-btn
            icon="mdi-chevron-right"
            size="small"
            variant="text"
            :disabled="offset + limit >= previewData.total_rows || loading"
            @click="nextPage"
          />
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useDataSourceStore } from '@/stores/data-source'
import type { PreviewData } from '@/types/schema'

// Props
interface Props {
  dataSource?: string
  tableName?: string
  schema?: string
  autoLoad?: boolean
  defaultLimit?: number
}

const props = withDefaults(defineProps<Props>(), {
  autoLoad: true,
  defaultLimit: 50,
})

// Store
const dataSourceStore = useDataSourceStore()

// State
const previewData = ref<PreviewData | null>(null)
const limit = ref(props.defaultLimit)
const offset = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)
const isMounted = ref(true)

// Computed
const totalPages = computed(() => {
  if (!previewData.value) return 0
  return Math.ceil(previewData.value.total_rows / limit.value)
})

// Methods
async function loadPreview() {
  if (!props.dataSource || !props.tableName || !isMounted.value) return

  loading.value = true
  error.value = null

  try {
    const result = await dataSourceStore.previewTable(props.dataSource, props.tableName, {
      schema: props.schema,
      limit: limit.value,
      offset: offset.value,
    })
    
    // Only update if still mounted
    if (isMounted.value) {
      previewData.value = result
    }
  } catch (e) {
    if (isMounted.value) {
      error.value = e instanceof Error ? e.message : 'Failed to load table data'
      previewData.value = null
    }
  } finally {
    if (isMounted.value) {
      loading.value = false
    }
  }
}

function refreshData() {
  offset.value = 0
  loadPreview()
}

function nextPage() {
  if (previewData.value && offset.value + limit.value < previewData.value.total_rows) {
    offset.value += limit.value
    loadPreview()
  }
}

function previousPage() {
  if (offset.value > 0) {
    offset.value = Math.max(0, offset.value - limit.value)
    loadPreview()
  }
}

function clearError() {
  error.value = null
}

function formatCellValue(value: any): string {
  if (value === null || value === undefined) {
    return 'NULL'
  }

  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }

  if (typeof value === 'object') {
    return JSON.stringify(value)
  }

  if (typeof value === 'string' && value.length > 100) {
    return value.substring(0, 100) + '...'
  }

  return String(value)
}

function getCellClass(value: any): string {
  if (value === null || value === undefined) {
    return 'text-grey'
  }

  if (typeof value === 'number') {
    return 'text-blue'
  }

  if (typeof value === 'boolean') {
    return 'text-green'
  }

  return ''
}

// Watchers
watch(
  () => [props.dataSource, props.tableName, props.schema],
  () => {
    // Clear existing data immediately to prevent stale data display
    previewData.value = null
    error.value = null
    offset.value = 0
    
    if (props.autoLoad && isMounted.value) {
      loadPreview()
    }
  },
  { immediate: props.autoLoad }
)

// Lifecycle
onBeforeUnmount(() => {
  isMounted.value = false
})

// Expose methods for parent components
defineExpose({
  loadPreview,
  refreshData,
  nextPage,
  previousPage,
})
</script>

<style scoped>
.data-table-container {
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
  overflow: hidden;
}

.v-table {
  /* Use theme colors instead of hardcoded values */
  background-color: rgb(var(--v-theme-surface));
}

.v-table thead th {
  background-color: rgb(var(--v-theme-surface-variant));
  font-weight: 600;
  white-space: nowrap;
  color: rgb(var(--v-theme-on-surface));
}

.v-table tbody td {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgb(var(--v-theme-on-surface));
}

.text-grey {
  color: rgb(var(--v-theme-on-surface-variant));
  font-style: italic;
}

.text-blue {
  color: rgb(var(--v-theme-primary));
}

.text-green {
  color: rgb(var(--v-theme-success));
}
</style>
