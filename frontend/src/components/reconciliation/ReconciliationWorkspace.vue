<template>
  <div
    ref="workspaceRoot"
    class="reconciliation-workspace"
    data-testid="reconciliation-workspace"
    @keydown.capture="handleKeydown"
  >
    <v-alert
      v-if="capabilityState === 'loading'"
      type="info"
      variant="tonal"
      class="mb-4"
      data-testid="workspace-loading"
    >
      <div class="d-flex align-center">
        <v-progress-circular indeterminate size="20" color="primary" class="mr-3" />
        Loading review capabilities from the reconciliation service...
      </div>
    </v-alert>

    <v-alert v-else-if="fallbackMessage" type="warning" variant="tonal" class="mb-4" data-testid="workspace-fallback">
      <v-alert-title>Record review is unavailable</v-alert-title>
      <p class="mb-2">{{ fallbackMessage }}</p>
      <p class="text-caption mb-3">
        The existing review grid, single-row decisions, and manual links remain available.
      </p>
      <v-btn data-testid="workspace-use-legacy" variant="tonal" size="small" @click="emit('fallback')">
        Use the review grid instead
      </v-btn>
    </v-alert>

    <template v-else>
      <v-alert
        v-if="draftStorageError"
        type="warning"
        variant="tonal"
        class="mb-4"
        data-testid="workspace-storage-warning"
      >
        {{ draftStorageError }}
      </v-alert>

      <v-alert
        v-if="restoreNotice"
        type="info"
        variant="tonal"
        class="mb-4"
        closable
        data-testid="workspace-restore-notice"
        @click:close="restoreNotice = null"
      >
        {{ restoreNotice }}
      </v-alert>

      <div class="workspace-layout">
        <v-card variant="outlined" class="workspace-queue">
          <v-card-title class="text-subtitle-1 d-flex align-center justify-space-between">
            <span>Needs review</span>
            <v-chip size="small" variant="tonal" data-testid="workspace-queue-count">{{ queueRows.length }}</v-chip>
          </v-card-title>
          <v-card-subtitle class="text-caption">
            {{ unsavedCount }} unsaved {{ unsavedCount === 1 ? 'decision' : 'decisions' }} staged
          </v-card-subtitle>
          <v-divider />
          <v-list density="compact" nav class="workspace-queue-list">
            <v-list-item
              v-for="entry in queueRows"
              :key="entry.key ?? `row-${entry.index}`"
              :data-testid="`workspace-row-${entry.index}`"
              :active="entry.key === activeKey"
              :disabled="entry.unreviewable"
              @click="focusRow(entry)"
            >
              <v-list-item-title>
                {{ entry.label || '(no label)' }}
                <v-icon v-if="hasDraft(entry.key)" size="x-small" color="primary" class="ml-1" title="Unsaved decision">
                  mdi-circle-edit-outline
                </v-icon>
              </v-list-item-title>
              <v-list-item-subtitle>
                <span class="text-caption">{{ entry.key ?? 'No business key' }}</span>
                <span v-if="entry.unreviewable" class="text-caption text-warning"> · {{ entry.reason }}</span>
                <span v-else-if="entry.savedStatus" class="text-caption"> · saved {{ entry.savedStatus }}</span>
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item v-if="!queueRows.length">
              <v-list-item-title class="text-caption text-medium-emphasis">No rows need review.</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>

        <v-card variant="outlined" class="workspace-pane">
          <v-card-title class="text-subtitle-1">
            {{ activeEntry?.label || 'Select a row' }}
          </v-card-title>
          <v-card-subtitle v-if="activeEntry" class="text-caption">
            {{ entityName }}.{{ targetField }} · key: {{ activeEntry.key ?? 'none' }} ·
            {{ activeEntry.savedStatus ? `saved ${activeEntry.savedStatus}` : 'no saved decision' }}
          </v-card-subtitle>

          <v-card-text>
            <v-alert v-if="!activeEntry" type="info" variant="tonal" data-testid="workspace-no-active-row">
              Choose a row in Needs review to search or browse targets.
            </v-alert>

            <template v-else>
              <v-alert v-if="activeEntry.unreviewable" type="warning" variant="tonal" class="mb-4">
                <div class="font-weight-bold">This row cannot be reviewed</div>
                <div class="text-caption">{{ activeEntry.reason }}</div>
                <div class="text-caption">Correct the source data, then search again.</div>
              </v-alert>

              <div v-if="activeRowErrors.length" class="mb-4" data-testid="workspace-row-errors">
                <div class="text-caption text-error" v-for="(message, index) in activeRowErrors" :key="index">
                  {{ message }}
                </div>
              </div>

              <v-btn-toggle
                v-model="mode"
                mandatory
                density="compact"
                class="mb-4"
                data-testid="workspace-mode-toggle"
                @update:model-value="onModeChange"
              >
                <v-btn
                  value="search"
                  size="small"
                  :disabled="!capabilities?.type.search_supported && !capabilities?.type.identifier_search_supported"
                >
                  <v-icon start size="small">mdi-magnify</v-icon>
                  Search
                </v-btn>
                <v-btn value="browse" size="small" :disabled="!capabilities?.type.browse_supported">
                  <v-icon start size="small">mdi-format-list-bulleted</v-icon>
                  Browse
                </v-btn>
              </v-btn-toggle>

              <div v-if="mode === 'search'">
                <v-text-field
                  v-model="searchQuery"
                  data-testid="workspace-search-input"
                  label="Search targets, or id: 42 for an exact lookup"
                  variant="outlined"
                  density="compact"
                  hide-details
                  @update:model-value="onQueryChange"
                  @keydown.enter="handleSearchKeydown"
                  @compositionstart="composing = true"
                  @compositionend="composing = false"
                />
                <div class="text-caption mt-1">
                  Enter searches immediately. Ranked results are limited suggestions, not proof of absence.
                </div>

                <v-alert
                  v-if="searchState === 'loading'"
                  type="info"
                  variant="tonal"
                  class="mt-3"
                  data-testid="workspace-search-loading"
                >
                  Searching...
                </v-alert>
                <v-alert
                  v-else-if="searchState === 'invalid'"
                  type="error"
                  variant="tonal"
                  class="mt-3"
                  data-testid="workspace-search-invalid"
                >
                  {{ searchError }}
                </v-alert>
                <v-alert
                  v-else-if="searchState === 'unsupported'"
                  type="warning"
                  variant="tonal"
                  class="mt-3"
                  data-testid="workspace-search-unsupported"
                >
                  {{ searchError }}
                </v-alert>
                <v-alert
                  v-else-if="searchState === 'error'"
                  type="error"
                  variant="tonal"
                  class="mt-3"
                  data-testid="workspace-search-error"
                >
                  {{ searchError }}
                </v-alert>
                <v-alert
                  v-else-if="searchState === 'empty'"
                  type="info"
                  variant="tonal"
                  class="mt-3"
                  data-testid="workspace-search-empty"
                >
                  No targets matched. A miss does not mean this row is new.
                </v-alert>
                <v-alert
                  v-else-if="searchState === 'idle'"
                  type="info"
                  variant="tonal"
                  class="mt-3"
                  data-testid="workspace-search-idle"
                >
                  Search is not running yet.
                </v-alert>

                <v-list
                  v-if="searchState === 'ready'"
                  density="compact"
                  data-testid="workspace-search-results"
                  class="mt-2"
                >
                  <v-list-item
                    v-for="record in searchResults"
                    :key="record.id"
                    :data-testid="`workspace-result-${record.target_id}`"
                    :active="selectedRecord?.id === record.id"
                    @click="selectRecord(record)"
                  >
                    <v-list-item-title>{{ record.name }}</v-list-item-title>
                    <v-list-item-subtitle class="text-caption">
                      {{ record.id }}
                      <span v-if="record.score !== null && record.score !== undefined">
                        · score {{ record.score }}</span
                      >
                      <span v-if="searchMode === 'exact'"> · exact match</span>
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </div>

              <div v-else>
                <v-alert
                  v-if="browseState === 'too-large'"
                  type="warning"
                  variant="tonal"
                  data-testid="workspace-browse-too-large"
                >
                  This list is too large to browse completely, so no partial list is shown. Use Search instead.
                </v-alert>
                <v-alert
                  v-else-if="browseState === 'unsupported'"
                  type="warning"
                  variant="tonal"
                  data-testid="workspace-browse-unsupported"
                >
                  {{ browseError }}
                </v-alert>
                <v-alert
                  v-else-if="browseState === 'error'"
                  type="error"
                  variant="tonal"
                  data-testid="workspace-browse-error"
                >
                  {{ browseError }}
                </v-alert>

                <template v-else>
                  <div class="d-flex align-center gap-2 mb-2">
                    <v-text-field
                      v-model="browseText"
                      data-testid="workspace-browse-filter"
                      label="Filter this complete list"
                      variant="outlined"
                      density="compact"
                      hide-details
                      @update:model-value="onBrowseFilterChange"
                    />
                    <v-btn
                      data-testid="workspace-browse-refresh"
                      variant="tonal"
                      size="small"
                      :loading="browseState === 'loading'"
                      @click="loadBrowse"
                    >
                      Refresh
                    </v-btn>
                  </div>
                  <div class="text-caption mb-2" data-testid="workspace-browse-summary">
                    {{
                      browseState === 'loading'
                        ? 'Loading the complete list...'
                        : `${filteredBrowseItems.length} of ${browseItems.length} complete records`
                    }}
                  </div>

                  <v-list v-if="visibleBrowseItems.length" density="compact" data-testid="workspace-browse-results">
                    <v-list-item
                      v-for="record in visibleBrowseItems"
                      :key="record.id"
                      :data-testid="`workspace-result-${record.target_id}`"
                      :active="selectedRecord?.id === record.id"
                      @click="selectRecord(record)"
                    >
                      <v-list-item-title>{{ record.name || '(no label)' }}</v-list-item-title>
                      <v-list-item-subtitle class="text-caption">{{ record.id }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                  <div
                    v-else-if="browseState === 'ready'"
                    class="text-caption text-medium-emphasis"
                    data-testid="workspace-browse-empty"
                  >
                    No record matches the filter.
                  </div>
                </template>
              </div>

              <v-textarea
                :model-value="activeDraft.notes"
                data-testid="workspace-notes"
                label="Notes (optional)"
                rows="2"
                density="compact"
                variant="outlined"
                class="mt-4"
                hide-details
                @update:model-value="updateActiveDraft({ notes: $event })"
              />

              <div class="mt-4" data-testid="workspace-selection">
                <div v-if="activeDraft.decision" class="d-flex align-center">
                  <v-icon start size="small" color="primary">mdi-check-circle-outline</v-icon>
                  <span v-if="activeDraft.decision.status === 'accepted'">
                    Staged target {{ activeDraft.decision.name }} ({{ activeDraft.decision.id }})
                  </span>
                  <span v-else>Staged New (local-only) decision</span>
                </div>
                <div v-else class="text-caption text-medium-emphasis">Nothing staged for this row.</div>
              </div>

              <div class="d-flex flex-wrap gap-2 mt-4">
                <v-btn
                  data-testid="workspace-stage-next"
                  variant="tonal"
                  color="primary"
                  :disabled="!selectedRecord || selectedRecord.target_id === null"
                  @click="stageSelected"
                >
                  Stage selected &amp; next
                </v-btn>
                <v-btn data-testid="workspace-stage-new" variant="tonal" color="secondary" @click="stageNew">
                  Stage New &amp; next
                </v-btn>
                <v-btn data-testid="workspace-skip" variant="text" @click="skipRow">Skip for now</v-btn>
                <v-btn
                  data-testid="workspace-clear-draft"
                  variant="text"
                  :disabled="!activeDraft.decision"
                  @click="clearDraft"
                >
                  Clear staged decision
                </v-btn>
              </div>
              <div class="text-caption mt-2">
                Shortcuts: Alt+Enter stages, Alt+Right/Left moves, Alt+Down skips. New approves later new-record
                handling; it does not create a record.
              </div>
            </template>
          </v-card-text>

          <v-divider />
          <v-card-actions class="flex-wrap">
            <v-btn data-testid="workspace-previous" variant="text" :disabled="!canGoPrevious" @click="previousRow">
              Previous
            </v-btn>
            <v-btn data-testid="workspace-next" variant="text" :disabled="!canGoNext" @click="nextRow">Next</v-btn>
            <v-spacer />
            <v-btn
              data-testid="workspace-save"
              variant="elevated"
              color="primary"
              :loading="saving"
              :disabled="saving || unsavedCount === 0"
              @click="saveDecisions"
            >
              Save decisions ({{ unsavedCount }})
            </v-btn>
          </v-card-actions>
        </v-card>
      </div>

      <v-alert v-if="saveError" type="error" variant="tonal" class="mt-4" data-testid="workspace-save-error">
        {{ saveError }}
      </v-alert>
      <div v-if="saveIssues.length" class="mt-2" data-testid="workspace-save-issues">
        <div v-for="(issue, index) in saveIssues" :key="index" class="text-caption text-error">
          {{ issue.local_key_value ? `${issue.local_key_value}: ` : '' }}{{ issue.message }}
        </div>
      </div>
      <v-alert v-if="saveSummary" type="success" variant="tonal" class="mt-4" data-testid="workspace-save-summary">
        {{ saveSummary }}
      </v-alert>

      <v-dialog :model-value="conflict !== null" max-width="640" persistent data-testid="workspace-conflict-dialog">
        <v-card>
          <v-card-title>Saved decisions changed since this workspace loaded</v-card-title>
          <v-card-text>
            <p class="mb-2">
              These rows already have a saved decision that changed after this workspace loaded them. Saving now
              replaces the newer decision for each listed row.
            </p>
            <ul class="mb-2">
              <li v-for="change in conflictChanges" :key="change.key" class="text-caption">
                {{ change.key }}: loaded
                {{
                  change.loaded
                    ? `${change.loaded.status ?? 'none'} / target ${change.loaded.target_id ?? 'none'}`
                    : 'no decision'
                }}, now
                {{
                  change.current
                    ? `${change.current.status ?? 'none'} / target ${change.current.target_id ?? 'none'}`
                    : 'no decision'
                }}
              </li>
            </ul>
            <p class="text-caption mb-2">
              This comparison runs before the save and is advisory. A change made between the comparison and the save is
              still replaced, because the save has no expected-state field.
            </p>
            <p class="text-caption">Your staged decisions stay exactly as they are unless you confirm.</p>
          </v-card-text>
          <v-card-actions>
            <v-btn data-testid="workspace-conflict-cancel" variant="text" @click="cancelConflict"
              >Keep staged decisions</v-btn
            >
            <v-spacer />
            <v-btn
              data-testid="workspace-conflict-confirm"
              variant="elevated"
              color="primary"
              :loading="saving"
              @click="confirmConflict"
            >
              Replace and save once
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useReconciliationStore } from '@/stores/reconciliation'
import type {
  DecisionBatchIssue,
  DecisionBatchResult,
  DecisionDraftRequest,
  DecisionState,
  ReconciliationPreviewRow,
  ReconciliationSelectionDescriptor,
  SelectionCapabilities,
  SelectionRecord,
  SelectionMode,
  WorkspaceDraft,
  WorkspaceRowDraft,
} from '@/types/reconciliation'

