<template>
  <div class="integrity-troubleshooter-body">
    <div v-if="loading" class="mb-4 integrity-loading">
      <v-progress-linear indeterminate color="primary" class="mb-1" />
      <p class="text-caption text-medium-emphasis mb-0">
        Reading the link from current data. The link is re-run and its unmatched values recomputed every time this
        dialog opens or its page changes.
      </p>
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
        :title="result.status"
      >
        <div class="text-caption mb-1">Reason: {{ result.reason }}</div>
        <div>{{ result.message }}</div>
      </v-alert>

      <section class="integrity-finding-summary mb-4" aria-label="Integrity finding summary">
        <h2 class="text-subtitle-1 mb-2">Current finding</h2>
        <p v-if="result.current_orphan_count === 0" class="mb-2">
          No unmatched key values are present in the current data.
        </p>
        <p v-else-if="result.current_orphan_count !== null" class="mb-2">
          {{ formatCount(result.current_orphan_count) }} distinct unmatched key values are present in the current data
          for {{ result.relationship?.remote_entity || 'the remote entity' }}.
        </p>
        <p v-else class="mb-2">The current unmatched key-value count is unavailable.</p>
        <v-btn v-if="result.values" size="small" variant="outlined" @click="focusUnmatchedValues">
          Inspect unmatched values
        </v-btn>
        <section class="mt-3" aria-label="Unmatched value counts">
          <v-table density="compact">
            <tbody>
              <tr>
                <td>Recorded unmatched key values</td>
                <td>{{ formatCount(result.recorded_orphan_count) }}</td>
              </tr>
              <tr>
                <td>Current unmatched key values</td>
                <td>{{ formatCount(result.current_orphan_count) }}</td>
              </tr>
            </tbody>
          </v-table>
        </section>
      </section>

      <div class="integrity-troubleshooter-workspace">
        <aside class="integrity-link-details" aria-label="Saved link details">
          <section v-if="result.relationship" class="mb-5" aria-label="Saved relationship">
            <h3 class="text-subtitle-1 mb-2">Saved relationship</h3>
            <div class="d-flex flex-wrap ga-2 mb-2">
              <v-chip>A: {{ result.relationship.local_entity }}</v-chip>
              <v-chip>B: {{ result.relationship.remote_entity || '—' }}</v-chip>
              <v-chip>Link index: {{ formatCount(result.relationship.fk_index) }}</v-chip>
              <v-chip>Join: {{ result.relationship.join_type || '—' }}</v-chip>
            </div>
            <details class="integrity-details">
              <summary>Saved link rules</summary>
              <div v-if="Object.keys(result.relationship.constraints).length" class="d-flex flex-wrap ga-2 mt-2">
                <v-chip
                  v-for="(value, key) in result.relationship.constraints"
                  :key="key"
                  size="small"
                  variant="outlined"
                >
                  {{ key }}: {{ formatValue(value) }}
                </v-chip>
              </div>
              <span v-else class="text-body-2 text-medium-emphasis">None configured</span>
            </details>
          </section>

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

        <main class="integrity-results">
          <section v-if="result.values" class="mb-5" aria-label="Unmatched values">
            <h3 ref="unmatchedValuesRef" class="text-subtitle-1 mb-2">Unmatched values</h3>
            <div class="text-body-2">
              Complete distinct unmatched value count: {{ result.values.distinct_value_count }}
            </div>
            <div class="text-caption text-medium-emphasis mb-3">
              Showing {{ result.values.returned_value_count }} of {{ result.values.distinct_value_count }} values · Page
              {{ result.values.page }}
            </div>

            <v-data-table
              v-if="result.values.values.length > 0"
              class="integrity-values-table"
              :headers="valueHeaders"
              :items="valueRows"
              item-value="rowKey"
              :items-per-page="-1"
              hide-default-footer
              density="compact"
            >
              <template #item.actions="{ item }">
                <div class="text-right">
                  <v-btn
                    class="integrity-select-value"
                    size="x-small"
                    variant="text"
                    :disabled="loading"
                    @click="selectValue(item.value)"
                  >
                    Show local rows
                  </v-btn>
                </div>
              </template>
            </v-data-table>
            <p v-else class="text-body-2 text-medium-emphasis">No unmatched values on this page.</p>

            <div v-if="pageCount > 1" class="d-flex justify-end mt-2">
              <v-pagination
                :model-value="result.values.page"
                :length="pageCount"
                density="comfortable"
                @update:model-value="changePage"
              />
            </div>
          </section>

          <section v-if="result.selected" class="mb-2" aria-label="Selected value rows">
            <template v-if="result.selected.status === 'selected'">
              <h3 class="text-subtitle-1 mb-1">Affected local rows</h3>
              <div class="text-body-2">Selected key: {{ formatKey(result.selected.key_values ?? []) }}</div>
              <div class="text-body-2 mb-2">
                Local rows for this value: {{ formatCount(result.selected.total_row_count) }} · Returned rows:
                {{ formatCount(result.selected.returned_row_count) }}
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
              <v-table density="compact">
                <thead>
                  <tr>
                    <th v-for="column in result.selected.columns" :key="column">{{ column }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in result.selected.rows" :key="index">
                    <td v-for="column in result.selected.columns" :key="column">{{ formatValue(row[column]) }}</td>
                  </tr>
                  <tr v-if="result.selected.rows.length === 0">
                    <td :colspan="Math.max(result.selected.columns.length, 1)" class="text-center text-medium-emphasis">
                      No local rows.
                    </td>
                  </tr>
                </tbody>
              </v-table>
            </template>

            <v-alert v-else type="warning" variant="tonal" density="compact" class="integrity-selection-unavailable">
              <div v-if="result.selected.reason" class="text-caption mb-1">Reason: {{ result.selected.reason }}</div>
              <div>{{ result.selected.message }}</div>
            </v-alert>
          </section>
        </main>
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
  IntegrityTroubleshootResponse,
  IntegrityTroubleshootValue,
  ValidationError,
} from '@/types'
import { formatErrorMessage } from '@/utils/errors'
import { toIntegrityTroubleshootRequest } from '@/utils/linkTroubleshooter'

