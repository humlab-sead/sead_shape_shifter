<template>
  <div class="reconciliation-grid">
    <v-toolbar density="comfortable" color="transparent" flat class="mb-2">
      <v-chip-group v-model="statusFilter" mandatory>
        <v-chip value="all" variant="outlined">All ({{ previewData.length }})</v-chip>
        <v-chip value="proposed" color="warning" variant="outlined">Proposed ({{ stats.proposed }})</v-chip>
        <v-chip value="accepted" color="success" variant="outlined">Accepted ({{ stats.accepted }})</v-chip>
        <v-chip value="rejected" color="error" variant="outlined">Rejected ({{ stats.rejected }})</v-chip>
        <v-chip value="local-only" color="grey" variant="outlined">Local-only ({{ stats.localOnly }})</v-chip>
        <v-chip value="unresolved" color="warning" variant="outlined">Unresolved ({{ stats.unresolved }})</v-chip>
        <v-chip value="errors" color="error" variant="outlined">Errors ({{ stats.errors }})</v-chip>
      </v-chip-group>

      <v-spacer />

      <v-text-field
        v-model="searchQuery"
        data-testid="reconciliation-search"
        prepend-inner-icon="mdi-magnify"
        placeholder="Search rows..."
        density="compact"
        variant="outlined"
        clearable
        hide-details
        style="max-width: 260px"
      />

      <v-btn
        data-testid="preview-reconciliation"
        variant="tonal"
        color="info"
        prepend-icon="mdi-table-eye"
        @click="previewDialog = true"
      >
        Preview
      </v-btn>
    </v-toolbar>

    <v-toolbar density="compact" color="transparent" flat class="mb-2">
      <v-chip size="small" variant="text">Showing {{ displayedRowCount }} of {{ previewData.length }} rows</v-chip>
      <v-spacer />
      <v-chip size="small" variant="text"
        >Review threshold: {{ thresholdPercent(entitySpec?.review_threshold) }}%</v-chip
      >
      <v-chip size="small" variant="text"
        >High score: {{ thresholdPercent(entitySpec?.auto_accept_threshold) }}%</v-chip
      >
    </v-toolbar>

    <v-alert
      v-if="actionError"
      data-testid="decision-error"
      type="error"
      variant="tonal"
      closable
      @click:close="actionError = null"
    >
      {{ actionError }}
    </v-alert>

    <div @click="handleGridClick">
      <ag-grid-vue
        class="ag-theme-material reconciliation-ag-grid"
        :columnDefs="columnDefs"
        :rowData="gridData"
        :defaultColDef="defaultColDef"
        :rowClassRules="rowClassRules"
        :quickFilterText="appliedSearchQuery"
        :suppressRowClickSelection="true"
        @grid-ready="onGridReady"
        @filter-changed="onFilterChanged"
        @model-updated="onFilterChanged"
        :domLayout="'normal'"
      />
    </div>

    <v-dialog v-model="candidateDialog" max-width="700">
      <v-card>
        <v-card-title class="d-flex align-center">Review candidates</v-card-title>
        <v-card-subtitle v-if="selectedRow">
          {{ getRowDisplayText(selectedRow) }} · Key: {{ selectedRow.local_key_value || 'Unavailable' }}
        </v-card-subtitle>
        <v-card-text>
          <v-list v-if="selectedRow?.candidates?.length">
            <v-list-item
              v-for="candidate in selectedRow.candidates"
              :key="candidate.id"
              data-testid="candidate-option"
              @click="selectCandidate(candidate)"
              :class="{ 'bg-blue-lighten-5': selectedCandidate?.id === candidate.id }"
            >
              <template #prepend>
                <v-avatar :color="candidate.score == null ? 'grey' : getConfidenceColor(candidate.score)" size="36">
                  {{ candidate.score == null ? '—' : `${Math.round(candidate.score)}%` }}
                </v-avatar>
              </template>
              <v-list-item-title>{{ candidate.name }}</v-list-item-title>
              <v-list-item-subtitle v-if="candidate.description">{{ candidate.description }}</v-list-item-subtitle>
              <template #append>
                <v-chip size="small" variant="outlined"
                  >ID: {{ extractIdFromUri(candidate.id) ?? 'Unavailable' }}</v-chip
                >
              </template>
            </v-list-item>
          </v-list>
          <div v-else class="text-center text-grey py-8">
            No candidates available. Search for a candidate or add a manual link.
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="candidateDialog = false">Cancel</v-btn>
          <v-btn
            data-testid="accept-candidate"
            variant="tonal"
            color="primary"
            :loading="selectedRow ? isBusy(selectedRow.local_key_value) : false"
            :disabled="!selectedCandidate || !selectedRow?.local_key_value"
            @click="acceptCandidate"
          >
            Accept selected candidate
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <AlternativeSearchDialog
      v-model="alternativeSearchDialog"
      :project-name="projectName"
      :entity-name="entityName"
      :target-field="targetField"
      :original-query="selectedRow ? getRowDisplayText(selectedRow) : ''"
      @accept="handleAlternativeAccept"
    />

    <v-dialog v-model="localOnlyDialog" max-width="600">
      <v-card>
        <v-card-title>Mark row as local-only</v-card-title>
        <v-card-subtitle v-if="selectedRow">
          {{ getRowDisplayText(selectedRow) }} · Key: {{ selectedRow.local_key_value }}
        </v-card-subtitle>
        <v-card-text>
          <p class="mb-4">This records that the row should not be linked to a target entity.</p>
          <v-textarea v-model="localOnlyNotes" label="Reason (optional)" rows="3" variant="outlined" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="localOnlyDialog = false">Cancel</v-btn>
          <v-btn
            data-testid="confirm-local-only"
            variant="tonal"
            color="warning"
            :loading="selectedRow ? isBusy(selectedRow.local_key_value) : false"
            :disabled="!selectedRow?.local_key_value"
            @click="confirmLocalOnly"
          >
            Mark local-only
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <preview-matched-data-dialog v-model="previewDialog" :preview-data="previewData" :entity-spec="entitySpec" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type { ColDef, GridApi, GridReadyEvent, ICellRendererParams, IRowNode, RowClassParams } from 'ag-grid-community'
import type {
  DecisionUpdateRequest,
  EntityResolutionSet,
  MappingEntityResponse,
  ReconciliationCandidate,
  ReconciliationPreviewRow,
} from '@/types'
import AlternativeSearchDialog from './AlternativeSearchDialog.vue'
import PreviewMatchedDataDialog from './PreviewMatchedDataDialog.vue'