interface Props {
  projectName: string
  entityName: string
  targetField: string
  serviceType: string | null
  previewRows: ReconciliationPreviewRow[]
  selectionDescriptor: ReconciliationSelectionDescriptor | null
}

interface QueueEntry {
  key: string | null
  index: number
  label: string
  unreviewable: boolean
  reason: string | null
  savedStatus: string | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  fallback: []
  saved: [result: DecisionBatchResult]
}>()

const reconciliationStore = useReconciliationStore()
const workspaceRoot = ref<HTMLDivElement | null>(null)

/** Preview columns that carry reconciliation state rather than source data. */
const STATUS_FIELDS = new Set([
  'local_key_value',
  'status',
  'target_id',
  'candidate_id',
  'confidence',
  'notes',
  'candidates',
  'errors',
])

const composing = ref(false)
const capabilities = ref<SelectionCapabilities | null>(null)
const capabilityState = ref<'loading' | 'ready' | 'fallback'>('loading')
const fallbackMessage = ref<string | null>(null)
const restoreNotice = ref<string | null>(null)
const draftStorageError = ref<string | null>(null)

const activeKey = ref<string | null>(null)
const mode = ref<SelectionMode>('search')
const searchQuery = ref('')
const searchState = ref<'idle' | 'loading' | 'ready' | 'empty' | 'invalid' | 'unsupported' | 'error'>('idle')
const searchError = ref('')
const searchMode = ref<'ranked' | 'exact'>('ranked')
const searchResults = ref<SelectionRecord[]>([])
const selectedRecord = ref<SelectionRecord | null>(null)

