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

        <div v-if="!isIntegrityIssue && loading" class="mb-4 troubleshooter-loading">
          <v-progress-linear indeterminate color="primary" class="mb-1" />
          <p class="text-caption text-medium-emphasis mb-0">
            Reading the link from current data. The link is re-run when this dialog opens and when the retained inputs
            expire; changing pages or groups reads nothing new.
          </p>
        </div>

        <v-alert v-if="!isIntegrityIssue && refreshed" type="info" variant="tonal" class="mb-4">
          The retained inputs expired and were reproduced again from current data. Run a new trial to compare the
          refreshed baseline.
        </v-alert>

        <v-alert v-if="!isIntegrityIssue && error" type="error" variant="tonal" class="mb-4">
          <div>{{ error.message }}</div>
          <ul v-if="error.tips?.length" class="mt-2">
            <li v-for="tip in error.tips" :key="tip">{{ tip }}</li>
          </ul>
        </v-alert>

        <template v-if="!isIntegrityIssue && result">
          <v-alert
            v-if="result.status !== 'reproduced'"
            type="warning"
            variant="tonal"
            class="mb-4"
            :title="result.status"
          >
            <div class="text-caption mb-1">Reason: {{ result.reason }}</div>
            <div>{{ result.message }}</div>
          </v-alert>

          <section
            v-if="result.status === 'reproduced' && result.baseline"
            class="link-finding-summary mb-4"
            aria-label="Link finding summary"
          >
            <h2 v-if="unmatchedHeadline" class="text-subtitle-1 font-weight-bold mb-1">
              {{ unmatchedHeadline }}
            </h2>
            <p v-if="savedJoinEffect" class="text-body-2 text-medium-emphasis mb-0">
              {{ savedJoinEffect }}
            </p>
          </section>

          <div
            class="link-troubleshooter-workspace"
            :class="{ 'link-troubleshooter-workspace--single': result.status !== 'reproduced' || !result.baseline }"
          >
            <aside class="link-troubleshooter-settings" aria-label="Link settings">
              <section v-if="result.relationship" class="mb-5" aria-label="Saved relationship">
                <h3 class="text-subtitle-1 mb-2">Saved relationship</h3>
                <div class="d-flex flex-wrap ga-2 mb-2">
                  <v-chip>A: {{ result.relationship.local_entity }}</v-chip>
                  <v-chip>B: {{ result.relationship.remote_entity || '—' }}</v-chip>
                  <v-chip>Join: {{ result.relationship.join_type || '—' }}</v-chip>
                  <v-chip>Link pass: {{ result.relationship.link_pass || '—' }}</v-chip>
                </div>
                <details class="link-troubleshooter-details">
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

              <template v-if="result.status === 'reproduced' && result.baseline">
                <section v-if="result.key_options" class="mb-5" aria-label="Trial keys">
                  <div class="d-flex align-center justify-space-between mb-2">
                    <h3 class="text-subtitle-1">Try a different link</h3>
                  </div>

                  <div class="link-key-pair-headings" aria-hidden="true">
                    <span>{{ localEntityName }}</span>
                    <span>{{ remoteEntityName }}</span>
                    <span />
                  </div>
                  <div v-if="keyPairCount === 0" class="text-body-2 text-medium-emphasis mb-2">
                    Add at least one local and remote key pair.
                  </div>
                  <div v-for="(_, index) in keyPairCount" :key="index" class="d-flex align-center ga-2 mb-2">
                    <v-select
                      v-model="localKeys[index]"
                      :items="result.key_options.local"
                      :aria-label="`Key pair ${index + 1} local key (${localEntityName})`"
                      density="compact"
                      hide-details
                    />
                    <v-select
                      v-model="remoteKeys[index]"
                      :items="result.key_options.remote"
                      :aria-label="`Key pair ${index + 1} remote key (${remoteEntityName})`"
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

                  <div class="mb-3">
                    <v-btn size="small" variant="outlined" prepend-icon="mdi-plus" @click="addKeyPair"
                      >Add key pair</v-btn
                    >
                  </div>

                  <div class="d-flex flex-wrap align-center ga-3 mb-2">
                    <v-select
                      v-model="how"
                      :items="joinTypeOptions"
                      label="Join type"
                      density="compact"
                      hide-details
                      class="filter-select"
                    />
                  </div>
                  <p v-if="result.baseline.settings" class="text-caption text-medium-emphasis mb-3">
                    Saved: {{ describeJoin(result.baseline.settings.join_type) }}
                  </p>

                  <details class="link-troubleshooter-details mb-3">
                    <summary>Advanced trial settings</summary>
                    <div class="d-flex flex-wrap align-center ga-2 mt-3">
                      <div class="d-flex align-center ga-1">
                        <v-select
                          v-model="allowNullKeys"
                          :items="nullOptionItems"
                          label="Allow missing join keys"
                          density="compact"
                          hide-details
                          class="filter-select"
                        />
                        <v-tooltip location="top" max-width="360">
                          <template #activator="{ props }">
                            <v-btn
                              v-bind="props"
                              icon
                              size="x-small"
                              variant="text"
                              class="text-medium-emphasis"
                              aria-label="About allowing missing join keys"
                            >
                              <v-icon icon="mdi-help-circle-outline" size="small" />
                            </v-btn>
                          </template>
                          <div class="text-body-2">
                            <strong>Allow missing join keys</strong>
                            <p class="mt-1 mb-1">
                              Lets rows with a missing (null) key value still join. Missing key columns are reported as
                              separate findings.
                            </p>
                            <p v-if="result.baseline.settings" class="mb-0">
                              Allow missing join keys:
                              {{ describeSetting(result.baseline.settings.allow_null_keys) }}. Strict null checks are
                              {{
                                result.baseline.settings.resolved_null_policy.enforce_strict_null_keys
                                  ? 'enforced'
                                  : 'relaxed'
                              }}.
                            </p>
                            <p v-else class="mb-0">This diagnostic has no resolved settings report.</p>
                          </div>
                        </v-tooltip>
                      </div>
                      <div class="d-flex align-center ga-1">
                        <v-select
                          v-model="nullKeysEqual"
                          :items="nullOptionItems"
                          label="Match null join-key parts"
                          density="compact"
                          hide-details
                          class="filter-select"
                        />
                        <v-tooltip location="top" max-width="360">
                          <template #activator="{ props }">
                            <v-btn
                              v-bind="props"
                              icon
                              size="x-small"
                              variant="text"
                              class="text-medium-emphasis"
                              aria-label="About matching null join-key parts"
                            >
                              <v-icon icon="mdi-help-circle-outline" size="small" />
                            </v-btn>
                          </template>
                          <div class="text-body-2">
                            <strong>Match null join-key parts</strong>
                            <p class="mt-1 mb-1">
                              Treats two missing (null) key values as equal, so rows can match on null.
                            </p>
                            <p v-if="result.baseline.settings" class="mb-0">
                              Match null join-key parts:
                              {{ describeSetting(result.baseline.settings.null_keys_equal) }}. Null key matches are
                              {{
                                result.baseline.settings.resolved_null_policy.prevent_null_key_matches
                                  ? 'prevented'
                                  : 'allowed'
                              }}.
                            </p>
                            <p v-else class="mb-0">This diagnostic has no resolved settings report.</p>
                          </div>
                        </v-tooltip>
                      </div>
                    </div>
                  </details>

                  <div class="d-flex align-center ga-2">
                    <v-btn color="primary" :disabled="!canRunTrial || loading" @click="runTrial">Run trial</v-btn>
                    <v-btn variant="text" :disabled="!result.baseline" @click="reset">Reset to saved</v-btn>
                  </div>
                </section>
              </template>
            </aside>

            <section
              v-if="result.status === 'reproduced' && result.baseline"
              class="link-troubleshooter-results"
              aria-label="Link results"
            >
              <section class="mb-5" aria-label="Baseline and trial comparison">
                <h2 class="text-subtitle-1 mb-1">Results</h2>
                <p class="text-caption text-medium-emphasis">Totals cover the full link input.</p>
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
                      <th>Saved link</th>
                      <th v-if="trial">Last trial</th>
                      <th v-if="trial">Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="measure in measures" :key="measure.label">
                      <td>{{ measure.label }}</td>
                      <td>{{ formatCount(measure.baseline) }}</td>
                      <td v-if="trial">{{ formatCount(measure.trial) }}</td>
                      <td v-if="trial">{{ formatDelta(measure.baseline, measure.trial) }}</td>
                    </tr>
                  </tbody>
                </v-table>
              </section>

              <v-alert v-if="trial && trialStale" type="warning" variant="tonal" class="mb-4">
                Settings changed — rerun the trial. The comparison below is from the previous settings.
              </v-alert>

              <v-alert
                v-if="trial && trial.status !== 'complete'"
                :type="trial.status === 'failed' ? 'error' : 'warning'"
                variant="tonal"
                class="mb-4"
              >
                <strong>Trial {{ trial.status }}:</strong> {{ trial.reason }}. {{ trial.message }}
              </v-alert>

              <p v-if="!trial" class="text-body-2 text-medium-emphasis mb-4">
                Run a trial to compare the saved link with the selected keys and settings.
              </p>

              <section class="mb-5" aria-label="Exception rows">
                <h3 class="text-subtitle-1 mb-2">Inspect affected rows</h3>
                <div class="d-flex flex-wrap align-center ga-3 mb-3">
                  <v-select
                    v-model="side"
                    :items="sideOptions"
                    label="Result source"
                    density="compact"
                    hide-details
                    class="filter-select"
                  />
                  <div class="d-flex flex-wrap ga-2" role="group" aria-label="Affected row category">
                    <v-btn
                      data-group="unmatched"
                      size="small"
                      :variant="group === 'unmatched' ? 'flat' : 'outlined'"
                      :aria-pressed="group === 'unmatched'"
                      @click="selectGroup('unmatched')"
                    >
                      Unmatched · {{ formatCount(activeDetail?.unmatched?.total_count) }}
                    </v-btn>
                    <v-btn
                      data-group="multiply_matched"
                      size="small"
                      :variant="group === 'multiply_matched' ? 'flat' : 'outlined'"
                      :aria-pressed="group === 'multiply_matched'"
                      @click="selectGroup('multiply_matched')"
                    >
                      Multiple matches · {{ formatCount(activeDetail?.multiply_matched?.total_count) }}
                    </v-btn>
                  </div>
                </div>
                <div v-if="activeRows.length > 25" class="mb-3">
                  <v-select
                    v-model="pageSize"
                    :items="pageSizeOptions"
                    label="Rows per page"
                    density="compact"
                    hide-details
                    class="page-size-select"
                  />
                </div>

                <div v-if="!activeGroup" class="text-body-2 text-medium-emphasis">
                  No exception rows are available for this selection.
                </div>
                <template v-else>
                  <p class="text-body-2 mb-2">
                    Showing {{ pagedRows.length.toLocaleString() }} of
                    {{ activeGroup.returned_count.toLocaleString() }} returned rows;
                    {{ activeGroup.total_count.toLocaleString() }} affected source rows in total.
                  </p>
                  <v-alert
                    v-if="activeGroup.row_cap_reached"
                    type="info"
                    variant="tonal"
                    density="compact"
                    class="mb-2"
                  >
                    Only the first {{ activeGroup.row_cap.toLocaleString() }} exception rows are returned.
                  </v-alert>
                  <v-alert
                    v-if="activeGroup.budget_exhausted"
                    type="info"
                    variant="tonal"
                    density="compact"
                    class="mb-2"
                  >
                    The response size limit stopped further exception rows.
                  </v-alert>
                  <v-alert
                    v-if="activeDetail?.detail_truncated"
                    type="info"
                    variant="tonal"
                    density="compact"
                    class="mb-2"
                  >
                    Some findings or key values in this response were shortened.
                  </v-alert>

                  <v-data-table
                    v-if="pagedRows.length"
                    class="exception-rows-table"
                    :headers="exceptionHeaders"
                    :items="pagedRows"
                    item-value="input_position"
                    :items-per-page="-1"
                    hide-default-footer
                    density="compact"
                  >
                    <template #item.input_position="{ item }">{{ item.input_position + 1 }}</template>
                    <template
                      v-for="(_, index) in activeKeyNames"
                      :key="`key-${index}`"
                      #[`item.key-${index}`]="{ item }"
                    >
                      <span>{{ formatKeyValue(item.key_values[index]) }}</span>
                    </template>
                  </v-data-table>
                  <div v-else class="text-center text-medium-emphasis py-4">
                    No returned exception rows are available for this page.
                  </div>
                  <div class="d-flex justify-end mt-2">
                    <v-pagination
                      :model-value="page"
                      :length="pageCount"
                      density="comfortable"
                      @update:model-value="page = $event"
                    />
                  </div>
                </template>
              </section>
            </section>
          </div>

          <details class="link-troubleshooter-details mt-4" aria-label="Technical details">
            <summary>Technical details</summary>
            <p class="text-body-2 mt-2">{{ message.message }}</p>
            <section class="mb-2" aria-label="Validation findings">
              <h3 class="text-subtitle-1 mb-2">Findings</h3>
              <p v-if="findingsNotice" class="text-caption text-medium-emphasis">{{ findingsNotice }}</p>
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
          </details>
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
import { useLinkTroubleshooter, type LinkExceptionGroupName } from '@/composables/useLinkTroubleshooter'
import type {
  LinkTroubleshootExceptionRow,
  LinkTroubleshootJoinTypeSetting,
  LinkTroubleshootKeyValue,
  LinkTroubleshootRequestedSetting,
  ValidationError,
} from '@/types'
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

