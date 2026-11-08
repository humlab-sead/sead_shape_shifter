<template>
  <div class="integrity-troubleshooter-body">
    <div v-if="loading && !result" class="mb-4 integrity-loading">
      <v-progress-linear indeterminate color="primary" class="mb-1" />
      <p class="text-caption text-medium-emphasis mb-0">
        Reading the link from current data. The link is re-run when this dialog opens; later pages use the same
        inspection snapshot.
      </p>
    </div>
    <div v-else-if="loading" class="mb-2 integrity-page-loading" aria-label="Loading inspection page">
      <v-progress-linear indeterminate color="primary" />
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      <div>{{ error.message }}</div>
      <ul v-if="error.tips?.length" class="mt-2">
        <li v-for="tip in error.tips" :key="tip">{{ tip }}</li>
      </ul>
    </v-alert>

    <template v-if="result">
      <!-- A reproduced warning is the expected outcome, so only a failed reproduction
      is reported. The current values below already show what was found. -->
      <v-alert
        v-if="result.status !== 'reproduced'"
        type="warning"
        variant="tonal"
        class="mb-4 integrity-status"
        :title="formatCodeLabel(result.status)"
      >
        <div class="text-caption mb-1">Reason: {{ formatCodeLabel(result.reason) }}</div>
        <div>{{ result.message }}</div>
      </v-alert>

      <section class="integrity-finding-summary mb-4" aria-label="Integrity finding summary">
        <div class="d-flex flex-wrap align-center justify-space-between ga-2 mb-3">
          <div class="d-flex align-center ga-1">
            <h2 class="text-subtitle-1 mb-0">Integrity results</h2>
            <v-tooltip location="top" max-width="360">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon
                  size="x-small"
                  variant="text"
                  class="text-medium-emphasis"
                  aria-label="About integrity counts"
                >
                  <v-icon icon="mdi-help-circle-outline" size="small" />
                </v-btn>
              </template>
              <div class="text-body-2">
                <p class="mb-1">The recorded count comes from the validation warning.</p>
                <p class="mb-0">
                  The current count is recalculated from current data. The list below shows the unmatched key values and
                  how many local rows use each one.
                </p>
              </div>
            </v-tooltip>
          </div>
          <v-btn v-if="result.values" size="small" variant="outlined" @click="focusUnmatchedValues">
            Inspect unmatched values
          </v-btn>
        </div>
        <div class="integrity-finding-stats">
          <div class="integrity-finding-stat" data-stat="recorded">
            <div class="integrity-finding-stat-value">{{ formatCount(result.recorded_orphan_count) }}</div>
            <div class="text-body-2 text-medium-emphasis">Recorded unmatched values</div>
          </div>
          <div class="integrity-finding-stat" data-stat="current">
            <div class="integrity-finding-stat-value">{{ formatCount(result.current_orphan_count) }}</div>
            <div class="text-body-2 text-medium-emphasis">Current unmatched values</div>
          </div>
        </div>
      </section>

      <div class="integrity-troubleshooter-workspace">
        <aside class="integrity-link-details" aria-label="Configured link details">
          <section v-if="result.configured_keys" class="mb-5" aria-label="Configured keys">
            <h3 class="text-subtitle-1 mb-2">Configured key pairs</h3>
            <div class="integrity-key-headings" aria-hidden="true">
              <span>{{ result.relationship?.local_entity || 'Local entity' }}</span>
              <span>{{ result.relationship?.remote_entity || 'Remote entity' }}</span>
            </div>
            <v-table density="compact">
              <tbody>
                <tr v-for="(pair, index) in configuredKeyPairs" :key="`key-pair-${index}`">
                  <td>{{ pair.local }}</td>
                  <td>{{ pair.remote }}</td>
                </tr>
              </tbody>
            </v-table>
          </section>
        </aside>

        <div class="integrity-results">
          <section v-if="result.values" class="mb-5" aria-label="Unmatched values">
            <h3 ref="unmatchedValuesRef" class="text-subtitle-1 mb-2">Unmatched values</h3>
            <div class="text-caption text-medium-emphasis mb-3">
              Showing {{ formatCount(result.values.returned_value_count) }} of
              {{ formatCount(result.values.distinct_value_count) }} distinct values · Page {{ result.values.page }}
            </div>

            <template v-if="result.values.values.length > 0">
              <p class="text-body-2 text-medium-emphasis mb-2">Select a value to list its affected local rows.</p>
              <TroubleshooterDataGrid
                :columns="valueColumns"
                :rows="valueRows"
                :loading="loading"
                selectable
                height="320px"
                @row-click="selectValueRow"
              />
            </template>
            <p v-else class="text-body-2 text-medium-emphasis">No unmatched values on this page.</p>

            <div v-if="valuePageCount > 1" class="d-flex justify-end mt-2">
              <v-pagination
                :model-value="result.values.page"
                :length="valuePageCount"
                density="comfortable"
                @update:model-value="changePage"
              />
            </div>
          </section>

          <section v-if="result.selected" class="mb-2" aria-label="Selected value rows">
            <template v-if="result.selected.status === 'selected'">
              <h3 class="text-subtitle-1 mb-1">Affected local rows</h3>
              <div class="text-body-2">Unmatched key: {{ formatKey(result.selected.key_values ?? []) }}</div>
              <div class="text-body-2 mb-2">
                Showing {{ formatCount(result.selected.returned_row_count) }} of
                {{ formatCount(result.selected.total_row_count) }} local rows for this key.
              </div>
              <v-alert
                v-if="result.selected.browse_cap_reached"
                type="info"
                variant="tonal"
                density="compact"
                class="mb-2"
              >
                Only the first {{ formatCount(result.selected.browse_cap) }} local rows for this key are browsable.
              </v-alert>
              <v-alert
                v-if="result.selected.columns_truncated"
                type="info"
                variant="tonal"
                density="compact"
                class="mb-2"
              >
                Only the first {{ result.selected.columns.length }} columns are shown.
              </v-alert>
              <TroubleshooterDataGrid
                :columns="selectedColumns"
                :rows="result.selected.rows"
                :loading="loading"
                height="320px"
              />
              <div v-if="selectedRowPageCount > 1" class="d-flex justify-end mt-2">
                <v-btn
                  size="small"
                  variant="text"
                  aria-label="Previous rows page"
                  :disabled="rowOffset <= 0 || loading"
                  @click="changeRowPage(-1)"
                >
                  Previous
                </v-btn>
                <v-btn
                  size="small"
                  variant="text"
                  aria-label="Next rows page"
                  :disabled="selectedRowPage >= selectedRowPageCount || loading"
                  @click="changeRowPage(1)"
                >
                  Next
                </v-btn>
              </div>
            </template>

            <v-alert v-else type="warning" variant="tonal" density="compact" class="integrity-selection-unavailable">
              <div v-if="result.selected.reason" class="text-caption mb-1">Reason: {{ result.selected.reason }}</div>
              <div>{{ result.selected.message }}</div>
            </v-alert>
          </section>
        </div>
      </div>

      <details class="integrity-details mt-4" aria-label="Technical details">
        <summary>Technical details</summary>
        <p class="text-body-2 mt-2">{{ message.message }}</p>
        <p class="text-caption text-medium-emphasis mb-0">
          {{ result.status }} · {{ result.reason }} · {{ result.source }}
        </p>
      </details>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { integrityTroubleshooterApi } from '@/api/integrityTroubleshooter'
