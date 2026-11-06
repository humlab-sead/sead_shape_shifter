<template>
  <v-dialog
    :model-value="modelValue"
    max-width="1100"
    scrollable
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <span>{{ header }}</span>
        <v-btn icon="mdi-close" variant="text" aria-label="Close link troubleshooter" @click="close" />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-alert v-if="localMessage" type="info" variant="tonal" class="mb-4">
          {{ localMessage }}
        </v-alert>

        <IntegrityTroubleshooterBody
          v-if="modelValue && isIntegrityIssue && !localMessage"
          :project-name="projectName"
          :message="message"
          @remote-entity="integrityRemoteEntity = $event"
        />

        <v-progress-linear v-if="!isIntegrityIssue && loading" indeterminate color="primary" class="mb-4" />

        <v-alert v-if="!isIntegrityIssue && error" type="error" variant="tonal" class="mb-4">
          <div>{{ error.message }}</div>
          <ul v-if="error.tips?.length" class="mt-2">
            <li v-for="tip in error.tips" :key="tip">{{ tip }}</li>
          </ul>
        </v-alert>

        <template v-if="!isIntegrityIssue && result">
          <v-alert
            :type="result.status === 'reproduced' ? 'success' : 'warning'"
            variant="tonal"
            class="mb-4"
            :title="result.status"
          >
            <div class="text-caption mb-1">Reason: {{ result.reason }}</div>
            <div>{{ result.message }}</div>
          </v-alert>

          <section v-if="result.relationship" class="mb-5" aria-label="Saved relationship">
            <h3 class="text-subtitle-1 mb-2">Saved relationship</h3>
            <div class="d-flex flex-wrap ga-2 mb-2">
              <v-chip>A: {{ result.relationship.local_entity }}</v-chip>
              <v-chip>B: {{ result.relationship.remote_entity || '—' }}</v-chip>
              <v-chip>Join: {{ result.relationship.join_type || '—' }}</v-chip>
              <v-chip>Link pass: {{ result.relationship.link_pass || '—' }}</v-chip>
            </div>
            <div class="text-body-2 font-weight-medium mb-1">Constraints</div>
            <div v-if="Object.keys(result.relationship.constraints).length" class="d-flex flex-wrap ga-2">
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
          </section>

          <template v-if="result.status === 'reproduced' && result.baseline">
            <section v-if="result.key_options" class="mb-5" aria-label="Trial keys">
              <div class="d-flex align-center justify-space-between mb-2">
                <h3 class="text-subtitle-1">Trial key pairs</h3>
                <v-btn size="small" variant="outlined" prepend-icon="mdi-plus" @click="addKeyPair">Add pair</v-btn>
              </div>

              <div v-if="keyPairCount === 0" class="text-body-2 text-medium-emphasis mb-2">
                Add at least one local and remote key pair.
              </div>
              <div v-for="(_, index) in keyPairCount" :key="index" class="d-flex align-center ga-2 mb-2">
                <v-select
                  v-model="localKeys[index]"
                  :items="result.key_options.local"
                  label="A key"
                  density="compact"
                  hide-details
                />
                <v-select
                  v-model="remoteKeys[index]"
                  :items="result.key_options.remote"
                  label="B key"
                  density="compact"
                  hide-details
                />
                <v-btn
                  icon="mdi-delete-outline"
                  size="small"
                  variant="text"
                  :aria-label="`Remove key pair ${index + 1}`"
                  @click="removeKeyPair(index)"
                />
              </div>

              <v-btn color="primary" :disabled="!canRunTrial || loading" @click="runTrial">Run trial</v-btn>
            </section>

            <section class="mb-5" aria-label="Baseline and trial comparison">
              <h3 class="text-subtitle-1 mb-1">Baseline and trial comparison</h3>
              <p class="text-caption text-medium-emphasis">Complete totals cover the full link input.</p>
              <v-alert
                v-if="
                  result.baseline.diagnostic_status === 'failed' || result.baseline.diagnostic_status === 'incomplete'
                "
                type="warning"
                variant="tonal"
                density="compact"
                class="mb-3"
              >
                <strong>Configured-key diagnostics {{ result.baseline.diagnostic_status }}:</strong>
                {{ result.baseline.diagnostic_reason }}. {{ result.baseline.diagnostic_message }}
              </v-alert>
              <v-table density="compact">
                <thead>
                  <tr>
                    <th>Measure</th>
                    <th>Baseline</th>
                    <th>Trial</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="measure in measures" :key="measure.label">
                    <td>{{ measure.label }}</td>
                    <td>{{ formatCount(measure.baseline) }}</td>
                    <td>{{ formatCount(measure.trial) }}</td>
                  </tr>
                </tbody>
              </v-table>
            </section>

            <v-alert
              v-if="result.trial && result.trial.status !== 'complete'"
              :type="result.trial.status === 'failed' ? 'error' : 'warning'"
              variant="tonal"
              class="mb-4"
            >
              <strong>Trial {{ result.trial.status }}:</strong> {{ result.trial.reason }}. {{ result.trial.message }}
            </v-alert>

            <section
              v-if="result.trial?.status === 'complete' && result.trial.pagination"
              class="mb-5"
              aria-label="A-row diagnostics"
            >
              <div class="d-flex flex-wrap align-center ga-3 mb-3">
                <v-select
                  v-model="rowFilter"
                  :items="rowFilterOptions"
                  label="Filter rows"
                  density="compact"
                  hide-details
                  class="filter-select"
                  @update:model-value="changeFilter"
                />
                <v-select
                  v-model="pageSize"
                  :items="pageSizeOptions"
                  label="Rows per page"
                  density="compact"
                  hide-details
                  class="page-size-select"
                  @update:model-value="changePageSize"
                />
              </div>
              <v-data-table
                class="trial-rows-table"
                :headers="trialHeaders"
                :items="trialRows"
                item-value="rowKey"
                :items-per-page="-1"
                hide-default-footer
                density="compact"
              >
                <template v-for="(_, index) in trialKeyNames" :key="`key-${index}`" #[`item.key-${index}`]="{ item }">
                  <span>{{ formatValue(item.keyValues[index]) }}</span>
                </template>
                <template #no-data>
                  <div class="text-center text-medium-emphasis py-4">No rows match this filter.</div>
                </template>
              </v-data-table>
              <div class="d-flex justify-end mt-2">
                <v-pagination
                  :model-value="page"
                  :length="pageCount"
                  density="comfortable"
                  @update:model-value="changePage"
                />
              </div>
            </section>

            <section class="mb-2" aria-label="Validation findings">
              <h3 class="text-subtitle-1 mb-2">Findings</h3>
              <div v-if="allIssues.length === 0" class="text-body-2 text-medium-emphasis">No findings.</div>
              <v-list v-else density="compact">
                <v-list-item v-for="(issue, index) in allIssues" :key="`${issue.code || issue.message}-${index}`">
                  <v-list-item-title>
                    <span class="font-weight-medium">{{ issue.source }} · {{ issue.severity }}</span>
                    — {{ issue.message }}
                  </v-list-item-title>
                  <v-list-item-subtitle v-if="issue.suggestion"
                    >Suggestion: {{ issue.suggestion }}</v-list-item-subtitle
                  >
                </v-list-item>
              </v-list>
            </section>
          </template>
        </template>
      </v-card-text>

      <v-divider />
      <v-card-actions class="justify-end">
        <v-btn variant="text" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useLinkTroubleshooter } from '@/composables/useLinkTroubleshooter'
