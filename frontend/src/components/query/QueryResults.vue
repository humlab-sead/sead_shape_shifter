<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2">mdi-table-large</v-icon>
      Query Results
      <v-spacer />
      <v-btn v-if="result && result.rows.length > 0" variant="text" size="small" @click="exportToCSV">
        <v-icon start size="small">mdi-download</v-icon>
        Export CSV
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- No results message -->
      <v-alert v-if="!result" type="info" variant="tonal" density="compact">
        Execute a query to see results here
      </v-alert>

      <!-- Empty results -->
      <v-alert v-else-if="result.rows.length === 0" type="info" variant="tonal" density="compact">
        Query returned no results
      </v-alert>

      <!-- Results table -->
      <div v-else>
        <!-- Stats bar -->
        <v-row class="mb-3">
          <v-col cols="12" class="d-flex align-center gap-4">
            <v-chip size="small" label>
              <v-icon start size="small">mdi-table-row</v-icon>
              {{ result.row_count }} {{ result.row_count === 1 ? 'row' : 'rows' }}
            </v-chip>
            <v-chip size="small" label>
              <v-icon start size="small">mdi-table-column</v-icon>
              {{ result.columns.length }} {{ result.columns.length === 1 ? 'column' : 'columns' }}
            </v-chip>
            <v-chip size="small" label>
              <v-icon start size="small">mdi-clock-outline</v-icon>
              {{ result.execution_time_ms }}ms
            </v-chip>
            <v-chip v-if="result.is_truncated" size="small" color="warning" label>
              <v-icon start size="small">mdi-alert</v-icon>
              Results truncated
            </v-chip>
          </v-col>
        </v-row>

        <!-- Data table -->
        <v-data-table
          :headers="headers"
          :items="paginatedRows"
          :items-per-page="itemsPerPage"
          :page="page"
          density="compact"
          class="elevation-1 results-table"
          fixed-header
          height="500"
        >
          <!-- Custom cell rendering -->
          <template #item="{ item }">
            <tr>
              <td v-for="column in result.columns" :key="column" :class="getCellClass(item[column])">
                {{ formatValue(item[column]) }}
              </td>
            </tr>
          </template>

          <!-- Footer with pagination -->
          <template #bottom>
            <div class="d-flex align-center justify-space-between pa-3">
              <div class="text-caption text-grey">Showing {{ startRow }}-{{ endRow }} of {{ result.row_count }}</div>
              <v-pagination v-model="page" :length="totalPages" :total-visible="7" size="small" />
              <v-select
                v-model="itemsPerPage"
                :items="[10, 25, 50, 100]"
                density="compact"
                variant="outlined"
                hide-details
                style="max-width: 100px"
                label="Per page"
              />
            </div>
          </template>
        </v-data-table>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { QueryResult } from '@/types/query'

const props = defineProps<{
  result: QueryResult | null
}>()

// State
const page = ref(1)
const itemsPerPage = ref(25)

// Computed
const headers = computed(() => {
  if (!props.result) return []
  return props.result.columns.map((col) => ({
    title: col,
    key: col,
    sortable: false,
  }))
})

const totalPages = computed(() => {
  if (!props.result) return 0
  return Math.ceil(props.result.rows.length / itemsPerPage.value)
})

const startRow = computed(() => {
  if (!props.result || props.result.rows.length === 0) return 0
  return (page.value - 1) * itemsPerPage.value + 1
})

const endRow = computed(() => {
  if (!props.result) return 0
  return Math.min(page.value * itemsPerPage.value, props.result.rows.length)
})

const paginatedRows = computed(() => {
  if (!props.result) return []
  const start = (page.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return props.result.rows.slice(start, end)
})

// Methods
function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return 'NULL'
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

function getCellClass(value: any): string {
  if (value === null || value === undefined) {
    return 'null-value'
  }
  if (typeof value === 'number') {
    return 'number-value'
  }
  if (typeof value === 'boolean') {
    return 'boolean-value'
  }
  return ''
}

function exportToCSV() {
  if (!props.result || props.result.rows.length === 0) return

  // Generate CSV content
  const headers = props.result.columns.join(',')
  const rows = props.result.rows.map((row) =>
    props
      .result!.columns.map((col) => {
        const value = row[col]
        if (value === null || value === undefined) return ''
        // Escape quotes and wrap in quotes if contains comma or quote
        const stringValue = String(value)
        if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
          return `"${stringValue.replace(/"/g, '""')}"`
        }
        return stringValue
      })
      .join(',')
  )

  const csv = [headers, ...rows].join('\n')

  // Create download link
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)

  link.setAttribute('href', url)
  link.setAttribute('download', `query_results_${new Date().getTime()}.csv`)
  link.style.visibility = 'hidden'

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Reset page when result changes
watch(
  () => props.result,
  () => {
    page.value = 1
  }
)
</script>

<style scoped>
.results-table :deep(th) {
  font-weight: 600;
  background-color: rgb(var(--v-theme-surface-variant));
}

.results-table :deep(td) {
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
}

.null-value {
  color: rgb(var(--v-theme-error));
  font-style: italic;
  opacity: 0.7;
}

.number-value {
  text-align: right;
  color: rgb(var(--v-theme-primary));
}

.boolean-value {
  color: rgb(var(--v-theme-secondary));
  font-weight: 500;
}
</style>
