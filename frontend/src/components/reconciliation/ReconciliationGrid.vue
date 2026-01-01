<template>
  <div class="reconciliation-grid">
    <!-- Toolbar -->
    <v-toolbar density="compact" color="transparent" flat>
      <v-chip v-if="stats.autoMatched > 0" size="small" color="success" variant="tonal" class="mr-2">
        <v-icon start size="small">mdi-check-circle</v-icon>
        {{ stats.autoMatched }} Auto-matched
      </v-chip>
      <v-chip v-if="stats.needsReview > 0" size="small" color="warning" variant="tonal" class="mr-2">
        <v-icon start size="small">mdi-help-circle</v-icon>
        {{ stats.needsReview }} Needs Review
      </v-chip>
      <v-chip v-if="stats.unmatched > 0" size="small" color="error" variant="tonal">
        <v-icon start size="small">mdi-close-circle</v-icon>
        {{ stats.unmatched }} Unmatched
      </v-chip>
      <v-spacer />
      <v-btn
        v-if="hasChanges"
        variant="tonal"
        color="primary"
        prepend-icon="mdi-content-save"
        @click="saveChanges"
        :loading="saving"
      >
        Save Changes
      </v-btn>
    </v-toolbar>

    <!-- AG Grid -->
    <ag-grid-vue
      ref="gridRef"
      class="ag-theme-material reconciliation-ag-grid"
      :columnDefs="columnDefs"
      :rowData="rowData"
      :defaultColDef="defaultColDef"
      :getRowStyle="getRowStyle"
      @grid-ready="onGridReady"
      @cell-value-changed="onCellValueChanged"
      :domLayout="'autoHeight'"
    />

    <!-- Candidate Review Dialog -->
    <v-dialog v-model="candidateDialog" max-width="700">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-magnify</v-icon>
          Review Candidates
        </v-card-title>
        <v-card-subtitle v-if="selectedRow">
          {{ getRowDisplayText(selectedRow) }}
        </v-card-subtitle>

        <v-card-text>
          <v-list v-if="selectedRow?.candidates && selectedRow.candidates.length > 0">
            <v-list-item
              v-for="(candidate, idx) in selectedRow.candidates"
              :key="idx"
              @click="selectCandidate(candidate)"
              :class="{ 'bg-blue-lighten-5': selectedCandidate === candidate }"
            >
              <template v-slot:prepend>
                <v-avatar :color="getConfidenceColor((candidate.score ?? 0) * 100)" size="32">
                  {{ Math.round((candidate.score ?? 0) * 100) }}
                </v-avatar>
              </template>
              <v-list-item-title>
                {{ candidate.name }}
              </v-list-item-title>
              <v-list-item-subtitle v-if="candidate.description">
                {{ candidate.description }}
              </v-list-item-subtitle>
              <template v-slot:append>
                <v-chip size="small" variant="outlined"> ID: {{ extractIdFromUri(candidate.id) }} </v-chip>
              </template>
            </v-list-item>
          </v-list>
          <div v-else class="text-center text-grey py-8">No candidates available</div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="candidateDialog = false"> Cancel </v-btn>
          <v-btn variant="tonal" color="primary" @click="acceptCandidate" :disabled="!selectedCandidate">
            Accept
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type { GridApi, ColDef, CellValueChangedEvent } from 'ag-grid-community'
import type { EntityReconciliationSpec, ReconciliationPreviewRow, ReconciliationCandidate } from '@/types'

// AG Grid Community styles
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-material.css'