const {
  loading,
  error,
  context,
  trial,
  trialLocalKeys,
  trialStale,
  refreshed,
  localKeys,
  remoteKeys,
  how,
  allowNullKeys,
  nullKeysEqual,
  page,
  pageSize,
  group,
  side,
  canRunTrial,
  open,
  run,
  reset,
  close: releaseContext,
} = useLinkTroubleshooter(props.projectName)

// The retained context response holds the baseline and relationship details.
const result = context

const isIntegrityIssue = computed(() => props.message.code === INTEGRITY_ISSUE_CODE)

const localEntityName = computed(() => result.value?.relationship?.local_entity || props.message.entity || 'A')
const remoteEntityName = computed(() => {
  const metadataRemote = props.message.metadata?.remote_entity
  return (
    result.value?.relationship?.remote_entity ||
    integrityRemoteEntity.value ||
    (typeof metadataRemote === 'string' && metadataRemote.trim().length > 0 ? metadataRemote : 'B')
  )
})
const header = computed(() => `${localEntityName.value} → ${remoteEntityName.value}`)
const keyPairCount = computed(() => Math.max(localKeys.value.length, remoteKeys.value.length))
const measures = computed(() => {
  const baseline = result.value?.baseline
  const totals = trial.value?.status === 'complete' ? trial.value.totals : null
  return [
    { label: 'Input A rows', baseline: baseline?.input_a_rows, trial: totals?.input_a_rows },
    { label: 'Output rows', baseline: baseline?.output_rows, trial: totals?.output_rows },
    { label: 'Unmatched A rows', baseline: baseline?.unmatched_a_rows, trial: totals?.unmatched_a_rows },
    {
      label: 'Multiply matched A rows',
      baseline: baseline?.multiply_matched_a_rows,
      trial: totals?.multiply_matched_a_rows,
    },
  ]
})