const browseState = ref<'idle' | 'loading' | 'ready' | 'too-large' | 'unsupported' | 'error'>('idle')
const browseError = ref('')
const browseItems = ref<SelectionRecord[]>([])
const browseText = ref('')
const browseFieldFilters = reactive<Record<string, string>>({})
const sortField = ref('name')
const sortDirection = ref<'asc' | 'desc'>('asc')

const saving = ref(false)
const saveError = ref<string | null>(null)
const saveIssues = ref<DecisionBatchIssue[]>([])
const saveSummary = ref<string | null>(null)
const conflict = ref<{ keys: string[]; current: Record<string, DecisionState> } | null>(null)

const rowsByKey = ref<Record<string, WorkspaceRowDraft>>({})
const loadedStates = ref<Record<string, DecisionState>>({})

let searchSequence = 0
let browseSequence = 0
let searchTimer: ReturnType<typeof setTimeout> | null = null

const TYPEAHEAD_DEBOUNCE_MS = 300

/** Build the row drafts a restored workspace starts from. */
function emptyDraft(): WorkspaceRowDraft {
  return { query: '', notes: '', decision: null, displayedValues: {} }
}

const activeDraft = computed<WorkspaceRowDraft>(() => {
  const key = activeKey.value
  if (!key) return emptyDraft()
  return rowsByKey.value[key] ?? emptyDraft()
})

