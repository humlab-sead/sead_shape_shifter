<template>
  <v-dialog v-model="show" max-width="1200" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center bg-primary">
        <v-icon class="mr-2">mdi-table-eye</v-icon>
        Preview Matched Data
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="show = false" />
      </v-card-title>

      <v-card-subtitle class="py-3">
        Preview of final output with SEAD IDs and matched names
      </v-card-subtitle>

      <v-divider />

      <!-- Toolbar with filters and export -->
      <v-toolbar density="comfortable" color="transparent" flat>
        <v-switch
          v-model="showOnlyMatched"
          label="Show only matched rows"
          density="compact"
          hide-details
          color="primary"
          class="mr-4"
        />

        <v-switch
          v-model="showOnlyChanged"
          label="Show only changed rows"
          density="compact"
          hide-details
          color="primary"
          class="mr-4"
        />

        <v-spacer />

        <v-chip size="small" variant="text" class="mr-2">
          {{ filteredPreviewData.length }} / {{ previewData.length }} rows
        </v-chip>

        <v-btn
          variant="tonal"
          color="success"
          prepend-icon="mdi-download"
          @click="exportPreview"
          :disabled="filteredPreviewData.length === 0"
        >
          Export CSV
        </v-btn>
      </v-toolbar>

      <v-divider />

      <v-card-text class="pa-0" style="max-height: 600px">
        <v-table fixed-header density="compact">
          <thead>
            <tr>
              <th v-for="column in displayColumns" :key="column" class="text-left">
                {{ formatColumnName(column) }}
              </th>
              <th class="text-left">SEAD ID</th>
              <th class="text-left">Matched Name</th>
              <th class="text-left">Confidence</th>
              <th class="text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in filteredPreviewData"
              :key="idx"
              :class="getRowClass(row)"
            >
              <td v-for="column in displayColumns" :key="column">
                {{ row[column] ?? '—' }}
              </td>
              <td>
                <v-chip
                  v-if="row.sead_id"
                  size="small"
                  color="primary"
                  variant="tonal"
                >
                  {{ row.sead_id }}
                </v-chip>
                <span v-else class="text-grey">—</span>
              </td>
              <td>
                <span v-if="row.matched_name" class="font-weight-medium">
                  {{ row.matched_name }}
                </span>
                <span v-else class="text-grey">Not matched</span>
              </td>
              <td>
                <v-chip
                  v-if="row.confidence != null"
                  size="small"
                  :color="getConfidenceColor(row.confidence)"
                  variant="tonal"
                >
                  {{ Math.round(row.confidence) }}%
                </v-chip>
                <span v-else class="text-grey">—</span>
              </td>
              <td>
                <v-chip
                  size="small"
                  :color="getStatusColor(row)"
                  variant="flat"
                >
                  {{ getStatusLabel(row) }}
                </v-chip>
              </td>
            </tr>
          </tbody>
        </v-table>

        <div v-if="filteredPreviewData.length === 0" class="text-center py-8 text-grey">
          <v-icon size="64" color="grey-lighten-1">mdi-filter-off</v-icon>
          <p class="mt-4">No rows match the current filters</p>
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-chip size="small" variant="text">
          <v-icon start size="small">mdi-check-circle</v-icon>
          {{ stats.matched }} matched
        </v-chip>
        <v-chip size="small" variant="text">
          <v-icon start size="small">mdi-close-circle</v-icon>
          {{ stats.unmatched }} unmatched
        </v-chip>
        <v-chip size="small" variant="text">
          <v-icon start size="small">mdi-cancel</v-icon>
          {{ stats.willNotMatch }} won't match
        </v-chip>
        <v-spacer />
        <v-btn variant="text" @click="show = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { ReconciliationPreviewRow, EntityReconciliationSpec } from '@/types'