// First summary line: how many source rows find no match at all.
const unmatchedHeadline = computed<string | null>(() => {
  const count = result.value?.baseline?.unmatched_a_rows
  if (count === null || count === undefined) {
    return null
  }
  const target = remoteEntityName.value
  return count === 1
    ? `1 source row has no match in ${target}`
    : `${formatCount(count)} source rows have no match in ${target}`
})

// Second summary line: what the saved join does with those rows.
const savedJoinEffect = computed<string | null>(() => {
  const baseline = result.value?.baseline
  if (!baseline || baseline.input_a_rows === null || baseline.output_rows === null) {
    return null
  }
  const counts = `${formatCount(baseline.input_a_rows)} input → ${formatCount(baseline.output_rows)} output`
  const joinType = baseline.settings?.join_type.effective ?? null
  if (!joinType) {
    return `Saved link: ${counts}.`
  }
  const effect = joinType === 'left' ? 'keeps' : 'removes'
  return baseline.unmatched_a_rows === null
    ? `The saved ${joinType} join produces ${counts}.`
    : `The saved ${joinType} join ${effect} these rows: ${counts}.`
})

const baselineFindings = computed(() => result.value?.baseline?.detail?.findings ?? null)
const trialFindings = computed(() => trial.value?.detail?.findings ?? null)
const allIssues = computed<Finding[]>(() => {
  const issues: Finding[] = []
  for (const issue of baselineFindings.value?.issues ?? []) {
    issues.push({ ...issue, source: 'Baseline' })
  }
  for (const issue of trialFindings.value?.issues ?? []) {
    issues.push({ ...issue, source: 'Trial' })
  }
  return issues
})
const findingsNotice = computed(() => {
  const notices: string[] = []
  const sides = [
    ['Baseline', baselineFindings.value],
    ['Trial', trialFindings.value],
  ] as const
  for (const [label, findings] of sides) {
    if (findings && findings.returned_count < findings.total_count) {
      notices.push(`${label}: showing ${findings.returned_count} of ${findings.total_count} findings.`)
    }
  }
  return notices.join(' ')
})