// ---------- Queue and row state ----------

function updateActiveDraft(change: Partial<WorkspaceRowDraft>) {
  const key = activeKey.value
  if (!key) return
  rowsByKey.value = { ...rowsByKey.value, [key]: { ...(rowsByKey.value[key] ?? emptyDraft()), ...change } }
  persistDraft()
}

function rowErrors(row: ReconciliationPreviewRow): string[] {
  return Array.isArray(row.errors) ? row.errors.filter((message): message is string => typeof message === 'string') : []
}

function rowLabel(row: ReconciliationPreviewRow): string {
  const value = row[props.targetField]
  return value === null || value === undefined ? '' : String(value)
}

const activeRowErrors = computed(() => (activeEntry.value ? rowErrors(activeEntry.value.row) : []))

const queueRows = computed<QueueEntry[]>(() => {
  return props.previewRows
    .map((row, index) => {
      const key = typeof row.local_key_value === 'string' && row.local_key_value ? row.local_key_value : null
      const errors = rowErrors(row)
      const status = typeof row.status === 'string' ? row.status : null
      return {
        key,
        index,
        label: rowLabel(row),
        unreviewable: key === null || errors.length > 0,
        reason: key === null ? 'No business key' : errors.length ? (errors[0] ?? 'Row has errors') : null,
        savedStatus: status && status !== 'proposed' ? status : null,
      }
    })
    .filter((entry) => {
      if (entry.unreviewable) return true
      if (!entry.savedStatus) return true
      const draft = entry.key ? rowsByKey.value[entry.key] : undefined
      return Boolean(draft?.decision)
    })
})

