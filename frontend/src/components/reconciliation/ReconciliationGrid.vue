<template>
  <div class="reconciliation-grid">
    <!-- Filters and Search Toolbar -->
    <v-toolbar density="comfortable" color="transparent" flat class="mb-2">
      <v-chip-group v-model="statusFilter" mandatory>
        <v-chip value="all" variant="outlined">
          <v-icon start size="small">mdi-filter-variant</v-icon>
          All ({{ props.previewData.length }})
        </v-chip>
        <v-chip value="auto-accepted" color="success" variant="outlined">
          <v-icon start size="small">mdi-check-circle</v-icon>
          Auto-Accepted ({{ stats.autoMatched }})
        </v-chip>
        <v-chip value="needs-review" color="warning" variant="outlined">
          <v-icon start size="small">mdi-help-circle</v-icon>
          Needs Review ({{ stats.needsReview }})
        </v-chip>
        <v-chip value="unmatched" color="error" variant="outlined">
          <v-icon start size="small">mdi-close-circle</v-icon>
          Unmatched ({{ stats.unmatched }})
        </v-chip>
      </v-chip-group>

      <v-spacer />

      <v-text-field
        v-model="searchQuery"
        prepend-inner-icon="mdi-magnify"
        placeholder="Search queries..."
        density="compact"
        variant="outlined"
        clearable
        hide-details
        style="max-width: 300px"
        class="mr-2"
      />

      <!-- Bulk Action Buttons -->
      <v-btn
        v-if="selectedRows.length > 0"
        variant="tonal"
        color="success"
        prepend-icon="mdi-check-all"
        @click="openBulkAcceptDialog"
        class="mr-2"
      >
        Accept ({{ selectedRows.length }})
      </v-btn>

      <v-btn
        v-if="selectedRows.length > 0"
        variant="tonal"
        color="error"
        prepend-icon="mdi-close-circle"
        @click="openBulkRejectDialog"
        class="mr-2"
      >
        Reject ({{ selectedRows.length }})
      </v-btn>

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

      <v-btn
        variant="tonal"
        color="info"
        prepend-icon="mdi-table-eye"
        @click="previewDialog = true"
        class="ml-2"
      >
        Preview
      </v-btn>
    </v-toolbar>

    <!-- Statistics Chips -->
    <v-toolbar density="compact" color="transparent" flat class="mb-2">
      <v-chip size="small" variant="text">
        Showing {{ filteredRowData.length }} of {{ props.previewData.length }} items
      </v-chip>
      <v-chip v-if="selectedRows.length > 0" size="small" variant="tonal" color="primary">
        {{ selectedRows.length }} selected
      </v-chip>
      <v-spacer />
      <v-chip v-if="searchQuery" size="small" variant="tonal" closable @click:close="searchQuery = ''">
        Search: "{{ searchQuery }}"
      </v-chip>
    </v-toolbar>

    <!-- AG Grid -->
    <div @click="handleGridClick">
      <ag-grid-vue
        ref="gridRef"
        class="ag-theme-material reconciliation-ag-grid"
        :columnDefs="columnDefs"
        :rowData="filteredRowData"
        :defaultColDef="defaultColDef"
        :getRowStyle="getRowStyle"
        :rowSelection="'multiple'"
        :suppressRowClickSelection="true"
        @grid-ready="onGridReady"
        @cell-value-changed="onCellValueChanged"
        @selection-changed="onSelectionChanged"
        :domLayout="'autoHeight'"
      />
    </div>

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

    <!-- Alternative Search Dialog -->
    <alternative-search-dialog
      v-model="alternativeSearchDialog"
      :project-name="projectName"
      :entity-name="entityName"
      :target-field="targetField"
      :original-query="selectedRow ? getRowDisplayText(selectedRow) : ''"
      @accept="handleAlternativeAccept"
    />

    <!-- Mark Unmatched Dialog -->
    <v-dialog v-model="unmatchedDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="warning">mdi-alert-circle</v-icon>
          Mark as Local-Only (Will Not Match)
        </v-card-title>
        <v-card-subtitle v-if="selectedRow">
          {{ getRowDisplayText(selectedRow) }}
        </v-card-subtitle>

        <v-card-text>
          <p class="mb-4">
            This will mark the item as a <strong>local-only identifier</strong> that will not be matched to SEAD.
          </p>
          <v-textarea
            v-model="unmatchedNotes"
            label="Reason (optional)"
            placeholder="Why won't this match? (e.g., 'Local code only', 'Not in SEAD database')"
            rows="3"
            variant="outlined"
            hint="Document why this item is local-only"
          />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="unmatchedDialog = false"> Cancel </v-btn>
          <v-btn 
            variant="tonal" 
            color="warning" 
            @click="confirmMarkUnmatched"
            :loading="markingUnmatched"
          >
            Mark as Local-Only
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Accept Confirmation Dialog -->
    <v-dialog v-model="bulkAcceptDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="success">mdi-check-all</v-icon>
          Bulk Accept Matches
        </v-card-title>

        <v-card-text>
          <p class="mb-4">
            Accept top candidates for <strong>{{ selectedRows.length }} selected items</strong>?
          </p>
          <v-alert type="info" variant="tonal" class="mb-4">
            This will accept the highest-confidence candidate for each selected row.
          </v-alert>
          <v-list density="compact" class="bg-grey-lighten-4" max-height="200" style="overflow-y: auto">
            <v-list-item v-for="(row, idx) in selectedRows.slice(0, 10)" :key="idx">
              <v-list-item-title>{{ getRowDisplayText(row) }}</v-list-item-title>
              <template v-slot:append>
                <v-chip size="small" :color="row.candidates?.[0] ? 'success' : 'warning'">
                  {{ row.candidates?.[0] ? Math.round((row.candidates[0].score ?? 0) * 100) + '%' : 'No candidates' }}
                </v-chip>
              </template>
            </v-list-item>
            <v-list-item v-if="selectedRows.length > 10">
              <v-list-item-title class="text-grey">... and {{ selectedRows.length - 10 }} more</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="bulkAcceptDialog = false"> Cancel </v-btn>
          <v-btn 
            variant="tonal" 
            color="success" 
            @click="confirmBulkAccept"
            :loading="bulkProcessing"
          >
            Accept {{ selectedRows.length }} Items
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Reject Confirmation Dialog -->
    <v-dialog v-model="bulkRejectDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="error">mdi-close-circle</v-icon>
          Bulk Reject Matches
        </v-card-title>

        <v-card-text>
          <p class="mb-4">
            Clear matches for <strong>{{ selectedRows.length }} selected items</strong>?
          </p>
          <v-alert type="warning" variant="tonal" class="mb-4">
            This will remove all candidates and SEAD IDs from selected rows.
          </v-alert>
          <v-list density="compact" class="bg-grey-lighten-4" max-height="200" style="overflow-y: auto">
            <v-list-item v-for="(row, idx) in selectedRows.slice(0, 10)" :key="idx">
              <v-list-item-title>{{ getRowDisplayText(row) }}</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="selectedRows.length > 10">
              <v-list-item-title class="text-grey">... and {{ selectedRows.length - 10 }} more</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="bulkRejectDialog = false"> Cancel </v-btn>
          <v-btn 
            variant="tonal" 
            color="error" 
            @click="confirmBulkReject"
            :loading="bulkProcessing"
          >
            Reject {{ selectedRows.length }} Items
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Preview Matched Data Dialog -->
    <preview-matched-data-dialog
      v-model="previewDialog"
      :preview-data="enrichedPreviewData"
      :entity-spec="entitySpec"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type { GridApi, ColDef, CellValueChangedEvent } from 'ag-grid-community'