const baselineDetail = computed(() => result.value?.baseline?.detail ?? null)
const trialDetail = computed(() => trial.value?.detail ?? null)
const activeDetail = computed(() => (side.value === 'trial' ? trialDetail.value : baselineDetail.value))
const activeGroup = computed(() => {
  const detail = activeDetail.value
  if (!detail) {
    return null
  }
  return detail[group.value]
})
const activeKeyNames = computed<string[]>(() =>
  side.value === 'trial' ? trialLocalKeys.value : (result.value?.configured_keys?.local_keys ?? [])
)
const activeRows = computed<LinkTroubleshootExceptionRow[]>(() => activeGroup.value?.rows ?? [])
const pageCount = computed(() => Math.max(1, Math.ceil(activeRows.value.length / pageSize.value)))
const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return activeRows.value.slice(start, start + pageSize.value)
})
watch([side, group, pageSize, trial], () => {
  page.value = 1
})
// Headers are not sortable: the backend returns a fixed bounded order, so
// sorting one page would only reorder the rows already returned.
const exceptionHeaders = computed(() => [
  { title: 'Input row', key: 'input_position', sortable: false },
  ...activeKeyNames.value.map((key, index) => ({ title: `A key: ${key}`, key: `key-${index}`, sortable: false })),
  { title: 'Remote matches', key: 'remote_match_count', sortable: false },
  { title: 'Output rows', key: 'output_row_contribution', sortable: false },
])