interface ActiveEntry extends QueueEntry {
  row: ReconciliationPreviewRow
}

const activeEntry = computed<ActiveEntry | null>(() => {
  const key = activeKey.value
  if (!key) return null
  const entry = queueRows.value.find((candidate) => candidate.key === key)
  const row = props.previewRows[entry?.index ?? -1]
  if (!entry || !row) return null
  return { ...entry, row }
})

const reviewableQueue = computed(() => queueRows.value.filter((entry) => !entry.unreviewable && entry.key !== null))

const activeQueueIndex = computed(() => reviewableQueue.value.findIndex((entry) => entry.key === activeKey.value))
const canGoPrevious = computed(() => activeQueueIndex.value > 0)
const canGoNext = computed(
  () => activeQueueIndex.value >= 0 && activeQueueIndex.value < reviewableQueue.value.length - 1
)

const unsavedCount = computed(() => Object.values(rowsByKey.value).filter((draft) => draft.decision !== null).length)

const stagedKeys = computed(() =>
  Object.entries(rowsByKey.value)
    .filter(([, draft]) => draft.decision !== null)
    .map(([key]) => key)
)

function hasDraft(key: string | null): boolean {
  return Boolean(key && rowsByKey.value[key]?.decision)
}

function focusRow(entry: QueueEntry) {
  if (entry.unreviewable || !entry.key) return
  if (entry.key !== activeKey.value) {
    activeKey.value = entry.key
    invalidateSelection()
  }
  persistDraft()
  void nextTick(() => {
    if (activeKey.value !== entry.key) return
    workspaceRoot.value?.querySelector<HTMLElement>(`[data-testid="workspace-row-${entry.index}"]`)?.focus()
  })
}

function nextRow() {
  const next = reviewableQueue.value[activeQueueIndex.value + 1]
  if (next?.key) focusRow(next)
}

function previousRow() {
  const previous = reviewableQueue.value[activeQueueIndex.value - 1]
  if (previous?.key) focusRow(previous)
}

/** Advance without staging anything; any draft already staged for this row stays. */
function skipRow() {
  nextRow()
}

function displayedValuesFor(row: ReconciliationPreviewRow): Record<string, unknown> {
  const values: Record<string, unknown> = {}
  for (const [column, value] of Object.entries(row)) {
    if (STATUS_FIELDS.has(column)) continue
    if (value === null || ['string', 'number', 'boolean'].includes(typeof value)) {
      values[column] = value
    }
  }
  return values
}

function stageSelected() {
  const entry = activeEntry.value
  if (!entry || entry.unreviewable) return
  const record = selectedRecord.value
  if (!record || record.target_id === null) return
  updateActiveDraft({
    decision: { status: 'accepted', id: record.id, target_id: record.target_id, name: record.name },
    displayedValues: displayedValuesFor(entry.row),
  })
  nextRow()
}

function stageNew() {
  const entry = activeEntry.value
  if (!entry || entry.unreviewable) return
  updateActiveDraft({ decision: { status: 'local-only' }, displayedValues: displayedValuesFor(entry.row) })
  nextRow()
}

function clearDraft() {
  updateActiveDraft({ decision: null })
}

// ---------- Draft persistence ----------

function currentDraft(): WorkspaceDraft {
  return {
    focusedKey: activeKey.value,
    mode: mode.value,
    searchQuery: searchQuery.value,
    browseText: browseText.value,
    browseFieldFilters: { ...browseFieldFilters },
    sortField: sortField.value,
    sortDirection: sortDirection.value,
    rows: JSON.parse(JSON.stringify(rowsByKey.value)) as Record<string, WorkspaceRowDraft>,
  }
}

function persistDraft() {
  const stored = reconciliationStore.saveWorkspaceDraft(
    props.projectName,
    props.entityName,
    props.targetField,
    currentDraft()
  )
  draftStorageError.value = stored
    ? null
    : 'This browser could not store the draft, so the staged decisions are not durable. Save them before reloading or leaving this page.'
}