import type {
  FormattedError,
  IntegrityTroubleshootRequest,
  IntegrityTroubleshootRelationship,
  IntegrityTroubleshootResponse,
  ValidationError,
} from '@/types'
import { formatErrorMessage } from '@/utils/errors'
import { toIntegrityTroubleshootRequest } from '@/utils/linkTroubleshooter'
import TroubleshooterDataGrid, { type TroubleshooterGridColumn } from './TroubleshooterDataGrid.vue'

/** Default number of local rows requested for one selected unmatched value. */
const ROW_PAGE_SIZE = 100

interface Props {
  projectName: string
  message: ValidationError
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (event: 'relationship', value: IntegrityTroubleshootRelationship | null): void
}>()

const loading = ref(false)
const error = ref<FormattedError | null>(null)
const result = ref<IntegrityTroubleshootResponse | null>(null)
const contextId = ref<string | null>(null)
const page = ref(1)
const selectedToken = ref<string | null>(null)
const rowOffset = ref(0)
const rowLimit = ref(ROW_PAGE_SIZE)
const unmatchedValuesRef = ref<HTMLElement | null>(null)
let requestVersion = 0

const configuredKeyPairs = computed(() => {
  const localKeys = result.value?.configured_keys?.local_keys ?? []
  const remoteKeys = result.value?.configured_keys?.remote_keys ?? []
  const pairCount = Math.max(localKeys.length, remoteKeys.length)

  return Array.from({ length: pairCount }, (_, index) => ({
    local: localKeys[index] ?? '—',
    remote: remoteKeys[index] ?? '—',
  }))
})

