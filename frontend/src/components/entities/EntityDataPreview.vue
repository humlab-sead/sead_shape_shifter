<template>
  <v-card>
    <v-card-title class="d-flex align-center py-2">
      <v-icon icon="mdi-eye-outline" class="mr-2" size="small" />
      <span class="text-body-1">Entity Data Preview</span>
      <v-spacer />

      <!-- Cache indicator -->
      <v-chip v-if="previewData?.cache_hit" size="x-small" color="info" variant="flat" class="mr-2">
        <v-icon icon="mdi-cached" start size="x-small" />
        Cached
      </v-chip>

      <!-- Row count -->
      <v-chip v-if="previewData" size="x-small" variant="text" class="mr-2">
        {{ previewData.total_rows_in_preview }} / {{ previewData.estimated_total_rows || '?' }} rows
      </v-chip>

      <!-- Refresh button -->
      <v-btn icon="mdi-refresh" size="small" variant="text" :loading="loading" @click="emit('refresh')" />
    </v-card-title>

    <v-divider />

    <v-card-text class="pa-0">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" size="48" />
        <p class="text-caption mt-2">Loading preview...</p>
      </div>

      <!-- Error Display -->
      <div v-else-if="error" class="ma-4">
        <preview-error :error="error" />
      </div>

      <!-- Empty State -->
      <v-alert
        v-else-if="!previewData || !previewData.rows.length"
        type="info"
        variant="tonal"
        density="compact"
        class="ma-4"
      >
        <template v-if="!previewData"> No preview data available </template>
        <template v-else> Entity has no data rows </template>
      </v-alert>

      <!-- Data Table -->
      <div v-else>
        <!-- Metadata chips and controls -->
        <div class="d-flex flex-wrap gap-2 pa-3 metadata-bar align-center">
          <v-chip v-if="previewData.has_dependencies" size="small" variant="outlined" color="primary">
            <v-icon icon="mdi-link-variant" start size="small" />
            {{ previewData.dependencies_loaded.length }} dependencies
          </v-chip>

          <v-chip size="small" variant="outlined" color="success">
            <v-icon icon="mdi-clock-outline" start size="small" />
            {{ previewData.execution_time_ms }}ms
          </v-chip>

          <v-spacer />

          <!-- Filter indicator and clear button -->
          <v-chip
            v-if="Object.keys(columnFilters).length > 0"
            size="small"
            variant="flat"
            color="info"
            closable
            @click:close="clearFilters"
          >
            <v-icon icon="mdi-filter" start size="small" />
            {{ Object.keys(columnFilters).length }} filters
          </v-chip>

          <v-chip v-if="filteredRows.length !== previewData.rows.length" size="small" variant="text">
            Showing {{ filteredRows.length }} / {{ previewData.rows.length }} rows
          </v-chip>
        </div>

        <v-divider />

        <!-- Scrollable table container -->
        <div class="preview-table-container">
          <v-table density="compact" fixed-header height="400px">
            <thead>
              <!-- Column headers with sort -->
              <tr>
                <th
                  v-for="column in previewData.columns"
                  :key="column.name"
                  class="text-left column-header"
                  @click="toggleSort(column.name)"
                >
                  <div class="d-flex align-center gap-1">
                    <v-icon v-if="column.is_key" icon="mdi-key" size="x-small" color="warning" class="mr-1" />
                    <span class="font-weight-medium">{{ column.name }}</span>
                    <v-chip size="x-small" variant="flat" :color="getTypeColor(column.data_type)" class="ml-1">
                      {{ column.data_type }}
                    </v-chip>
                    <v-icon v-if="column.nullable" icon="mdi-null" size="x-small" color="grey" />
                    <v-spacer />
                    <v-icon
                      :icon="getSortIcon(column.name)"
                      size="small"
                      :color="sortColumn === column.name ? 'primary' : 'grey'"
                    />
                  </div>
                </th>
              </tr>
              <!-- Column filters -->
              <tr class="filter-row">
                <th v-for="column in previewData.columns" :key="`filter-${column.name}`" class="pa-1">
                  <v-text-field
                    v-model="columnFilters[column.name]"
                    density="compact"
                    variant="outlined"
                    hide-details
                    clearable
                    placeholder="Filter..."
                    @click.stop
                  >
                    <template #prepend-inner>
                      <v-icon icon="mdi-filter-outline" size="x-small" />
                    </template>
                  </v-text-field>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in filteredRows" :key="idx" :class="{ 'striped-row': idx % 2 === 0 }">
                <td v-for="column in previewData.columns" :key="column.name" class="text-left">
                  <span
                    v-if="row[column.name] === null || row[column.name] === undefined"
                    class="text-grey font-italic"
                  >
                    null
                  </span>
                  <span v-else>{{ formatValue(row[column.name]) }}</span>
                </td>
              </tr>
            </tbody>
          </v-table>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { PreviewResult } from '@/composables/useEntityPreview'