import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-material.css'

interface Props {
  entitySpec: EntityResolutionSet | null
  previewData: ReconciliationPreviewRow[]
  mappingData: MappingEntityResponse | null
  loading?: boolean
  projectName: string
  entityName: string
  targetField: string
  submitDecision: (request: DecisionUpdateRequest) => Promise<void>
}

const props = withDefaults(defineProps<Props>(), { loading: false })

const emit = defineEmits<{
  'manual-link': [row: ReconciliationPreviewRow]
}>()

const gridApi = ref<GridApi | null>(null)
const statusFilter = ref<'all' | 'proposed' | 'accepted' | 'rejected' | 'local-only' | 'unresolved' | 'errors'>('all')
const searchQuery = ref('')
const appliedSearchQuery = ref('')
const displayedRowCount = ref(0)
const actionError = ref<string | null>(null)
const busyKeys = ref(new Set<string>())
const selectedRow = ref<ReconciliationPreviewRow | null>(null)
const selectedCandidate = ref<ReconciliationCandidate | null>(null)
const candidateDialog = ref(false)
const alternativeSearchDialog = ref(false)
const localOnlyDialog = ref(false)
const localOnlyNotes = ref('')
const previewDialog = ref(false)

const defaultColDef: ColDef = {
  resizable: true,
  sortable: true,
  filter: true,
  editable: false,
}

const gridRows = computed(() =>
  props.previewData.map((row) => {
    const sidecarLink = row.local_key_value ? props.mappingData?.links[row.local_key_value] : undefined
    const committedLink = sidecarLink?.committed_at ? sidecarLink : undefined
    const savedRowId = props.mappingData ? row[props.mappingData.public_id] : null
    return {
      ...row,
      saved_row_id: savedRowId,
      status_display: formatStatus(row),
      effective_id: props.mappingData ? (committedLink?.target_id ?? savedRowId) : null,
      effective_id_status: committedLink
        ? committedLink.source === 'manual'
          ? 'Trusted manual · not checked'
          : committedLink.source === 'reconciliation'
            ? committedLink.verified_at
              ? `reconciliation · verified ${committedLink.verified_at}`
              : 'reconciliation · unverified'
            : `${committedLink.source} · not checked`
        : props.mappingData
          ? 'Saved row ID'
          : 'Sidecar unavailable',
      confidence_percent: row.confidence == null ? null : row.confidence * 100,
      errors_display: row.errors?.join('; ') ?? '',
      row_style_class: rowStyleClass(row),
    }
  })
)