function restoreDraft() {
  const { status, draft } = reconciliationStore.loadWorkspaceDraft(
    props.projectName,
    props.entityName,
    props.targetField
  )

  if (status === 'invalid') {
    restoreNotice.value =
      'The stored draft for this specification could not be read and was cleared. Nothing was reused from another specification.'
    return
  }
  if (!draft) return

  mode.value = draft.mode
  searchQuery.value = draft.searchQuery
  browseText.value = draft.browseText
  for (const [field, value] of Object.entries(draft.browseFieldFilters)) browseFieldFilters[field] = value
  sortField.value = draft.sortField
  sortDirection.value = draft.sortDirection

  const presentKeys = new Set(
    props.previewRows.map((row) => row.local_key_value).filter((key): key is string => typeof key === 'string')
  )
  const restored: Record<string, WorkspaceRowDraft> = {}
  for (const [key, row] of Object.entries(draft.rows)) {
    if (presentKeys.has(key)) restored[key] = row
  }
  rowsByKey.value = restored

  const restoredCount = Object.values(restored).filter((row) => row.decision !== null).length
  if (restoredCount > 0) {
    restoreNotice.value = `Restored ${restoredCount} unsaved ${restoredCount === 1 ? 'decision' : 'decisions'}. No target selection or result list was restored.`
  }

  if (draft.focusedKey && reviewableQueue.value.some((entry) => entry.key === draft.focusedKey)) {
    activeKey.value = draft.focusedKey
  }
}

// ---------- Capabilities ----------

function selectionErrorCode(error: unknown): string | null {
  if (typeof error !== 'object' || error === null || !('response' in error)) return null
  const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
  if (typeof detail === 'object' && detail !== null && 'error_code' in detail) {
    const code = (detail as { error_code?: unknown }).error_code
    return typeof code === 'string' ? code : null
  }
  return null
}

function selectionErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
    if (typeof detail === 'string') return detail
    if (typeof detail === 'object' && detail !== null && 'message' in detail) {
      const message = (detail as { message?: unknown }).message
      if (typeof message === 'string') return message
    }
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}

async function loadCapabilities() {
  if (!props.selectionDescriptor) {
    capabilityState.value = 'fallback'
    fallbackMessage.value =
      'The reconciliation service does not advertise record selection, so Search and Browse are not available for this specification.'
    return
  }

  capabilityState.value = 'loading'
  try {
    capabilities.value = await reconciliationStore.loadSelectionCapabilities(
      props.projectName,
      props.entityName,
      props.targetField
    )
    capabilityState.value = 'ready'
    const flags = capabilities.value.type
    if (
      mode.value === 'search' &&
      !flags.search_supported &&
      !flags.identifier_search_supported &&
      flags.browse_supported
    ) {
      mode.value = 'browse'
    }
    if (mode.value === 'browse') await loadBrowse()
  } catch (error) {
    capabilityState.value = 'fallback'
    fallbackMessage.value = selectionErrorMessage(
      error,
      'Record selection could not be started because the reconciliation service did not answer.'
    )
  }
}

// ---------- Ranked search and exact lookup ----------

function invalidateSelection() {
  searchSequence += 1
  browseSequence += 1
  selectedRecord.value = null
}

function onQueryChange() {
  invalidateSelection()
  searchResults.value = []
  searchState.value = 'idle'
  if (composing.value) return
  scheduleSearch()
  persistDraft()
}

function scheduleSearch() {
  if (searchTimer !== null) clearTimeout(searchTimer)
  const sequence = searchSequence
  searchTimer = setTimeout(() => {
    searchTimer = null
    if (sequence === searchSequence) void runSearch()
  }, TYPEAHEAD_DEBOUNCE_MS)
}

function submitSearch() {
  if (searchTimer !== null) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
  void runSearch()
}

function handleSearchKeydown(event: KeyboardEvent) {
  if (event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) return
  event.preventDefault()
  submitSearch()
}

async function runSearch() {
  const key = activeKey.value
  const query = searchQuery.value.trim()
  const caps = capabilities.value
  if (!caps || !key || !query) return

  const sequence = (searchSequence += 1)
  selectedRecord.value = null
  searchError.value = ''
  searchState.value = 'loading'

  try {
    const result = await reconciliationStore.searchSelection(props.projectName, props.entityName, props.targetField, {
      query,
      limit: caps.type.interactive_search_max_results ?? undefined,
    })
    if (sequence !== searchSequence) return
    searchMode.value = result.mode
    searchResults.value = result.items
    searchState.value = result.items.length ? 'ready' : 'empty'
  } catch (error) {
    if (sequence !== searchSequence) return
    const code = selectionErrorCode(error)
    const message = selectionErrorMessage(error, 'The search request failed.')
    if (code === 'RECORD_SELECTION_INVALID_INPUT') {
      searchState.value = 'invalid'
    } else if (code === 'RECORD_SELECTION_UNSUPPORTED') {
      searchState.value = 'unsupported'
    } else {
      searchState.value = 'error'
    }
    searchError.value = message
    searchResults.value = []
  }
}

function selectRecord(record: SelectionRecord) {
  selectedRecord.value = record
}