import PreviewError from './PreviewError.vue'

interface Props {
  previewData: PreviewResult | null
  loading?: boolean
  error?: string | any | null
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
})

const emit = defineEmits<{
  refresh: []
}>()

// Sorting state
const sortColumn = ref<string | null>(null)
const sortDirection = ref<'asc' | 'desc'>('asc')

// Filtering state
const columnFilters = ref<Record<string, string>>({})

// Computed filtered and sorted rows
const filteredRows = computed(() => {
  if (!props.previewData) return []

  let rows = [...props.previewData.rows]

  // Apply column filters
  Object.entries(columnFilters.value).forEach(([column, filterText]) => {
    if (filterText.trim()) {
      rows = rows.filter((row) => {
        const value = row[column]
        if (value === null || value === undefined) return false
        return String(value).toLowerCase().includes(filterText.toLowerCase())
      })
    }
  })

  // Apply sorting
  if (sortColumn.value) {
    rows.sort((a, b) => {
      const aVal = a[sortColumn.value!]
      const bVal = b[sortColumn.value!]

      // Handle nulls
      if (aVal === null || aVal === undefined) return 1
      if (bVal === null || bVal === undefined) return -1

      // Compare values
      let comparison = 0
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal
      } else {
        comparison = String(aVal).localeCompare(String(bVal))
      }

      return sortDirection.value === 'asc' ? comparison : -comparison
    })
  }

  return rows
})

function toggleSort(columnName: string) {
  if (sortColumn.value === columnName) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = columnName
    sortDirection.value = 'asc'
  }
}

function getSortIcon(columnName: string): string {
  if (sortColumn.value !== columnName) return 'mdi-sort'
  return sortDirection.value === 'asc' ? 'mdi-sort-ascending' : 'mdi-sort-descending'
}

function clearFilters() {
  columnFilters.value = {}
}

function getTypeColor(dataType: string): string {
  const typeMap: Record<string, string> = {
    string: 'blue-grey',
    integer: 'green',
    number: 'green',
    boolean: 'purple',
    date: 'orange',
    datetime: 'orange',
    object: 'blue',
  }
  return typeMap[dataType.toLowerCase()] || 'grey'
}

function formatValue(value: any): string {
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value)
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  return String(value)
}
</script>

<style scoped>
.preview-table-container {
  max-height: 400px;
  overflow-y: auto;
}

:deep(.v-table) {
  background-color: rgb(var(--v-theme-surface));
}

.metadata-bar {
  background: rgb(var(--v-theme-surface-variant));
}

:deep(.v-table th) {
  background: rgb(var(--v-theme-surface));
  font-weight: 600;
  white-space: nowrap;
  position: sticky;
  top: 0;
  z-index: 2;
}

:deep(.v-table th.column-header) {
  cursor: pointer;
  user-select: none;
}

:deep(.v-table th.column-header:hover) {
  background: rgba(var(--v-theme-on-surface), 0.08);
}

:deep(.v-table tr.filter-row th) {
  position: sticky;
  top: 48px;
  z-index: 2;
  background: rgb(var(--v-theme-surface));
  border-bottom: 2px solid rgba(var(--v-theme-on-surface), 0.12);
}

/* Striped rows - theme aware */
:deep(.v-table tbody tr.striped-row) {
  background: rgba(var(--v-theme-on-surface), 0.05);
}

:deep(.v-table td) {
  white-space: nowrap;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Resizable columns */
:deep(.v-table th) {
  position: relative;
  min-width: 100px;
  resize: horizontal;
  overflow: auto;
}
</style>