interface Props {
  projectName: string
  message: ValidationError
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (event: 'remote-entity', value: string | null): void
}>()

const loading = ref(false)
const error = ref<FormattedError | null>(null)
const result = ref<IntegrityTroubleshootResponse | null>(null)
const page = ref(1)
const selectedToken = ref<string | null>(null)
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

const pageCount = computed(() => {
  const values = result.value?.values
  if (!values || values.page_size <= 0) {
    return 1
  }

  return Math.max(1, Math.ceil(values.distinct_value_count / values.page_size))
})

interface ValueTableRow {
  rowKey: string
  unmatchedKey: string
  localRowCount: number
  value: IntegrityTroubleshootValue
}

// Headers are not sortable: the backend pages the complete value set in a fixed
// order, so sorting one page would only reorder the rows currently returned.
const valueHeaders = [
  { title: 'Unmatched key', key: 'unmatchedKey', sortable: false },
  { title: 'Local rows', key: 'localRowCount', align: 'end' as const, sortable: false },
  { title: 'Rows', key: 'actions', align: 'end' as const, sortable: false },
]

const valueRows = computed<ValueTableRow[]>(() =>
  (result.value?.values?.values ?? []).map((value, index) => ({
    rowKey: `${value.token}-${index}`,
    unmatchedKey: formatKey(value.key_values),
    localRowCount: value.local_row_count,
    value,
  }))
)

watch(
  () => [props.projectName, props.message] as const,
  () => {
    page.value = 1
    selectedToken.value = null
    void sendRequest()
  },
  { immediate: true }
)

// Closing the dialog unmounts this body; a late response must not be applied.
onBeforeUnmount(() => {
  requestVersion += 1
})

function selectValue(value: IntegrityTroubleshootValue): void {
  selectedToken.value = value.token
  void sendRequest()
}

function changePage(value: number): void {
  page.value = value
  selectedToken.value = null
  void sendRequest()
}

function focusUnmatchedValues(): void {
  unmatchedValuesRef.value?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
}

async function sendRequest(): Promise<void> {
  const identity: IntegrityTroubleshootRequest | null = toIntegrityTroubleshootRequest(props.message)
  if (!identity) {
    result.value = null
    error.value = null
    return
  }

  const request: IntegrityTroubleshootRequest = {
    ...identity,
    page: page.value,
    ...(selectedToken.value === null ? {} : { selected_value_token: selectedToken.value }),
  }

  const version = ++requestVersion
  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await integrityTroubleshooterApi.inspect(props.projectName, request)
    if (version !== requestVersion) {
      return
    }

    result.value = response
    emit('remote-entity', response.relationship?.remote_entity ?? null)
  } catch (caughtError: unknown) {
    if (version !== requestVersion) {
      return
    }

    error.value = formatErrorMessage(caughtError)
    result.value = null
    console.error('Integrity troubleshooter request failed:', caughtError)
  } finally {
    if (version === requestVersion) {
      loading.value = false
    }
  }
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
</script>

<style scoped>
.integrity-finding-summary {
  padding: 1rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 0.5rem;
  background: rgba(var(--v-theme-primary), 0.04);
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
</style>