interface Props {
  entitySpec: EntityReconciliationSpec | null
  previewData: ReconciliationPreviewRow[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const emit = defineEmits<{
  'update:mapping': [row: ReconciliationPreviewRow, seadId: number | null, notes?: string]
  save: []
}>()

// Grid reference
const gridApi = ref<GridApi>()
const hasChanges = ref(false)
const saving = ref(false)

// Candidate dialog
const candidateDialog = ref(false)
const selectedRow = ref<ReconciliationPreviewRow | null>(null)
const selectedCandidate = ref<ReconciliationCandidate | null>(null)

// Default column definition
const defaultColDef: ColDef = {
  resizable: true,
  sortable: true,
  filter: true,
  editable: false,
}

// Column definitions
const columnDefs = computed<ColDef[]>(() => {
  if (!props.entitySpec) return []

  const cols: ColDef[] = []

  // Key columns (read-only, pinned left)
  props.entitySpec.keys.forEach((key) => {
    cols.push({
      field: key,
      headerName: key.replace(/_/g, ' ').toUpperCase(),
      pinned: 'left',
      width: 150,
    })
  })

  // Property-mapped columns (read-only)
  // Get unique source columns from property_mappings
  const propertyColumns = new Set(Object.values(props.entitySpec.property_mappings))
  propertyColumns.forEach((col) => {
    cols.push({
      field: col,
      headerName: col.replace(/_/g, ' ').toUpperCase(),
      width: 150,
    })
  })

  // SEAD ID column (editable with autocomplete)
  cols.push({
    field: 'sead_id',
    headerName: 'SEAD ID',
    width: 120,
    editable: true,
    cellRenderer: (params: any) => {
      if (params.value) {
        return `<span class="font-weight-bold">${params.value}</span>`
      }
      return '<span class="text-grey">—</span>'
    },
  })

  // Confidence column
  cols.push({
    field: 'confidence',
    headerName: 'Confidence',
    width: 120,
    cellRenderer: (params: any) => {
      const confidence = params.value
      if (confidence == null) return '—'

      const color = getConfidenceColorHex(confidence)
      return `<span style="color: ${color}; font-weight: 600;">${Math.round(confidence)}%</span>`
    },
  })

  // Notes column (editable)
  cols.push({
    field: 'notes',
    headerName: 'Notes',
    width: 200,
    editable: true,
    cellEditor: 'agTextCellEditor',
  })

  // Candidates action column
  cols.push({
    field: 'candidates',
    headerName: 'Actions',
    width: 100,
    pinned: 'right',
    cellRenderer: (params: any) => {
      const candidatesCount = params.value?.length || 0
      if (candidatesCount === 0) return ''

      return `<button class="candidate-btn" data-row-index="${params.node.rowIndex}">
        <span class="mdi mdi-magnify"></span> ${candidatesCount}
      </button>`
    },
    onCellClicked: (params: any) => {
      if (params.value && params.value.length > 0) {
        showCandidates(params.data)
      }
    },
  })

  return cols
})

// Row data
const rowData = computed(() => props.previewData)

// Statistics
const stats = computed(() => {
  const autoMatched = props.previewData.filter(
    (row) => row.confidence != null && row.confidence >= (props.entitySpec?.auto_accept_threshold || 95)
  ).length

  const needsReview = props.previewData.filter(
    (row) =>
      row.confidence != null &&
      row.confidence < (props.entitySpec?.auto_accept_threshold || 95) &&
      row.confidence >= (props.entitySpec?.review_threshold || 70)
  ).length

  const unmatched = props.previewData.filter(
    (row) => row.confidence == null || row.confidence < (props.entitySpec?.review_threshold || 70)
  ).length

  return { autoMatched, needsReview, unmatched }
})

// Grid ready event
function onGridReady(params: any) {
  gridApi.value = params.api
}

// Row styling based on confidence
function getRowStyle(params: any) {
  const row = params.data as ReconciliationPreviewRow
  if (!row.confidence) {
    return { background: '#ffebee' } // Light red for unmatched
  }

  const autoAcceptThreshold = props.entitySpec?.auto_accept_threshold || 95
  const reviewThreshold = props.entitySpec?.review_threshold || 70

  if (row.confidence >= autoAcceptThreshold) {
    return { background: '#e8f5e9' } // Light green for auto-matched
  } else if (row.confidence >= reviewThreshold) {
    return { background: '#fff3e0' } // Light orange for needs review
  }

  return { background: '#ffebee' } // Light red for low confidence
}

// Confidence color helpers
function getConfidenceColor(confidence: number): string {
  if (confidence >= 95) return 'success'
  if (confidence >= 70) return 'warning'
  return 'error'
}

function getConfidenceColorHex(confidence: number): string {
  if (confidence >= 95) return '#4caf50'
  if (confidence >= 70) return '#ff9800'
  return '#f44336'
}

// Cell value changed
function onCellValueChanged(event: CellValueChangedEvent) {
  const row = event.data as ReconciliationPreviewRow
  const field = event.colDef.field

  if (field === 'sead_id') {
    const seadId = event.newValue ? parseInt(event.newValue) : null
    emit('update:mapping', row, seadId, row.notes)
    hasChanges.value = true
  } else if (field === 'notes') {
    emit('update:mapping', row, row.sead_id ?? null, event.newValue)
    hasChanges.value = true
  }
}

// Show candidate dialog
function showCandidates(row: ReconciliationPreviewRow) {
  selectedRow.value = row
  selectedCandidate.value = null
  candidateDialog.value = true
}

// Select a candidate
function selectCandidate(candidate: ReconciliationCandidate) {
  selectedCandidate.value = candidate
}

// Accept selected candidate
function acceptCandidate() {
  if (!selectedCandidate.value || !selectedRow.value) return

  const seadId = extractIdFromUri(selectedCandidate.value.id)
  if (seadId) {
    selectedRow.value.sead_id = seadId
    selectedRow.value.confidence = (selectedCandidate.value.score ?? 0) * 100

    emit('update:mapping', selectedRow.value, seadId, selectedRow.value.notes)
    hasChanges.value = true

    // Refresh grid
    gridApi.value?.refreshCells()
  }

  candidateDialog.value = false
}

// Extract ID from URI
function extractIdFromUri(uri: string): number | null {
  const match = uri.match(/\/(\d+)$/)
  return match?.[1] ? parseInt(match[1]) : null
}

// Get row display text
function getRowDisplayText(row: ReconciliationPreviewRow): string {
  if (!props.entitySpec) return ''

  const keyValues = props.entitySpec.keys
    .map((key) => row[key])
    .filter((val) => val != null)
    .join(' | ')

  return keyValues
}

// Save changes
function saveChanges() {
  saving.value = true
  emit('save')

  // Simulate save delay
  setTimeout(() => {
    saving.value = false
    hasChanges.value = false
  }, 500)
}

// Watch for data changes
watch(
  () => props.previewData,
  () => {
    hasChanges.value = false
  }
)
</script>

<style scoped>
.reconciliation-grid {
  width: 100%;
}

.reconciliation-ag-grid {
  height: 100%;
  width: 100%;
  min-height: 400px;
}

:deep(.candidate-btn) {
  background: #2196f3;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

:deep(.candidate-btn:hover) {
  background: #1976d2;
}

:deep(.ag-cell) {
  display: flex;
  align-items: center;
}

:deep(.ag-header-cell-text) {
  font-weight: 600;
}
</style>
