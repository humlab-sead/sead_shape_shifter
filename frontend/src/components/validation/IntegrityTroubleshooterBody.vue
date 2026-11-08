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

      <div class="integrity-troubleshooter-workspace">
        <aside class="integrity-link-details" aria-label="Configured link details">
          <section v-if="result.configured_keys" aria-label="Configured keys">
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
          <section class="integrity-finding-summary mb-4" aria-label="Integrity finding summary">
            <div class="d-flex align-center ga-1 mb-3">
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
                    The current count is recalculated from current data. The list below shows every unmatched key value
                    and how many local rows use each one.
                  </p>
                </div>
              </v-tooltip>
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

          <section v-if="result.values" class="mb-5" aria-label="Unmatched values">
            <div class="d-flex flex-wrap align-center justify-space-between ga-2 mb-2">
              <h3 class="text-subtitle-1 mb-0">Unmatched values</h3>
              <v-btn
                v-if="result.values.values.length > 0"
                size="small"
                variant="text"
                prepend-icon="mdi-download"
                :disabled="loading"
                @click="exportUnmatchedValues"
              >
                Export unmatched keys
              </v-btn>
            </div>
            <div class="text-caption text-medium-emphasis mb-3">
              {{ formatCount(result.values.values.length) }} unmatched
              {{ result.values.values.length === 1 ? 'value' : 'values' }}
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
            <p v-else class="text-body-2 text-medium-emphasis">No unmatched values in the current data.</p>
          </section>

          <section v-if="result.selected" class="mb-2" aria-label="Selected value rows">
            <template v-if="result.selected.status === 'selected'">
              <h3 class="text-subtitle-1 mb-1">Affected local rows</h3>
              <div class="text-body-2">Unmatched key: {{ formatKey(result.selected.key_values ?? []) }}</div>
              <div class="text-body-2 mb-2">
                {{ formatCount(result.selected.total_row_count) }} local rows use this key.
              </div>
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
  IntegrityTroubleshootPageRequest,
  IntegrityTroubleshootRequest,
  IntegrityTroubleshootRelationship,
  IntegrityTroubleshootResponse,
  ValidationError,
} from '@/types'
import { formatErrorMessage } from '@/utils/errors'
import { downloadCsv, toCsv } from '@/utils/csv'
import { toIntegrityTroubleshootRequest } from '@/utils/linkTroubleshooter'
import TroubleshooterDataGrid, { type TroubleshooterGridColumn } from './TroubleshooterDataGrid.vue'

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
const selectedToken = ref<string | null>(null)
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

// Columns are read-only: the backend returns the complete value set in a fixed
// order, so sorting or filtering would only reorder what is loaded.
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

// One CSV column per key part, so a composite key stays addressable instead of
// being flattened into one joined cell. Configured local key names label the
// columns; a wider key falls back to a positional name.
const unmatchedKeyColumns = computed<string[]>(() => {
  const configuredKeys = result.value?.configured_keys?.local_keys ?? []
  const width = (result.value?.values?.values ?? []).reduce(
    (widest, value) => Math.max(widest, value.key_values.length),
    0
  )

  return Array.from({ length: width }, (_, index) => configuredKeys[index] ?? `key_${index + 1}`)
})

watch(
  () => [props.projectName, props.message] as const,
  () => {
    closeContext(contextId.value)
    contextId.value = null
    result.value = null
    selectedToken.value = null
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
// position in the list.
function selectValueRow(row: Record<string, unknown>): void {
  const token = typeof row.token === 'string' ? row.token : null
  if (token === null) {
    return
  }
  selectedToken.value = token
  void sendRequest()
}

// Offer the complete unmatched key set as a CSV file. The response already
// holds every value, so no request is needed.
function exportUnmatchedValues(): void {
  const values = result.value?.values?.values ?? []
  if (values.length === 0) {
    return
  }

  const keyColumns = unmatchedKeyColumns.value
  const headers = [...keyColumns, 'Local rows']
  const rows = values.map((value) => [
    ...keyColumns.map((_, index) => value.key_values[index] ?? null),
    value.local_row_count,
  ])

  downloadCsv(unmatchedValuesFilename(), toCsv(headers, rows))
}

function unmatchedValuesFilename(): string {
  const entity = (result.value?.relationship?.local_entity || props.message.entity || 'entity')
    .replace(/[^a-z0-9_-]+/gi, '-')
    .toLowerCase()
  return `${entity}_unmatched_keys_${Date.now()}.csv`
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
    ...(selectedToken.value === null ? {} : { selected_value_token: selectedToken.value }),
  }

  const pageRequest: IntegrityTroubleshootPageRequest = {
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