const columnDefs = computed<ColDef[]>(() => {
  if (!props.entitySpec) return []

  const columns: ColDef[] = [
    {
      field: props.targetField,
      headerName: `${props.targetField.replace(/_/g, ' ')} (Search label)`,
      pinned: 'left',
      width: 200,
    },
    { field: 'local_key_value', headerName: 'Business key', pinned: 'left', width: 170 },
  ]

  for (const column of new Set(Object.values(props.entitySpec.property_mappings))) {
    if (column !== props.targetField) columns.push({ field: column, headerName: column.replace(/_/g, ' '), width: 150 })
  }

  columns.push(
    { field: 'saved_row_id', headerName: 'Saved row ID', width: 120 },
    { field: 'target_id', headerName: 'Decision ID', width: 120 },
    {
      field: 'confidence_percent',
      headerName: 'Decision confidence',
      width: 150,
      valueFormatter: (params) => (params.value == null ? 'Unknown' : `${Math.round(params.value)}%`),
    },
    { field: 'status_display', headerName: 'Decision status', width: 140 },
    { field: 'effective_id', headerName: 'Effective ID', width: 120 },
    { field: 'effective_id_status', headerName: 'Effective ID source', width: 190 },
    { field: 'errors_display', headerName: 'Row errors', width: 240 },
    {
      field: 'candidates',
      headerName: 'Actions',
      width: 470,
      pinned: 'right',
      sortable: false,
      filter: false,
      cellRenderer: (params: ICellRendererParams) => {
        const row = params.data as ReconciliationPreviewRow | undefined
        if (!row) return ''
        const key = row.local_key_value
        const encodedKey = key ? encodeURIComponent(key) : ''
        const disabled = !key || props.loading || isBusy(key)
        const buttons = []
        if (row.candidates?.length) {
          buttons.push(
            `<button class="candidate-btn" data-local-key="${encodedKey}" data-action="review" ${disabled ? 'disabled' : ''}>Review (${row.candidates.length})</button>`
          )
        }
        buttons.push(
          `<button class="search-btn" data-local-key="${encodedKey}" data-action="search" ${disabled ? 'disabled' : ''}>Search</button>`
        )
        buttons.push(
          `<button class="reject-btn" data-local-key="${encodedKey}" data-action="reject" ${disabled ? 'disabled' : ''}>Reject</button>`
        )
        buttons.push(
          `<button class="local-only-btn" data-local-key="${encodedKey}" data-action="local-only" ${disabled ? 'disabled' : ''}>Local-only</button>`
        )
        buttons.push(
          `<button class="manual-link-btn" data-local-key="${encodedKey}" data-action="manual-link" ${!key ? 'disabled' : ''}>Manual link</button>`
        )
        return buttons.join(' ')
      },
    }
  )

  return columns
})

const rowClassRules: Record<string, (params: RowClassParams) => boolean> = {
  'row-needs-attention': (params) => params.data?.row_style_class === 'row-needs-attention',
  'row-accepted': (params) => params.data?.row_style_class === 'row-accepted',
  'row-rejected': (params) => params.data?.row_style_class === 'row-rejected',
  'row-local-only': (params) => params.data?.row_style_class === 'row-local-only',
  'row-proposed': (params) => params.data?.row_style_class === 'row-proposed',
}

/** Status filter only. Text search is delegated to ag-Grid quick filtering. */
const gridData = computed(() => {
  const rows = gridRows.value
  if (statusFilter.value === 'errors') return rows.filter((row) => Boolean(row.errors?.length))
  if (statusFilter.value === 'unresolved') {
    return rows.filter(
      (row) => !row.local_key_value || row.status == null || (row.status === 'proposed' && !row.candidates?.length)
    )
  }
  if (statusFilter.value !== 'all') return rows.filter((row) => row.status === statusFilter.value)
  return rows
})