const valuePageCount = computed(() => {
  const values = result.value?.values
  if (!values || values.page_size <= 0) {
    return 1
  }

  return Math.max(1, Math.ceil(values.distinct_value_count / values.page_size))
})

const selectedRowPage = computed(() => Math.floor(rowOffset.value / rowLimit.value) + 1)

const selectedRowPageCount = computed(() => {
  const selected = result.value?.selected
  const totalRows = selected?.total_row_count ?? 0
  const browseCap = selected?.browse_cap ?? totalRows
  if (rowLimit.value <= 0) {
    return 1
  }

  return Math.max(1, Math.ceil(Math.min(totalRows, browseCap) / rowLimit.value))
})

// Columns are read-only: the backend pages the complete value set in a fixed
// order, so sorting or filtering one page would only reorder what is loaded.
const valueColumns = computed<TroubleshooterGridColumn[]>(() => [
  { field: 'unmatchedKey', header: 'Unmatched key' },
  { field: 'localRowCount', header: 'Local rows', align: 'right' as const, width: 140 },
])

const valueRows = computed<Record<string, unknown>[]>(() =>
  (result.value?.values?.values ?? []).map((value) => ({
    token: value.token,
    unmatchedKey: formatKey(value.key_values),
    localRowCount: value.local_row_count,
  }))
)

const selectedColumns = computed<TroubleshooterGridColumn[]>(() =>
  (result.value?.selected?.columns ?? []).map((column) => ({ field: column, header: column }))
)

watch(
  () => [props.projectName, props.message] as const,
  () => {
    closeContext(contextId.value)
    contextId.value = null
    result.value = null
    page.value = 1
    selectedToken.value = null
    rowOffset.value = 0
    void sendRequest()
  },
  { immediate: true }
)

// Closing the dialog unmounts this body; a late response must not be applied.
onBeforeUnmount(() => {
  requestVersion += 1
  closeContext(contextId.value)
  contextId.value = null
})

// Grid rows carry the token, so selecting a value does not depend on its
// position in the page.
function selectValueRow(row: Record<string, unknown>): void {
  const token = typeof row.token === 'string' ? row.token : null
  if (token === null) {
    return
  }
  selectedToken.value = token
  rowOffset.value = 0
  void sendRequest()
}

function changePage(value: number): void {
  page.value = value
  selectedToken.value = null
  rowOffset.value = 0
  void sendRequest()
}

function changeRowPage(direction: -1 | 1): void {
  const nextOffset = rowOffset.value + direction * rowLimit.value
  if (nextOffset < 0) {
    return
  }
  rowOffset.value = nextOffset
  void sendRequest()
}

function focusUnmatchedValues(): void {
  unmatchedValuesRef.value?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
}