// ---------- Complete-list browse ----------

function browseField(record: SelectionRecord, field: string): unknown {
  if (field === 'name') return record.name
  if (field === 'target_id') return record.target_id
  if (field === 'description') return record.description ?? null
  return record.fields?.[field] ?? null
}

const browseTextFields = computed(() => capabilities.value?.type.text_filter_fields ?? [])
const browseFieldFilterDeclarations = computed(() => capabilities.value?.type.field_filters ?? [])

const filteredBrowseItems = computed(() => {
  const needle = browseText.value.trim().toLowerCase()
  return browseItems.value.filter((record) => {
    if (needle) {
      const matchesText = browseTextFields.value.some((field) =>
        String(browseField(record, field) ?? '')
          .toLowerCase()
          .includes(needle)
      )
      if (!matchesText) return false
    }
    return browseFieldFilterDeclarations.value.every((filter) => {
      const expected = (browseFieldFilters[filter.field] ?? '').trim()
      if (!expected) return true
      const actual = browseField(record, filter.field)
      if (filter.operator === 'contains_ci') {
        return String(actual ?? '')
          .toLowerCase()
          .includes(expected.toLowerCase())
      }
      if (actual === null || actual === undefined) return false
      return String(actual).toLowerCase() === expected.toLowerCase()
    })
  })
})

function compareIds(left: SelectionRecord, right: SelectionRecord): number {
  return (left.target_id ?? 0) - (right.target_id ?? 0)
}

const sortedBrowseItems = computed(() => {
  const items = [...filteredBrowseItems.value]
  const field = sortField.value
  const direction = sortDirection.value === 'asc' ? 1 : -1
  return items.sort((left, right) => {
    const leftValue = browseField(left, field)
    const rightValue = browseField(right, field)
    const leftMissing = leftValue === null || leftValue === undefined
    const rightMissing = rightValue === null || rightValue === undefined
    if (leftMissing && rightMissing) return compareIds(left, right)
    if (leftMissing) return 1
    if (rightMissing) return -1
    if (typeof leftValue === 'number' && typeof rightValue === 'number') {
      if (leftValue !== rightValue) return (leftValue - rightValue) * direction
      return compareIds(left, right)
    }
    const sorted = String(leftValue).localeCompare(String(rightValue), 'en', { sensitivity: 'base' })
    if (sorted !== 0) return sorted * direction
    return compareIds(left, right)
  })
})

const visibleBrowseItems = computed(() => sortedBrowseItems.value)

watch(visibleBrowseItems, (items) => {
  const current = selectedRecord.value
  if (mode.value === 'browse' && current && !items.some((record) => record.id === current.id)) {
    selectedRecord.value = null
  }
})

function onBrowseFilterChange() {
  persistDraft()
}

async function loadBrowse() {
  const caps = capabilities.value
  if (!caps) return
  if (!caps.type.browse_supported) {
    browseState.value = 'unsupported'
    browseError.value = 'Browse is not enabled for this target type, so the complete list is unavailable.'
    return
  }

  const sequence = (browseSequence += 1)
  browseState.value = 'loading'
  browseError.value = ''
  try {
    const result = await reconciliationStore.browseSelection(props.projectName, props.entityName, props.targetField)
    if (sequence !== browseSequence) return
    browseItems.value = result.items
    browseState.value = 'ready'
  } catch (error) {
    if (sequence !== browseSequence) return
    const code = selectionErrorCode(error)
    browseItems.value = []
    if (code === 'RECORD_SELECTION_TOO_LARGE') {
      browseState.value = 'too-large'
      browseError.value = selectionErrorMessage(error, 'The complete list is too large to browse.')
    } else if (code === 'RECORD_SELECTION_UNSUPPORTED') {
      browseState.value = 'unsupported'
      browseError.value = selectionErrorMessage(error, 'Browse is not enabled for this target type.')
    } else {
      browseState.value = 'error'
      browseError.value = selectionErrorMessage(error, 'The complete list could not be loaded.')
    }
  }
}

function onModeChange(value: SelectionMode) {
  const current = selectedRecord.value
  mode.value = value
  invalidateSelection()

  // Keep a selection only when the same record exists in the mode now shown.
  if (current) {
    const source = value === 'browse' ? visibleBrowseItems.value : searchResults.value
    if (source.some((record) => record.id === current.id)) selectedRecord.value = current
  }

  if (value === 'browse' && browseState.value === 'idle') void loadBrowse()
  persistDraft()
}

// ---------- Batch save with an advisory stale-view comparison ----------

const conflictChanges = computed(() => {
  if (!conflict.value) return []
  return conflict.value.keys.map((key) => ({
    key,
    loaded: loadedStates.value[key] ?? null,
    current: conflict.value?.current[key] ?? null,
  }))
})