/** One pass over the rows instead of six separate filter passes. */
const stats = computed(() => {
  const counts = { proposed: 0, accepted: 0, rejected: 0, localOnly: 0, unresolved: 0, errors: 0 }
  for (const row of props.previewData) {
    if (row.status === 'proposed') counts.proposed += 1
    else if (row.status === 'accepted') counts.accepted += 1
    else if (row.status === 'rejected') counts.rejected += 1
    else if (row.status === 'local-only') counts.localOnly += 1
    if (!row.local_key_value || row.status == null || (row.status === 'proposed' && !row.candidates?.length)) {
      counts.unresolved += 1
    }
    if (row.errors?.length) counts.errors += 1
  }
  return counts
})

function onGridReady(event: GridReadyEvent) {
  gridApi.value = event.api
  displayedRowCount.value = event.api.getDisplayedRowCount()
}

function onFilterChanged() {
  displayedRowCount.value = gridApi.value?.getDisplayedRowCount() ?? 0
}

// Debounce typed search so each keystroke does not start a filter pass.
let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(searchQuery, (value) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    appliedSearchQuery.value = value
  }, 250)
})

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

// Row count changes with the status filter, which is applied in Vue rather than the grid.
watch(gridData, () => {
  setTimeout(onFilterChanged)
})

function thresholdPercent(value: number | undefined): number {
  return Math.round((value ?? 0) * 100)
}

function getConfidenceColor(score: number): string {
  const high = (props.entitySpec?.auto_accept_threshold ?? 0.95) * 100
  const review = (props.entitySpec?.review_threshold ?? 0.7) * 100
  if (score >= high) return 'success'
  if (score >= review) return 'warning'
  return 'error'
}

function formatStatus(row: ReconciliationPreviewRow | undefined): string {
  if (!row?.local_key_value) return 'Unreviewable'
  if (row.errors?.length) return 'Needs attention'
  if (row.status == null || (row.status === 'proposed' && !row.candidates?.length)) return 'Unresolved'
  if (row.status === 'local-only') return 'Local-only'
  if (row.status === 'accepted' && !row.candidate_id) return 'Accepted · re-accept candidate'
  if (row.status === 'accepted' || row.status === 'rejected' || row.status === 'proposed') {
    return row.status.charAt(0).toUpperCase() + row.status.slice(1)
  }
  return 'Unreviewable'
}

/** Row background class. Computed once per row instead of a style object per render. */
function rowStyleClass(row: ReconciliationPreviewRow): string {
  if (row.errors?.length) return 'row-needs-attention'
  if (row.status === 'accepted') return 'row-accepted'
  if (row.status === 'rejected') return 'row-rejected'
  if (row.status === 'local-only') return 'row-local-only'
  if (row.status === 'proposed') return 'row-proposed'
  return ''
}

function extractIdFromUri(uri: string): number | null {
  const match = uri.match(/\/(\d+)\/?$/)
  return match?.[1] ? Number(match[1]) : null
}

function getRowDisplayText(row: ReconciliationPreviewRow): string {
  return String(row[props.targetField] ?? '')
}

function isBusy(localKeyValue: string | null | undefined): boolean {
  return Boolean(localKeyValue && busyKeys.value.has(localKeyValue))
}

function setBusy(localKeyValue: string, busy: boolean) {
  const next = new Set(busyKeys.value)
  if (busy) next.add(localKeyValue)
  else next.delete(localKeyValue)
  busyKeys.value = next
  refreshRowCells(localKeyValue)
}

/** Refresh the cells of one row instead of every cell in the grid. */
function refreshRowCells(localKeyValue: string) {
  const api = gridApi.value
  if (!api) return
  const nodes: IRowNode[] = []
  api.forEachNode((node) => {
    if (node.data?.local_key_value === localKeyValue) nodes.push(node)
  })
  if (nodes.length > 0) api.refreshCells({ rowNodes: nodes, force: true })
}