const joinTypeOptions = [
  { title: 'Inherit saved', value: null },
  { title: 'Inner', value: 'inner' },
  { title: 'Left', value: 'left' },
]
const nullOptionItems = [
  { title: 'Inherit saved', value: null },
  { title: 'Yes', value: true },
  { title: 'No', value: false },
]
const sideOptions = [
  { title: 'Saved link', value: 'baseline' },
  { title: 'Last trial', value: 'trial' },
]
const pageSizeOptions = [25, 50, 100, 200]

watch(
  () => [props.modelValue, props.message] as const,
  async ([isOpen, message]) => {
    integrityRemoteEntity.value = null
    if (!isOpen) {
      localMessage.value = null
      await releaseContext()
      return
    }

    if (message.code === INTEGRITY_ISSUE_CODE) {
      // Integrity inspection has its own read-only body and endpoint, so the
      // row-count context and trial state are cleared instead of opened.
      await releaseContext()
      localMessage.value = integrityTroubleshootRefusal(message)
      return
    }

    localMessage.value = null
    const request = toLinkTroubleshootRequest(message)
    if (!request) {
      localMessage.value = 'This warning cannot be troubleshot.'
      await releaseContext()
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
  void run()
}

function selectGroup(value: LinkExceptionGroupName): void {
  group.value = value
  page.value = 1
}

function describeJoin(setting: LinkTroubleshootJoinTypeSetting): string {
  const requested = setting.requested === null ? 'inherited' : `${setting.requested} (explicit)`
  return `${requested}; effective ${setting.effective}`
}

function describeSetting(setting: LinkTroubleshootRequestedSetting): string {
  return setting.requested === null ? 'inherited' : `${setting.requested ? 'yes' : 'no'} (explicit)`
}

function formatKeyValue(keyValue: LinkTroubleshootKeyValue | undefined): string {
  if (!keyValue) {
    return '—'
  }
  const text = formatValue(keyValue.value)
  return keyValue.truncated ? `${text}…` : text
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

function formatDelta(saved: number | null | undefined, trialValue: number | null | undefined): string {
  if (saved === null || saved === undefined || trialValue === null || trialValue === undefined) {
    return '—'
  }

  const delta = trialValue - saved
  return delta > 0 ? `+${delta.toLocaleString()}` : delta.toLocaleString()
}
</script>

<style scoped>
.link-troubleshooter-workspace {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.4fr);
  gap: 1.5rem;
  align-items: start;
}

.link-troubleshooter-workspace--single {
  grid-template-columns: minmax(0, 1fr);
}

.link-troubleshooter-settings,
.link-troubleshooter-results {
  min-width: 0;
}

.link-finding-summary {
  padding: 1rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 0.5rem;
  background: rgba(var(--v-theme-primary), 0.04);
}

.link-key-pair-headings {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 40px;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.75rem;
  font-weight: 500;
}

.link-troubleshooter-details {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  padding-top: 0.75rem;
}

.link-troubleshooter-details > summary {
  cursor: pointer;
  font-weight: 500;
}

.filter-select {
  max-width: 220px;
}

.page-size-select {
  max-width: 180px;
}

@media (max-width: 900px) {
  .link-troubleshooter-workspace {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