import type { EntityReconciliationSpec, ReconciliationPreviewRow, ReconciliationCandidate } from '@/types'
import AlternativeSearchDialog from './AlternativeSearchDialog.vue'
import PreviewMatchedDataDialog from './PreviewMatchedDataDialog.vue'

// AG Grid Community styles
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-material.css'

interface Props {
  entitySpec: EntityReconciliationSpec | null
  previewData: ReconciliationPreviewRow[]
  loading?: boolean
  projectName: string
  entityName: string
  targetField: string // Target field being reconciled
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

// Filter and search state
const statusFilter = ref<'all' | 'auto-accepted' | 'needs-review' | 'unmatched'>('all')
const searchQuery = ref('')

// Candidate dialog
const candidateDialog = ref(false)
const alternativeSearchDialog = ref(false)
const unmatchedDialog = ref(false)
const unmatchedNotes = ref('')
const markingUnmatched = ref(false)
const selectedRow = ref<ReconciliationPreviewRow | null>(null)
const selectedCandidate = ref<ReconciliationCandidate | null>(null)

// Debug: Watch alternativeSearchDialog changes
watch(alternativeSearchDialog, (newValue, oldValue) => {
  console.log('[ReconciliationGrid] alternativeSearchDialog changed from', oldValue, 'to', newValue)
})

// Bulk actions
const selectedRows = ref<ReconciliationPreviewRow[]>([])
const bulkAcceptDialog = ref(false)
const bulkRejectDialog = ref(false)
const bulkProcessing = ref(false)

// Preview dialog
const previewDialog = ref(false)

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