async function persistDecision(
  row: ReconciliationPreviewRow,
  status: DecisionUpdateRequest['status'],
  targetId?: number,
  candidateId?: string,
  notes?: string
): Promise<boolean> {
  const key = row.local_key_value
  if (!key) {
    actionError.value = 'This row has no valid business key and cannot receive a decision.'
    return false
  }

  setBusy(key, true)
  actionError.value = null
  try {
    const request: DecisionUpdateRequest = {
      local_key_value: key,
      status,
      ...(targetId === undefined ? {} : { target_id: targetId }),
      ...(candidateId === undefined ? {} : { candidate_id: candidateId }),
      ...(notes === undefined ? {} : { notes }),
    }
    await props.submitDecision(request)
    return true
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : 'The decision could not be saved.'
    return false
  } finally {
    setBusy(key, false)
  }
}

function showCandidates(row: ReconciliationPreviewRow) {
  selectedRow.value = row
  selectedCandidate.value = null
  candidateDialog.value = true
}

function selectCandidate(candidate: ReconciliationCandidate) {
  selectedCandidate.value = candidate
}

async function acceptCandidate() {
  const row = selectedRow.value
  const candidate = selectedCandidate.value
  if (!row || !candidate) return
  const targetId = extractIdFromUri(candidate.id)
  if (targetId === null) {
    actionError.value = `Candidate ID is not a numeric target ID: ${candidate.id}`
    return
  }
  if (await persistDecision(row, 'accepted', targetId, candidate.id)) candidateDialog.value = false
}

function handleGridClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  const button = target.closest('button[data-action]') as HTMLButtonElement | null
  if (!button || button.disabled) return
  const encodedKey = button.getAttribute('data-local-key')
  if (!encodedKey) return
  const key = decodeURIComponent(encodedKey)
  const row = gridRows.value.find((item) => item.local_key_value === key)
  if (!row) return

  switch (button.getAttribute('data-action')) {
    case 'review':
      showCandidates(row)
      break
    case 'search':
      selectedRow.value = row
      alternativeSearchDialog.value = true
      break
    case 'reject':
      void persistDecision(row, 'rejected')
      break
    case 'local-only':
      selectedRow.value = row
      localOnlyNotes.value = ''
      localOnlyDialog.value = true
      break
    case 'manual-link':
      emit('manual-link', row)
      break
  }
}

async function handleAlternativeAccept(candidate: ReconciliationCandidate) {
  const row = selectedRow.value
  if (!row) return
  const targetId = extractIdFromUri(candidate.id)
  if (targetId === null) {
    actionError.value = `Candidate ID is not a numeric target ID: ${candidate.id}`
    return
  }
  await persistDecision(row, 'accepted', targetId, candidate.id)
}

async function confirmLocalOnly() {
  if (!selectedRow.value) return
  const saved = await persistDecision(
    selectedRow.value,
    'local-only',
    undefined,
    undefined,
    localOnlyNotes.value.trim() || undefined
  )
  if (saved) localOnlyDialog.value = false
}
</script>

<style scoped>
.reconciliation-grid {
  width: 100%;
}

.reconciliation-ag-grid {
  width: 100%;
  /* Fixed height keeps ag-Grid row virtualization enabled, so only the visible
     rows are rendered. An auto height would render every row at once. */
  height: 68vh;
  min-height: 400px;
}

:deep(.reconciliation-ag-grid .ag-row.row-needs-attention) {
  background-color: #fff3e0;
}

:deep(.reconciliation-ag-grid .ag-row.row-accepted) {
  background-color: #e8f5e9;
}

:deep(.reconciliation-ag-grid .ag-row.row-rejected) {
  background-color: #ffebee;
}

:deep(.reconciliation-ag-grid .ag-row.row-local-only) {
  background-color: #f5f5f5;
}

:deep(.reconciliation-ag-grid .ag-row.row-proposed) {
  background-color: #fff8e1;
}

:deep(.candidate-btn),
:deep(.search-btn),
:deep(.reject-btn),
:deep(.local-only-btn),
:deep(.manual-link-btn) {
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin: 2px;
  padding: 5px 8px;
}

:deep(.candidate-btn) {
  background: #e3f2fd;
  color: #1565c0;
}

:deep(.search-btn),
:deep(.manual-link-btn) {
  background: #eeeeee;
  color: #333333;
}

:deep(.reject-btn) {
  background: #ffebee;
  color: #b71c1c;
}

:deep(.local-only-btn) {
  background: #fff3e0;
  color: #8d5b00;
}

:deep(button:disabled) {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