interface Props {
  modelValue: boolean
  previewData: ReconciliationPreviewRow[]
  entitySpec: EntityReconciliationSpec | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

// Dialog state
const show = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

// Filter state
const showOnlyMatched = ref(false)
const showOnlyChanged = ref(false)

// Display columns from entity spec
const displayColumns = computed(() => {
  if (!props.entitySpec) return []
  
  // Show property-mapped columns (source columns from property_mappings)
  const columns = Array.from(new Set(Object.values(props.entitySpec.property_mappings)))
  
  return columns
})

// Filtered preview data
const filteredPreviewData = computed(() => {
  let filtered = props.previewData

  if (showOnlyMatched.value) {
    filtered = filtered.filter(row => row.sead_id != null && !row.will_not_match)
  }

  if (showOnlyChanged.value) {
    filtered = filtered.filter(row => row.sead_id != null || row.will_not_match)
  }

  return filtered
})

// Statistics
const stats = computed(() => {
  const matched = props.previewData.filter(row => row.sead_id != null && !row.will_not_match).length
  const willNotMatch = props.previewData.filter(row => row.will_not_match).length
  const unmatched = props.previewData.length - matched - willNotMatch

  return { matched, unmatched, willNotMatch }
})

// Helper functions
function formatColumnName(column: string): string {
  return column
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function getRowClass(row: ReconciliationPreviewRow): string {
  if (row.will_not_match) {
    return 'bg-grey-lighten-3 text-decoration-line-through'
  }
  
  if (row.sead_id) {
    const autoAcceptThreshold = props.entitySpec?.auto_accept_threshold || 95
    if ((row.confidence ?? 0) >= autoAcceptThreshold) {
      return 'bg-green-lighten-5'
    }
    return 'bg-orange-lighten-5'
  }
  
  return 'bg-red-lighten-5'
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 95) return 'success'
  if (confidence >= 70) return 'warning'
  return 'error'
}

function getStatusColor(row: ReconciliationPreviewRow): string {
  if (row.will_not_match) return 'grey'
  if (row.sead_id) {
    const autoAcceptThreshold = props.entitySpec?.auto_accept_threshold || 95
    if ((row.confidence ?? 0) >= autoAcceptThreshold) return 'success'
    return 'warning'
  }
  return 'error'
}

function getStatusLabel(row: ReconciliationPreviewRow): string {
  if (row.will_not_match) return 'Won\'t Match'
  if (row.sead_id) {
    const autoAcceptThreshold = props.entitySpec?.auto_accept_threshold || 95
    if ((row.confidence ?? 0) >= autoAcceptThreshold) return 'Auto-Matched'
    return 'Manual Match'
  }
  return 'Unmatched'
}

// Export to CSV
function exportPreview() {
  if (filteredPreviewData.value.length === 0) return

  // Build CSV header
  const headers = [
    ...displayColumns.value,
    'sead_id',
    'matched_name',
    'confidence',
    'status',
  ]

  // Build CSV rows
  const csvRows = filteredPreviewData.value.map(row => {
    const values = displayColumns.value.map(col => {
      const value = row[col]
      // Escape quotes and wrap in quotes if contains comma or quote
      if (value == null) return ''
      const str = String(value)
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`
      }
      return str
    })

    values.push(row.sead_id?.toString() || '')
    values.push(row.matched_name || '')
    values.push(row.confidence != null ? Math.round(row.confidence).toString() : '')
    values.push(getStatusLabel(row))

    return values.join(',')
  })

  // Combine header and rows
  const csv = [headers.join(','), ...csvRows].join('\n')

  // Create download link
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `reconciliation_preview_${Date.now()}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Reset filters when dialog opens
watch(show, (newValue) => {
  if (newValue) {
    showOnlyMatched.value = false
    showOnlyChanged.value = false
  }
})
</script>

<style scoped>
:deep(.v-table) {
  background-color: transparent;
}

:deep(.v-table thead th) {
  background-color: rgb(var(--v-theme-surface));
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}

:deep(.v-table tbody tr:hover) {
  background-color: rgba(0, 0, 0, 0.02) !important;
}
</style>