  // Checkbox column for row selection
  cols.push({
    headerName: '',
    field: '__selected',
    width: 50,
    pinned: 'left',
    checkboxSelection: true,
    headerCheckboxSelection: true,
    headerCheckboxSelectionFilteredOnly: true,
    suppressMenu: true,
    sortable: false,
    filter: false,
  })

  // Target field column (pinned left)
  cols.push({
    field: props.targetField,
    headerName: `${props.targetField.replace(/_/g, ' ').toUpperCase()} (Target)`,
    pinned: 'left',
    width: 200,
    cellClass: 'font-weight-bold',
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
    width: 200,
    pinned: 'right',
    cellRenderer: (params: any) => {
      const candidatesCount = params.value?.length || 0
      const buttons = []

      if (candidatesCount > 0) {
        buttons.push(`<button class="candidate-btn" data-row-index="${params.node.rowIndex}" data-action="review">
          <span class="mdi mdi-magnify"></span> Review (${candidatesCount})
        </button>`)
      }

      buttons.push(`<button class="search-btn" data-row-index="${params.node.rowIndex}" data-action="search">
        <span class="mdi mdi-search-web"></span> Search
      </button>`)

      buttons.push(`<button class="unmatched-btn" data-row-index="${params.node.rowIndex}" data-action="unmatched">
        <span class="mdi mdi-cancel"></span> Won't Match
      </button>`)

      return buttons.join(' ')
    },
  })

  return cols
})

// Filtered row data based on status and search
const filteredRowData = computed(() => {
  let filtered = props.previewData

  const autoAcceptThreshold = props.entitySpec?.auto_accept_threshold || 95
  const reviewThreshold = props.entitySpec?.review_threshold || 70

  // Apply status filter
  if (statusFilter.value !== 'all') {
    filtered = filtered.filter((row) => {
      const confidence = row.confidence ?? 0

      if (statusFilter.value === 'auto-accepted') {
        return confidence >= autoAcceptThreshold
      } else if (statusFilter.value === 'needs-review') {
        return confidence >= reviewThreshold && confidence < autoAcceptThreshold
      } else if (statusFilter.value === 'unmatched') {
        return confidence < reviewThreshold
      }

      return true
    })
  }

  // Apply search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter((row) => {
      const rowText = getRowDisplayText(row).toLowerCase()
      return rowText.includes(query)
    })
  }

  return filtered
})

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

// Enriched preview data with matched names from candidates
const enrichedPreviewData = computed(() => {
  return props.previewData.map(row => {
    // Find matched name from candidates if we have a SEAD ID
    let matched_name: string | undefined
    
    if (row.sead_id && row.candidates) {
      const matchedCandidate = row.candidates.find(c => {
        const candidateId = extractIdFromUri(c.id)
        return candidateId === row.sead_id
      })
      
      if (matchedCandidate) {
        matched_name = matchedCandidate.name
      }
    }
    
    return {
      ...row,
      matched_name,
    }
  })
})

// Grid ready event
function onGridReady(params: any) {
  gridApi.value = params.api
}

// Row styling based on confidence and will_not_match flag
function getRowStyle(params: any) {
  const row = params.data as ReconciliationPreviewRow
  
  // Gray out items marked as "will not match"
  if (row.will_not_match) {
    return { 
      background: '#f5f5f5', 
      color: '#999',
      textDecoration: 'line-through',
      opacity: 0.7
    }
  }
  
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

  // Use the target field value as the display text
  const targetValue = row[props.targetField]
  return targetValue != null ? String(targetValue) : ''
}

// Handle clicks on action buttons in the grid
function handleGridClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  
  // Find the button that was clicked
  const button = target.closest('button[data-action]') as HTMLButtonElement
  if (!button) return
  
  const action = button.getAttribute('data-action')
  const rowIndex = button.getAttribute('data-row-index')
  
  console.log('[ReconciliationGrid] Button clicked - action:', action, 'rowIndex:', rowIndex)
  
  if (rowIndex === null) return
  
  const row = filteredRowData.value[parseInt(rowIndex)]
  if (!row) {
    console.warn('[ReconciliationGrid] No row found at index:', rowIndex)
    return
  }
  
  console.log('[ReconciliationGrid] Row data:', row)
  
  if (action === 'review' && row.candidates && row.candidates.length > 0) {
    showCandidates(row)
  } else if (action === 'search') {
    openAlternativeSearch(row)
  } else if (action === 'unmatched') {
    openUnmatchedDialog(row)
  }
}

