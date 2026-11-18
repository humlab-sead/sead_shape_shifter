<template>
  <div class="reconciliation-grid">
    <v-toolbar density="comfortable" color="transparent" flat class="mb-2">
      <v-chip-group v-model="statusFilter" mandatory>
        <v-chip value="all" variant="outlined">All ({{ previewData.length }})</v-chip>
        <v-chip
          data-testid="status-filter-proposed"
          value="proposed"
          :color="RECONCILIATION_STATUS_PRESENTATION.proposed.color"
          variant="outlined"
          :aria-label="`Proposed (${stats.proposed})`"
          title="Proposed"
        >
          <v-icon
            :icon="RECONCILIATION_STATUS_PRESENTATION.proposed.icon"
            :color="RECONCILIATION_STATUS_PRESENTATION.proposed.color"
            size="small"
            class="me-2"
            aria-hidden="true"
          />
          Proposed ({{ stats.proposed }})
        </v-chip>
        <v-chip
          data-testid="status-filter-accepted"
          value="accepted"
          :color="RECONCILIATION_STATUS_PRESENTATION.accepted.color"
          variant="outlined"
          :aria-label="`Accepted (${stats.accepted})`"
          title="Accepted"
        >
          <v-icon
            :icon="RECONCILIATION_STATUS_PRESENTATION.accepted.icon"
            :color="RECONCILIATION_STATUS_PRESENTATION.accepted.color"
            size="small"
            class="me-2"
            aria-hidden="true"
          />
          Accepted ({{ stats.accepted }})
        </v-chip>
        <v-chip
          data-testid="status-filter-rejected"
          value="rejected"
          :color="RECONCILIATION_STATUS_PRESENTATION.rejected.color"
          variant="outlined"
          :aria-label="`Rejected (${stats.rejected})`"
          title="Rejected"
        >
          <v-icon
            :icon="RECONCILIATION_STATUS_PRESENTATION.rejected.icon"
            :color="RECONCILIATION_STATUS_PRESENTATION.rejected.color"
            size="small"
            class="me-2"
            aria-hidden="true"
          />
          Rejected ({{ stats.rejected }})
        </v-chip>
        <v-chip
          data-testid="status-filter-local-only"
          value="local-only"
          :color="RECONCILIATION_STATUS_PRESENTATION.local.color"
          variant="outlined"
          :aria-label="`New (${stats.localOnly})`"
          title="New"
        >
          <v-icon
            :icon="RECONCILIATION_STATUS_PRESENTATION.local.icon"
            :color="RECONCILIATION_STATUS_PRESENTATION.local.color"
            size="small"
            class="me-2"
            aria-hidden="true"
          />
          New ({{ stats.localOnly }})
        </v-chip>
        <v-chip
          data-testid="status-filter-unresolved"
          value="unresolved"
          :color="RECONCILIATION_STATUS_PRESENTATION.unresolved.color"
          variant="outlined"
          :aria-label="`Unresolved (${stats.unresolved})`"
          title="Unresolved"
        >
          <v-icon
            :icon="RECONCILIATION_STATUS_PRESENTATION.unresolved.icon"
            :color="RECONCILIATION_STATUS_PRESENTATION.unresolved.color"
            size="small"
            class="me-2"
            aria-hidden="true"
          />
          Unresolved ({{ stats.unresolved }})
        </v-chip>
        <v-chip
          data-testid="status-filter-errors"
          value="errors"
          :color="RECONCILIATION_STATUS_PRESENTATION.errors.color"
          variant="outlined"
          :aria-label="`Errors (${stats.errors})`"
          title="Errors"
        >
          <v-icon
            :icon="RECONCILIATION_STATUS_PRESENTATION.errors.icon"
            :color="RECONCILIATION_STATUS_PRESENTATION.errors.color"
            size="small"
            class="me-2"
            aria-hidden="true"
          />
          Errors ({{ stats.errors }})
        </v-chip>
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
        :rowHeight="32"
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
        <v-card-title>Mark row as New</v-card-title>
        <v-card-subtitle v-if="selectedRow">
          {{ getRowDisplayText(selectedRow) }} · Key: {{ selectedRow.local_key_value }}
        </v-card-subtitle>
        <v-card-text>
          <p class="mb-4">
            This row has no mapping to an existing target. Mark it New so the ingester treats it as a new record; ID
            allocation depends on the selected ingester mode.
          </p>
          <v-textarea v-model="localOnlyNotes" label="Reason (optional)" rows="3" variant="outlined" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="localOnlyDialog = false">Cancel</v-btn>
          <v-btn
            data-testid="confirm-new"
            variant="tonal"
            color="warning"
            :loading="selectedRow ? isBusy(selectedRow.local_key_value) : false"
            :disabled="!selectedRow?.local_key_value"
            @click="confirmLocalOnly"
          >
            Mark as New
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type {
  ColDef,
  ColGroupDef,
  GridApi,
  GridReadyEvent,
  ICellRendererParams,
  IRowNode,
  RowClassParams,
} from 'ag-grid-community'
import type {
  DecisionUpdateRequest,
  EntityResolutionSet,
  MappingLink,
  MappingEntityResponse,
  ReconciliationCandidate,
  ReconciliationPreviewRow,
} from '@/types'
import AlternativeSearchDialog from './AlternativeSearchDialog.vue'
import {
  getReconciliationStatusPresentation,
  RECONCILIATION_ACTION_ICONS,
  RECONCILIATION_STATUS_PRESENTATION,
} from './reconciliationHelp'

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