async function sendRequest(): Promise<void> {
  const identity: IntegrityTroubleshootRequest | null = toIntegrityTroubleshootRequest(props.message)
  if (!identity) {
    requestVersion += 1
    closeContext(contextId.value)
    contextId.value = null
    result.value = null
    error.value = null
    return
  }

  const request: IntegrityTroubleshootRequest = {
    ...identity,
    page: page.value,
    row_offset: rowOffset.value,
    row_limit: rowLimit.value,
    ...(selectedToken.value === null ? {} : { selected_value_token: selectedToken.value }),
  }

  const pageRequest = {
    page: page.value,
    row_offset: rowOffset.value,
    row_limit: rowLimit.value,
    ...(selectedToken.value === null ? {} : { selected_value_token: selectedToken.value }),
  }
  const currentContextId: string | null = contextId.value
  const version = ++requestVersion
  loading.value = true
  error.value = null
  if (currentContextId === null) {
    result.value = null
  }

  try {
    const response =
      currentContextId === null
        ? await integrityTroubleshooterApi.inspect(props.projectName, request)
        : await integrityTroubleshooterApi.page(props.projectName, currentContextId, pageRequest)
    if (version !== requestVersion) {
      if (currentContextId === null) {
        closeContext(response.context_id)
      }
      return
    }

    result.value = response
    contextId.value = response.context_id
    emit('relationship', response.relationship)
  } catch (caughtError: unknown) {
    if (version !== requestVersion) {
      return
    }

    if (currentContextId !== null && isContextExpired(caughtError)) {
      contextId.value = null
      await sendRequest()
      return
    }

    error.value = formatErrorMessage(caughtError)
    if (currentContextId === null) {
      result.value = null
    }
    console.error('Integrity troubleshooter request failed:', caughtError)
  } finally {
    if (version === requestVersion) {
      loading.value = false
    }
  }
}

function closeContext(value: string | null): void {
  if (value === null) {
    return
  }

  void integrityTroubleshooterApi.close(props.projectName, value).catch((caughtError: unknown) => {
    console.error('Integrity troubleshooter context cleanup failed:', caughtError)
  })
}

function isContextExpired(caughtError: unknown): boolean {
  const response = (caughtError as { response?: { status?: number; data?: unknown } } | null)?.response
  if (!response || response.status !== 410) {
    return false
  }

  const detail = (response.data as { detail?: { error_type?: unknown; reason?: unknown } } | null)?.detail
  return detail?.reason === 'context_expired' || detail?.error_type === 'IntegrityTroubleshooterContextExpired'
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '—'
  }
  if (typeof value === 'string') {
    return value
  }

  return typeof value === 'object' ? (JSON.stringify(value) ?? String(value)) : String(value)
}

function formatKey(values: unknown[]): string {
  return values.length === 0 ? '—' : values.map(formatValue).join(', ')
}

function formatCount(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

function formatCodeLabel(value: string): string {
  const label = value.replace(/_/g, ' ')
  return label.charAt(0).toUpperCase() + label.slice(1)
}
</script>

<style scoped>
.integrity-finding-summary {
  padding: 1rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 0.5rem;
  background: rgba(var(--v-theme-primary), 0.04);
}

.integrity-finding-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.integrity-finding-stat {
  min-width: 0;
  padding: 0.75rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 0.5rem;
}

.integrity-finding-stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.2;
}

.integrity-troubleshooter-workspace {
  display: grid;
  grid-template-columns: minmax(240px, 0.8fr) minmax(0, 1.6fr);
  gap: 1.5rem;
  align-items: start;
}

.integrity-link-details,
.integrity-results {
  min-width: 0;
}

.integrity-key-headings {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0.75rem;
  margin-bottom: 0.25rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.75rem;
  font-weight: 500;
}

.integrity-details {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  padding-top: 0.75rem;
}

.integrity-details > summary {
  cursor: pointer;
  font-weight: 500;
}

@media (max-width: 900px) {
  .integrity-troubleshooter-workspace {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 600px) {
  .integrity-finding-stats {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