// Open alternative search dialog
function openAlternativeSearch(row: ReconciliationPreviewRow) {
  console.log('[ReconciliationGrid] Opening alternative search for row:', row)
  selectedRow.value = row
  alternativeSearchDialog.value = true
  console.log('[ReconciliationGrid] Dialog state:', alternativeSearchDialog.value)
}

// Handle alternative match acceptance
function handleAlternativeAccept(candidate: ReconciliationCandidate) {
  if (!selectedRow.value) return

  const seadId = extractIdFromUri(candidate.id)
  if (seadId) {
    selectedRow.value.sead_id = seadId
    selectedRow.value.confidence = (candidate.score ?? 0) * 100

    emit('update:mapping', selectedRow.value, seadId, selectedRow.value.notes)
    hasChanges.value = true

    // Refresh grid
    gridApi.value?.refreshCells()
  }
}

// Open unmatched dialog
function openUnmatchedDialog(row: ReconciliationPreviewRow) {
  selectedRow.value = row
  unmatchedNotes.value = ''
  unmatchedDialog.value = true
}

// Confirm mark as unmatched
async function confirmMarkUnmatched() {
  if (!selectedRow.value) return

  markingUnmatched.value = true

  try {
    // Build source_value from target field
    const sourceValue = selectedRow.value![props.targetField]

    // Call API to mark as unmatched
    const response = await fetch(
      `/api/v1/projects/${props.projectName}/reconciliation/${props.entityName}/${props.targetField}/mark-unmatched`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_value: sourceValue,
          notes: unmatchedNotes.value || 'Marked as local-only (will not match)',
        }),
      }
    )

    if (!response.ok) {
      throw new Error('Failed to mark as unmatched')
    }

    // Update local row data
    selectedRow.value.sead_id = null as any
    selectedRow.value.confidence = null as any
    selectedRow.value.will_not_match = true
    selectedRow.value.notes = unmatchedNotes.value || 'Marked as local-only (will not match)'

    // Refresh grid to apply styling
    gridApi.value?.refreshCells()
    hasChanges.value = true

    unmatchedDialog.value = false
  } catch (error) {
    console.error('Failed to mark as unmatched:', error)
    alert('Failed to mark as unmatched. Please try again.')
  } finally {
    markingUnmatched.value = false
  }
}

// Handle row selection change
function onSelectionChanged() {
  const selected = gridApi.value?.getSelectedRows() || []
  selectedRows.value = selected
}

// Open bulk accept dialog
function openBulkAcceptDialog() {
  if (selectedRows.value.length === 0) return
  bulkAcceptDialog.value = true
}

// Open bulk reject dialog
function openBulkRejectDialog() {
  if (selectedRows.value.length === 0) return
  bulkRejectDialog.value = true
}

// Confirm bulk accept
function confirmBulkAccept() {
  bulkProcessing.value = true

  // Accept top candidate for each selected row
  selectedRows.value.forEach((row) => {
    if (row.candidates && row.candidates.length > 0) {
      const topCandidate = row.candidates[0]
      if (topCandidate) {
        const seadId = extractIdFromUri(topCandidate.id)
        if (seadId) {
          row.sead_id = seadId
          row.confidence = (topCandidate.score ?? 0) * 100
          emit('update:mapping', row, seadId, row.notes)
        }
      }
    }
  })

  // Refresh grid and reset selection
  gridApi.value?.refreshCells()
  gridApi.value?.deselectAll()
  hasChanges.value = true
  bulkProcessing.value = false
  bulkAcceptDialog.value = false
}

// Confirm bulk reject
function confirmBulkReject() {
  bulkProcessing.value = true

  // Clear matches for each selected row
  selectedRows.value.forEach((row) => {
    row.sead_id = undefined
    row.confidence = undefined
    row.candidates = []
    emit('update:mapping', row, null)
  })

  // Refresh grid and reset selection
  gridApi.value?.refreshCells()
  gridApi.value?.deselectAll()
  hasChanges.value = true
  bulkProcessing.value = false
  bulkRejectDialog.value = false
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

:deep(.search-btn) {
  background: #9c27b0;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 4px;
}

:deep(.search-btn:hover) {
  background: #7b1fa2;
}

:deep(.unmatched-btn) {
  background: #ff9800;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 4px;
}

:deep(.unmatched-btn:hover) {
  background: #f57c00;
}

:deep(.ag-cell) {
  display: flex;
  align-items: center;
}

:deep(.ag-header-cell-text) {
  font-weight: 600;
}
</style>