import type { LinkTroubleshootRowFilter, ValidationError } from '@/types'
import {
  INTEGRITY_ISSUE_CODE,
  integrityTroubleshootRefusal,
  toLinkTroubleshootRequest,
} from '@/utils/linkTroubleshooter'
import IntegrityTroubleshooterBody from './IntegrityTroubleshooterBody.vue'

interface Props {
  modelValue: boolean
  projectName: string
  message: ValidationError
}

interface Finding {
  source: 'Baseline' | 'Trial'
  code?: string | null
  severity: string
  message: string
  suggestion?: string | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()
const localMessage = ref<string | null>(null)
const integrityRemoteEntity = ref<string | null>(null)

const { loading, error, result, localKeys, remoteKeys, page, pageSize, rowFilter, open, run, reset } =
  useLinkTroubleshooter(props.projectName)

const isIntegrityIssue = computed(() => props.message.code === INTEGRITY_ISSUE_CODE)

const header = computed(() => {
  const localEntity = result.value?.relationship?.local_entity || props.message.entity || 'Unknown entity'
  // The warning metadata carries the remote entity, so the header stays correct while the first request loads.
  const metadataRemote = props.message.metadata?.remote_entity
  const remoteEntity =
    result.value?.relationship?.remote_entity ||
    integrityRemoteEntity.value ||
    (typeof metadataRemote === 'string' && metadataRemote.trim().length > 0 ? metadataRemote : 'Unknown entity')
  return `${localEntity} → ${remoteEntity}`
})
const keyPairCount = computed(() => Math.max(localKeys.value.length, remoteKeys.value.length))
const canRunTrial = computed(
  () =>
    localKeys.value.length > 0 &&
    localKeys.value.length === remoteKeys.value.length &&
    localKeys.value.every((key, index) => key.trim().length > 0 && (remoteKeys.value[index] ?? '').trim().length > 0)
)
const pageCount = computed(() => {
  const filteredCount = result.value?.trial?.pagination?.filtered_row_count ?? 0
  return Math.max(1, Math.ceil(filteredCount / pageSize.value))
})
const measures = computed(() => {
  const baseline = result.value?.baseline
  const trial = result.value?.trial?.status === 'complete' ? result.value.trial.totals : null
  return [
    { label: 'Input A rows', baseline: baseline?.input_a_rows, trial: trial?.input_a_rows },
    { label: 'Output rows', baseline: baseline?.output_rows, trial: trial?.output_rows },
    { label: 'Unmatched A rows', baseline: baseline?.unmatched_a_rows, trial: trial?.unmatched_a_rows },
    {
      label: 'Multiply matched A rows',
      baseline: baseline?.multiply_matched_a_rows,
      trial: trial?.multiply_matched_a_rows,
    },
  ]
})
const allIssues = computed<Finding[]>(() => [
  ...(result.value?.baseline?.issues ?? []).map((issue) => ({ ...issue, source: 'Baseline' as const })),
  ...(result.value?.trial?.issues ?? []).map((issue) => ({ ...issue, source: 'Trial' as const })),
])

interface TrialTableRow {
  rowKey: number
  inputRow: number
  keyValues: unknown[]
  matched: string
  remoteMatchCount: number
  outputRowContribution: number
}

const trialKeyNames = computed<string[]>(() => result.value?.trial?.local_keys ?? [])

// Headers are not sortable: the backend pages the filtered rows in a fixed order,
// so sorting one page would only reorder the rows currently returned.
const trialHeaders = computed(() => [
  { title: 'Input row', key: 'inputRow', sortable: false },
  ...trialKeyNames.value.map((key, index) => ({ title: `A key: ${key}`, key: `key-${index}`, sortable: false })),
  { title: 'Matched', key: 'matched', sortable: false },
  { title: 'Remote matches', key: 'remoteMatchCount', sortable: false },
  { title: 'Output rows', key: 'outputRowContribution', sortable: false },
])

const trialRows = computed<TrialTableRow[]>(() =>
  (result.value?.trial?.rows ?? []).map((row) => ({
    rowKey: row.input_position,
    inputRow: row.input_position + 1,
    keyValues: row.key_values,
    matched: row.matched ? 'Yes' : 'No',
    remoteMatchCount: row.remote_match_count,
    outputRowContribution: row.output_row_contribution,
  }))
)

const rowFilterOptions = [
  { title: 'All rows', value: 'all' },
  { title: 'Unmatched', value: 'unmatched' },
  { title: 'Multiply matched', value: 'multiply_matched' },
]
const pageSizeOptions = [25, 50, 100, 200]

watch(
  () => [props.modelValue, props.message] as const,
  async ([isOpen, message]) => {
    integrityRemoteEntity.value = null
    if (!isOpen) {
      localMessage.value = null
      reset()
      return
    }

    if (message.code === INTEGRITY_ISSUE_CODE) {
      // Integrity inspection has its own read-only body and endpoint, so the
      // row-count request and trial state are cleared instead of opened.
      reset()
      localMessage.value = integrityTroubleshootRefusal(message)
      return
    }

    localMessage.value = null
    const request = toLinkTroubleshootRequest(message)
    if (!request) {
      localMessage.value = 'This warning cannot be troubleshot.'
      reset()
      return
    }

    await open(request)
  },
  { immediate: true }
)

function close(): void {
  emit('update:modelValue', false)
}

function addKeyPair(): void {
  localKeys.value.push('')
  remoteKeys.value.push('')
}

function removeKeyPair(index: number): void {
  localKeys.value.splice(index, 1)
  remoteKeys.value.splice(index, 1)
}

function runTrial(): void {
  page.value = 1
  void run()
}

function changeFilter(value: LinkTroubleshootRowFilter): void {
  rowFilter.value = value
  page.value = 1
  void run()
}

function changePageSize(value: number): void {
  pageSize.value = value
  page.value = 1
  void run()
}

function changePage(value: number): void {
  page.value = value
  void run()
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

function formatCount(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}
</script>

<style scoped>
.filter-select {
  max-width: 220px;
}

.page-size-select {
  max-width: 180px;
}
</style>