function buildDrafts(): DecisionDraftRequest[] {
  const drafts: DecisionDraftRequest[] = []
  for (const [key, draft] of Object.entries(rowsByKey.value)) {
    if (!draft.decision) continue
    const notes = draft.notes.trim()
    if (draft.decision.status === 'accepted') {
      drafts.push({
        local_key_value: key,
        displayed_values: draft.displayedValues,
        status: 'accepted',
        target_id: draft.decision.target_id,
        candidate_id: draft.decision.id,
        notes: notes || null,
      })
    } else {
      drafts.push({
        local_key_value: key,
        displayed_values: draft.displayedValues,
        status: 'local-only',
        target_id: null,
        candidate_id: null,
        notes: notes || null,
      })
    }
  }
  return drafts
}

async function saveDecisions() {
  if (saving.value || stagedKeys.value.length === 0) return
  saveError.value = null
  saveIssues.value = []
  saveSummary.value = null

  saving.value = true
  try {
    const current = await reconciliationStore.fetchSavedDecisionStates(
      props.projectName,
      props.entityName,
      props.targetField
    )
    const changed = reconciliationStore.changedDecisionKeys(loadedStates.value, current, stagedKeys.value)
    if (changed.length > 0) {
      conflict.value = { keys: changed, current }
      return
    }
  } catch (error) {
    saveError.value =
      `Saved decisions could not be compared before saving, so nothing was saved: ` +
      selectionErrorMessage(error, 'the catalog could not be read')
    return
  } finally {
    saving.value = false
  }

  await submitBatch()
}

async function submitBatch() {
  const drafts = buildDrafts()
  if (saving.value) return
  if (drafts.length === 0) {
    conflict.value = null
    return
  }

  saving.value = true
  try {
    const result = await reconciliationStore.saveDecisionBatch(
      props.projectName,
      props.entityName,
      props.targetField,
      drafts
    )
    applySavedResult(result)
    conflict.value = null
  } catch (error) {
    saveError.value = selectionErrorMessage(error, 'The decision batch was not saved.')
    saveIssues.value = reconciliationStore.getDecisionBatchIssues(error)
    // Every draft stays staged so the reviewer can correct the reported rows.
  } finally {
    saving.value = false
  }
}

function applySavedResult(result: DecisionBatchResult) {
  const savedKeys = new Set(result.saved.map((saved) => saved.local_key_value))
  const nextRows = { ...rowsByKey.value }
  for (const key of savedKeys) {
    const draft = nextRows[key]
    if (draft) nextRows[key] = { ...draft, decision: null }
  }
  rowsByKey.value = nextRows

  const baseline = { ...loadedStates.value }
  for (const saved of result.saved) {
    baseline[saved.local_key_value] = {
      status: saved.status,
      target_id: saved.target_id ?? null,
      candidate_id: saved.candidate_id ?? null,
      notes: saved.notes ?? null,
    }
  }
  loadedStates.value = baseline

  saveSummary.value =
    `Saved ${result.counts.saved} ${result.counts.saved === 1 ? 'decision' : 'decisions'}: ` +
    `${result.counts.accepted} accepted and ${result.counts.local_only} New. ` +
    `${result.counts.specification.total} decisions are stored for this specification.`

  persistDraft()

  const remaining = queueRows.value.find((entry) => !entry.unreviewable && entry.key && !savedKeys.has(entry.key))
  if (remaining?.key) {
    activeKey.value = remaining.key
  } else if (activeKey.value && savedKeys.has(activeKey.value)) {
    activeKey.value = null
  }

  emit('saved', result)
}

function cancelConflict() {
  conflict.value = null
}

async function confirmConflict() {
  await submitBatch()
}

// ---------- Keyboard and lifecycle ----------

function handleKeydown(event: KeyboardEvent) {
  if (event.isComposing || composing.value) return
  if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return

  const actions: Record<string, () => void> = {
    ArrowRight: nextRow,
    ArrowLeft: previousRow,
    ArrowDown: skipRow,
    Enter: stageSelected,
    Backspace: stageNew,
  }
  const action = actions[event.key]
  if (!action) return
  event.preventDefault()
  action()
}

onMounted(async () => {
  loadedStates.value = reconciliationStore.decisionStatesFromPreview(props.previewRows)
  restoreDraft()
  await loadCapabilities()
})

watch(
  () => [props.projectName, props.entityName, props.targetField],
  () => {
    // A different specification is a different scope: drop in-memory state and reload.
    rowsByKey.value = {}
    loadedStates.value = reconciliationStore.decisionStatesFromPreview(props.previewRows)
    activeKey.value = null
    invalidateSelection()
    searchResults.value = []
    searchState.value = 'idle'
    browseItems.value = []
    browseState.value = 'idle'
    void loadCapabilities()
  }
)
</script>

<style scoped>
.workspace-layout {
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.workspace-queue-list {
  max-height: 520px;
  overflow-y: auto;
}

@media (max-width: 960px) {
  .workspace-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