interface CurrentIdSource {
  label: string
  description: string
  icon: string
  verificationIcon?: string
  verificationColor?: 'success' | 'warning'
}

const props = withDefaults(defineProps<Props>(), { loading: false })

const emit = defineEmits<{
  'manual-link': [row: ReconciliationPreviewRow]
  'remove-saved-entry': [row: ReconciliationPreviewRow]
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

const defaultColDef: ColDef = {
  resizable: true,
  sortable: true,
  filter: true,
  editable: false,
}

function getCurrentIdSource(link: MappingLink | undefined, mappingAvailable: boolean): CurrentIdSource {
  if (!mappingAvailable) {
    return {
      label: 'Unavailable',
      description: 'The mapping sidecar could not be loaded, so the current ID cannot be confirmed.',
      icon: 'mdi-database-off-outline',
    }
  }
  if (!link?.committed_at) {
    return {
      label: 'Normalized',
      description: 'No committed mapping link overrides the normalized row ID.',
      icon: 'mdi-table-row',
    }
  }
  if (link.source === 'manual') {
    return {
      label: 'Manual',
      description: 'This trusted manual link was not checked.',
      icon: 'mdi-pencil-outline',
    }
  }
  if (link.source === 'reconciliation') {
    return link.verified_at
      ? {
          label: 'Reconciled · verified',
          description: `Verified at ${link.verified_at}.`,
          icon: 'mdi-link-variant',
          verificationIcon: 'mdi-check-circle-outline',
          verificationColor: 'success',
        }
      : {
          label: 'Reconciled · unverified',
          description: 'This reconciled link has not been verified.',
          icon: 'mdi-link-variant',
          verificationIcon: 'mdi-help-circle-outline',
          verificationColor: 'warning',
        }
  }
  return {
    label: 'Imported',
    description: 'This imported mapping was not checked.',
    icon: 'mdi-database-import-outline',
  }
}

function hasDisplayableId(value: unknown): boolean {
  return value != null && String(value).trim() !== ''
}

const gridRows = computed(() =>
  props.previewData.map((row) => {
    const sidecarLink = row.local_key_value ? props.mappingData?.links[row.local_key_value] : undefined
    const committedLink = sidecarLink?.committed_at ? sidecarLink : undefined
    const savedRowId = props.mappingData ? row[props.mappingData.public_id] : null
    const currentId = props.mappingData ? (committedLink?.target_id ?? savedRowId) : null
    const currentIdSource = getCurrentIdSource(committedLink, Boolean(props.mappingData))
    const hasCurrentId = hasDisplayableId(currentId)
    const showCurrentIdSource = hasCurrentId || !props.mappingData
    return {
      ...row,
      current_id: currentId,
      current_id_source_label: showCurrentIdSource ? currentIdSource.label : null,
      current_id_source_description: showCurrentIdSource ? currentIdSource.description : null,
      current_id_source_icon: showCurrentIdSource ? currentIdSource.icon : null,
      current_id_source_verification_icon: showCurrentIdSource ? (currentIdSource.verificationIcon ?? null) : null,
      current_id_source_verification_color: showCurrentIdSource ? (currentIdSource.verificationColor ?? null) : null,
      status_display: formatStatus(row),
      confidence_percent: row.confidence == null ? null : row.confidence * 100,
      errors_display: row.errors?.join('; ') ?? '',
      row_style_class: rowStyleClass(row),
    }
  })
)

const columnDefs = computed<(ColDef | ColGroupDef)[]>(() => {
  if (!props.entitySpec) return []

  const columns: (ColDef | ColGroupDef)[] = [
    {
      field: 'status_display',
      headerName: 'Review status',
      width: 140,
      pinned: 'left',
      filter: false,
      cellRenderer: (params: ICellRendererParams) => {
        const label = typeof params.value === 'string' ? params.value : ''
        const presentation = getReconciliationStatusPresentation(label)
        if (!presentation) return label

        const status = document.createElement('span')
        status.className = 'reconciliation-status-icon'
        status.setAttribute('role', 'img')
        status.setAttribute('aria-label', label)
        const errorMessage = params.data?.errors?.join('; ')
        status.title = label === 'Needs attention' && errorMessage ? errorMessage : label

        const icon = document.createElement('span')
        icon.className = `mdi ${presentation.icon} text-${presentation.color}`
        icon.setAttribute('aria-hidden', 'true')
        status.append(icon)
        return status
      },
    },
    { field: 'local_key_value', headerName: 'Business key', pinned: 'left', width: 170 },
    {
      field: props.targetField,
      headerName: `${props.targetField.replace(/_/g, ' ')} (Search label)`,
      pinned: 'left',
      width: 200,
    },
  ]

  const mappedColumns = [...new Set(Object.values(props.entitySpec.property_mappings))].filter(
    (column) => column !== props.targetField
  )
  if (mappedColumns.length > 0) {
    columns.push({
      headerName: 'Property mappings',
      groupId: 'property-mappings',
      openByDefault: false,
      children: mappedColumns.map((column) => ({
        field: column,
        headerName: column.replace(/_/g, ' '),
        width: 150,
      })),
    })
  }

  columns.push(
    { field: 'target_id', headerName: 'Selected target ID', width: 150 },
    {
      field: 'confidence_percent',
      headerName: 'Score',
      filter: false,
      width: 150,
      valueFormatter: (params) => (params.value == null ? '' : `${Math.round(params.value)}%`),
    },
    {
      field: 'current_id',
      headerName: 'Current ID',
      filter: false,
      width: 270,
      cellRenderer: (params: ICellRendererParams) => {
        const cell = document.createElement('div')
        cell.className = 'current-id-cell'

        const id = document.createElement('span')
        id.className = 'current-id-value'
        id.textContent = params.value == null ? '' : String(params.value)
        cell.append(id)

        const source = params.data?.current_id_source_label
        if (typeof source === 'string') {
          const badge = document.createElement('span')
          badge.className = 'current-id-source-badge'
          const sourceIcon = params.data?.current_id_source_icon
          if (typeof sourceIcon === 'string') {
            const icon = document.createElement('span')
            icon.className = `mdi ${sourceIcon} current-id-source-icon`
            icon.setAttribute('aria-hidden', 'true')
            badge.append(icon)
          }
          const verificationIcon = params.data?.current_id_source_verification_icon
          if (typeof verificationIcon === 'string') {
            const icon = document.createElement('span')
            const verificationColor = params.data?.current_id_source_verification_color
            const colorClass = typeof verificationColor === 'string' ? ` text-${verificationColor}` : ''
            icon.className = `mdi ${verificationIcon} current-id-source-verification-icon${colorClass}`
            icon.setAttribute('aria-hidden', 'true')
            badge.append(icon)
          }
          const label = document.createElement('span')
          label.className = 'current-id-source-label'
          label.textContent = source
          badge.append(label)
          const description = params.data?.current_id_source_description
          if (typeof description === 'string') {
            badge.title = description
            badge.setAttribute('aria-label', `${source}: ${description}`)
          }
          cell.append(badge)
        }
        return cell
      },
    },
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
        buttons.push(
          `<button type="button" class="search-btn action-icon-btn" data-local-key="${encodedKey}" data-action="search" aria-label="Search for another candidate" data-tooltip="Search for another candidate" ${disabled ? 'disabled' : ''}><span class="mdi ${RECONCILIATION_ACTION_ICONS.search} row-action-icon" aria-hidden="true"></span></button>`
        )
        buttons.push(
          `<button type="button" class="reject-btn action-icon-btn" data-local-key="${encodedKey}" data-action="reject" aria-label="Reject this row" data-tooltip="Reject this row" ${disabled ? 'disabled' : ''}><span class="mdi ${RECONCILIATION_ACTION_ICONS.reject} row-action-icon" aria-hidden="true"></span></button>`
        )
        buttons.push(
          `<button type="button" class="local-only-btn action-icon-btn" data-local-key="${encodedKey}" data-action="local-only" aria-label="Mark this row as New" data-tooltip="Mark this row as New" ${disabled ? 'disabled' : ''}><span class="mdi ${RECONCILIATION_ACTION_ICONS.new} row-action-icon" aria-hidden="true"></span></button>`
        )
        buttons.push(
          `<button type="button" class="manual-link-btn action-icon-btn" data-local-key="${encodedKey}" data-action="manual-link" aria-label="Add a manual link for this row" data-tooltip="Add a manual link for this row" ${!key ? 'disabled' : ''}><span class="mdi ${RECONCILIATION_ACTION_ICONS.manualLink} row-action-icon" aria-hidden="true"></span></button>`
        )
        const hasSavedDecision = row.status != null
        const hasSidecarEntry = Boolean(
          key && (props.mappingData?.links[key] || props.mappingData?.local_only_approvals?.[key])
        )
        if (hasSavedDecision || hasSidecarEntry) {
          buttons.push(
            `<button type="button" class="remove-saved-entry-btn action-icon-btn" data-local-key="${encodedKey}" data-action="remove-saved-entry" aria-label="Clear this row's saved decision or sidecar mapping" data-tooltip="Clear this row's saved decision or sidecar mapping" ${disabled ? 'disabled' : ''}><span class="mdi mdi-delete-outline row-action-icon" aria-hidden="true"></span></button>`
          )
        }
        if (row.candidates?.length) {
          buttons.push(
            `<button class="candidate-btn" data-local-key="${encodedKey}" data-action="review" ${disabled ? 'disabled' : ''}>Review (${row.candidates.length})</button>`
          )
        }
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
  'row-unresolved': (params) => params.data?.row_style_class === 'row-unresolved',
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
  if (row?.errors?.length) return 'Needs attention'
  if (!row?.local_key_value) return 'Unreviewable'
  if (row.status == null || (row.status === 'proposed' && !row.candidates?.length)) return 'Unresolved'
  if (row.status === 'local-only') return 'New'
  if (row.status === 'accepted' && !row.candidate_id) return 'Accepted · re-accept candidate'
  if (row.status === 'accepted' || row.status === 'rejected' || row.status === 'proposed') {
    return row.status.charAt(0).toUpperCase() + row.status.slice(1)
  }
  return 'Unreviewable'
}

/** Row background class. Computed once per row instead of a style object per render. */
function rowStyleClass(row: ReconciliationPreviewRow): string {
  const label = formatStatus(row)
  if (label === 'Needs attention') return 'row-needs-attention'
  if (label === 'Unresolved' || label === 'Unreviewable') return 'row-unresolved'
  if (label === 'Accepted' || label === 'Accepted · re-accept candidate') return 'row-accepted'
  if (label === 'Rejected') return 'row-rejected'
  if (label === 'New') return 'row-local-only'
  if (label === 'Proposed') return 'row-proposed'
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
    actionError.value = 'This row has no valid business key and cannot be reviewed.'
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
    actionError.value = error instanceof Error ? error.message : 'The review choice could not be saved.'
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
    case 'remove-saved-entry':
      emit('remove-saved-entry', row)
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

:deep(.current-id-cell) {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 100%;
  min-width: 0;
}

:deep(.current-id-value) {
  font-variant-numeric: tabular-nums;
}

:deep(.current-id-source-badge) {
  align-items: center;
  border: 1px solid currentColor;
  border-radius: 999px;
  display: inline-flex;
  font-size: 10px;
  gap: 4px;
  line-height: 1.4;
  opacity: 0.8;
  padding: 1px 6px;
  white-space: nowrap;
}

:deep(.current-id-source-icon) {
  font-size: 16px;
  line-height: 1;
}

:deep(.current-id-source-verification-icon) {
  font-size: 14px;
  line-height: 1;
}

:deep(.reconciliation-status-icon) {
  align-items: center;
  display: inline-flex;
  font-size: 18px;
  height: 100%;
}

:deep(.reconciliation-ag-grid .ag-row.row-needs-attention) {
  background-color: #ffebee;
}

:deep(.reconciliation-ag-grid .ag-row.row-accepted) {
  background-color: #e8f5e9;
}

:deep(.reconciliation-ag-grid .ag-row.row-rejected) {
  background-color: #f5f5f5;
}

:deep(.reconciliation-ag-grid .ag-row.row-local-only) {
  background-color: #f3e5f5;
}

:deep(.reconciliation-ag-grid .ag-row.row-proposed) {
  background-color: #e3f2fd;
}

:deep(.reconciliation-ag-grid .ag-row.row-unresolved) {
  background-color: #fff8e1;
}

:deep(.candidate-btn),
:deep(.search-btn),
:deep(.reject-btn),
:deep(.local-only-btn),
:deep(.manual-link-btn) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  height: 28px;
  margin: 2px;
  padding: 5px 8px;
  vertical-align: middle;
}

:deep(.action-icon-btn) {
  min-width: 30px;
  min-height: 28px;
  padding: 5px;
  position: relative;
}

:deep(.row-action-icon) {
  font-size: 16px;
  line-height: 1;
}

:deep(.action-icon-btn:hover::after),
:deep(.action-icon-btn:focus-visible::after) {
  content: attr(data-tooltip);
  position: absolute;
  top: calc(100% + 4px);
  left: 50%;
  z-index: 1000;
  transform: translateX(-50%);
  border-radius: 4px;
  background: #333333;
  color: #ffffff;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.2;
  padding: 4px 8px;
  pointer-events: none;
  white-space: nowrap;
}

:deep(.reconciliation-ag-grid .ag-cell[col-id='candidates']) {
  background-color: var(--ag-header-background-color);
  overflow: visible;
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
