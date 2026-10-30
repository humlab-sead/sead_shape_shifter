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
      <v-chip size="small" variant="text">Showing {{ filteredRowData.length }} of {{ previewData.length }} rows</v-chip>
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
        :rowData="filteredRowData"
        :defaultColDef="defaultColDef"
        :getRowStyle="getRowStyle"
        :suppressRowClickSelection="true"
        @grid-ready="onGridReady"
        :domLayout="'autoHeight'"
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
import { computed, ref } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type { ColDef, GridApi, GridReadyEvent, ICellRendererParams } from 'ag-grid-community'
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
          : `${committedLink.source} · not checked`
        : props.mappingData
          ? 'Saved row ID'
          : 'Sidecar unavailable',
      confidence_percent: row.confidence == null ? null : row.confidence * 100,
      errors_display: row.errors?.join('; ') ?? '',
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

const filteredRowData = computed(() => {
  let rows = gridRows.value
  if (statusFilter.value === 'errors') rows = rows.filter((row) => Boolean(row.errors?.length))
  else if (statusFilter.value === 'unresolved') {
    rows = rows.filter(
      (row) => !row.local_key_value || row.status == null || (row.status === 'proposed' && !row.candidates?.length)
    )
  } else if (statusFilter.value !== 'all') rows = rows.filter((row) => row.status === statusFilter.value)

  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return rows
  return rows.filter((row) =>
    Object.values(row).some((value) =>
      String(value ?? '')
        .toLowerCase()
        .includes(query)
    )
  )
})

const stats = computed(() => ({
  proposed: props.previewData.filter((row) => row.status === 'proposed').length,
  accepted: props.previewData.filter((row) => row.status === 'accepted').length,
  rejected: props.previewData.filter((row) => row.status === 'rejected').length,
  localOnly: props.previewData.filter((row) => row.status === 'local-only').length,
  unresolved: props.previewData.filter(
    (row) => !row.local_key_value || row.status == null || (row.status === 'proposed' && !row.candidates?.length)
  ).length,
  errors: props.previewData.filter((row) => Boolean(row.errors?.length)).length,
}))

function onGridReady(event: GridReadyEvent) {
  gridApi.value = event.api
}

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
  if (row.status === 'accepted' || row.status === 'rejected' || row.status === 'proposed') {
    return row.status.charAt(0).toUpperCase() + row.status.slice(1)
  }
  return 'Unreviewable'
}

function getRowStyle(params: { data?: ReconciliationPreviewRow }) {
  const row = params.data
  if (!row) return undefined
  if (row.errors?.length) return { background: '#fff3e0' }
  if (row.status === 'accepted') return { background: '#e8f5e9' }
  if (row.status === 'rejected') return { background: '#ffebee' }
  if (row.status === 'local-only') return { background: '#f5f5f5' }
  if (row.status === 'proposed') return { background: '#fff8e1' }
  return { background: '#fafafa' }
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
  gridApi.value?.refreshCells()
}

async function persistDecision(
  row: ReconciliationPreviewRow,
  status: DecisionUpdateRequest['status'],
  targetId?: number,
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
  if (await persistDecision(row, 'accepted', targetId)) candidateDialog.value = false
}

function handleGridClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  const button = target.closest('button[data-action]') as HTMLButtonElement | null
  if (!button || button.disabled) return
  const encodedKey = button.getAttribute('data-local-key')
  if (!encodedKey) return
  const key = decodeURIComponent(encodedKey)
  const row = filteredRowData.value.find((item) => item.local_key_value === key)
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
  await persistDecision(row, 'accepted', targetId)
}

async function confirmLocalOnly() {
  if (!selectedRow.value) return
  const saved = await persistDecision(
    selectedRow.value,
    'local-only',
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
  height: 100%;
  width: 100%;
  min-height: 400px;
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
