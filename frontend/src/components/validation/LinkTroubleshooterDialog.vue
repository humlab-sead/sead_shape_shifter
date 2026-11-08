<template>
  <v-dialog
    :model-value="modelValue"
    :max-width="dialogMaxWidth"
    scrollable
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card
      class="link-troubleshooter-dialog-card"
      :class="{ 'link-troubleshooter-dialog-card--resizing': isResizingDialog }"
      :style="dialogCardStyle"
    >
      <v-card-title class="d-flex align-start justify-space-between ga-2">
        <div class="link-troubleshooter-heading">
          <div>{{ header }}</div>
          <div v-if="relationshipSummary" class="text-body-2 text-medium-emphasis">
            {{ relationshipSummary }}
          </div>
        </div>
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
          @relationship="integrityRelationship = $event"
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

          <div
            class="link-troubleshooter-workspace"
            :class="{ 'link-troubleshooter-workspace--single': result.status !== 'reproduced' || !result.baseline }"
          >
            <aside class="link-troubleshooter-settings" aria-label="Link settings">
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
                    Configured: {{ describeJoin(result.baseline.settings.join_type) }}
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
                    <v-btn variant="text" :disabled="!result.baseline" @click="reset">Reset to configured link</v-btn>
                  </div>
                </section>
              </template>
            </aside>

            <section
              v-if="result.status === 'reproduced' && result.baseline"
              class="link-troubleshooter-results"
              aria-label="Link results"
            >
              <div class="d-flex flex-wrap align-center justify-space-between ga-2 mb-1">
                <div class="d-flex align-center ga-1">
                  <h2 class="text-subtitle-1 mb-0">Inspect results</h2>
                  <v-tooltip location="top" max-width="320">
                    <template #activator="{ props }">
                      <v-btn
                        v-bind="props"
                        icon
                        size="x-small"
                        variant="text"
                        class="text-medium-emphasis"
                        aria-label="About result totals"
                      >
                        <v-icon icon="mdi-help-circle-outline" size="small" />
                      </v-btn>
                    </template>
                    <div class="text-body-2">
                      <div class="mb-1">Totals cover the full link input.</div>
                      <div v-if="joinNote" class="join-note">{{ joinNote }}</div>
                    </div>
                  </v-tooltip>
                </div>
                <div class="d-flex flex-wrap ga-2" role="group" aria-label="Result source">
                  <v-btn
                    data-side="baseline"
                    size="small"
                    :variant="side === 'baseline' ? 'flat' : 'outlined'"
                    :aria-pressed="side === 'baseline'"
                    @click="selectSide('baseline')"
                  >
                    Configured link
                  </v-btn>
                  <v-btn
                    v-if="trial"
                    data-side="trial"
                    size="small"
                    :variant="side === 'trial' ? 'flat' : 'outlined'"
                    :aria-pressed="side === 'trial'"
                    @click="selectSide('trial')"
                  >
                    Last trial
                  </v-btn>
                </div>
              </div>

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

              <v-alert v-if="trial && trialStale" type="warning" variant="tonal" class="mb-4">
                Settings changed — rerun the trial. The result below is from the previous settings.
              </v-alert>

              <v-alert
                v-if="trial && trial.status !== 'complete'"
                :type="trial.status === 'failed' ? 'error' : 'warning'"
                variant="tonal"
                class="mb-4"
              >
                <strong>Trial {{ trial.status }}:</strong> {{ trial.reason }}. {{ trial.message }}
              </v-alert>

              <div class="link-result-stats mb-2">
                <div v-for="stat in resultStats" :key="stat.key" class="link-result-stat" :data-stat="stat.key">
                  <div class="link-result-stat-value">{{ formatCount(stat.value) }}</div>
                  <div class="text-body-2 text-medium-emphasis">{{ stat.label }}</div>
                  <div v-if="showDeltas" class="text-caption text-medium-emphasis" :data-delta="stat.key">
                    {{ formatDelta(stat.configured, stat.value) }} vs configured
                  </div>
                </div>
              </div>

              <section aria-label="Exception rows">
                <div class="affected-row-toolbar d-flex flex-wrap align-center ga-2 mb-3">
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
                  <v-spacer />
                  <v-select
                    v-if="activeGroup"
                    v-model="pageSize"
                    :items="pageSizeOptions"
                    label="Rows per page"
                    density="compact"
                    hide-details
                    class="page-size-select"
                  />
                </div>

                <div v-if="!activeGroup" class="text-body-2 text-medium-emphasis">
                  No affected rows are available for this selection.
                </div>
                <template v-else>
                  <p class="text-body-2 mb-2">
                    Showing {{ formatCount(gridRows.length) }} of {{ formatCount(rowTotalCount) }} affected source
                    rows<span v-if="pageCount > 1"> · Page {{ page }} of {{ pageCount }}</span>
                  </p>
                  <v-alert v-if="rowBrowseCapReached" type="info" variant="tonal" density="compact" class="mb-2">
                    Only the first {{ formatCount(rowBrowseCap) }} affected source rows are browsable.
                  </v-alert>
                  <v-alert v-if="rowStatusMessage" type="info" variant="tonal" density="compact" class="mb-2">
                    {{ rowStatusMessage }}
                  </v-alert>
                  <v-alert v-if="rowsError" type="error" variant="tonal" density="compact" class="mb-2">
                    {{ rowsError.message }}
                  </v-alert>

                  <TroubleshooterDataGrid
                    :columns="exceptionColumns"
                    :rows="gridRows"
                    :loading="rowsLoading"
                    height="360px"
                  />
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

      <button
        type="button"
        class="link-troubleshooter-resize-handle link-troubleshooter-resize-handle--right"
        aria-label="Resize troubleshooting dialog width"
        aria-keyshortcuts="ArrowLeft ArrowRight"
        @pointerdown="startDialogResize($event, 'width')"
        @keydown="resizeDialogWithKeyboard($event, 'width')"
      />
      <button
        type="button"
        class="link-troubleshooter-resize-handle link-troubleshooter-resize-handle--bottom"
        aria-label="Resize troubleshooting dialog height"
        aria-keyshortcuts="ArrowUp ArrowDown"
        @pointerdown="startDialogResize($event, 'height')"
        @keydown="resizeDialogWithKeyboard($event, 'height')"
      />
      <button
        type="button"
        class="link-troubleshooter-resize-handle link-troubleshooter-resize-handle--corner"
        aria-label="Resize troubleshooting dialog width and height"
        aria-keyshortcuts="ArrowLeft ArrowRight ArrowUp ArrowDown"
        @pointerdown="startDialogResize($event, 'both')"
        @keydown="resizeDialogWithKeyboard($event, 'both')"
      />
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  useLinkTroubleshooter,
  type LinkExceptionGroupName,
  type LinkExceptionSide,
} from '@/composables/useLinkTroubleshooter'
import type {
  IntegrityTroubleshootRelationship,
  LinkTroubleshootJoinTypeSetting,
  LinkTroubleshootKeyValue,
  LinkTroubleshootRequestedSetting,
  ValidationError,
} from '@/types'
import { EXCEPTION_ROW_PAGE_LIMIT } from '@/types'
import {
  INTEGRITY_ISSUE_CODE,
  integrityTroubleshootRefusal,
  toLinkTroubleshootRequest,
} from '@/utils/linkTroubleshooter'
import IntegrityTroubleshooterBody from './IntegrityTroubleshooterBody.vue'
import TroubleshooterDataGrid, { type TroubleshooterGridColumn } from './TroubleshooterDataGrid.vue'

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

type DialogResizeDirection = 'width' | 'height' | 'both'

interface DialogResizeStart {
  direction: DialogResizeDirection
  clientX: number
  clientY: number
  width: number
  height: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()
const localMessage = ref<string | null>(null)
const integrityRelationship = ref<IntegrityTroubleshootRelationship | null>(null)
const dialogSize = ref<{ width: number; height: number } | null>(null)
const resizeStart = ref<DialogResizeStart | null>(null)

const dialogMaxWidth = computed(() => (dialogSize.value ? 'calc(100vw - 32px)' : 1100))
const dialogCardStyle = computed(() => {
  if (!dialogSize.value) {
    return undefined
  }

  return {
    width: `${dialogSize.value.width}px`,
    height: `${dialogSize.value.height}px`,
    maxWidth: 'calc(100vw - 32px)',
    maxHeight: 'calc(100vh - 32px)',
  }
})
const isResizingDialog = computed(() => resizeStart.value !== null)

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
  rows,
  rowTotalCount,
  rowBrowseCap,
  rowBrowseCapReached,
  rowStatusMessage,
  rowsLoading,
  rowsError,
  canRunTrial,
  open,
  run,
  reset,
  close: releaseContext,
} = useLinkTroubleshooter(props.projectName)

// The retained context response holds the baseline and relationship details.
const result = context

const isIntegrityIssue = computed(() => props.message.code === INTEGRITY_ISSUE_CODE)

const activeRelationship = computed(() => result.value?.relationship ?? integrityRelationship.value)
const localEntityName = computed(() => activeRelationship.value?.local_entity || props.message.entity || 'A')
const remoteEntityName = computed(() => {
  const metadataRemote = props.message.metadata?.remote_entity
  return (
    activeRelationship.value?.remote_entity ||
    (typeof metadataRemote === 'string' && metadataRemote.trim().length > 0 ? metadataRemote : 'B')
  )
})
const header = computed(() => `${localEntityName.value} → ${remoteEntityName.value}`)

// Format a snake_case value as a short statement, e.g. many_to_one reads as Many-to-one.
function textifyValue(value: string): string {
  const text = value.replace(/_/g, '-')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// Format a snake_case flag name as a short label, e.g. after_unnest reads as After unnest.
function textifyFlag(name: string): string {
  const text = name.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// Configured link facts under the heading: cardinality, linking pass, then the
// constraint flags that are set to true. Unset flags are left out.
const relationshipSummary = computed<string>(() => {
  const relationship = activeRelationship.value
  if (!relationship) {
    return ''
  }
  const parts: string[] = []
  const cardinality = relationship.constraints['cardinality']
  if (typeof cardinality === 'string' && cardinality.trim().length > 0) {
    parts.push(textifyValue(cardinality.trim()))
  }
  if ('link_pass' in relationship && typeof relationship.link_pass === 'string' && relationship.link_pass) {
    parts.push(textifyFlag(relationship.link_pass))
  }
  for (const [key, value] of Object.entries(relationship.constraints)) {
    if (key === 'cardinality' || value !== true) {
      continue
    }
    parts.push(textifyFlag(key))
  }
  return parts.join(' · ')
})

const keyPairCount = computed(() => Math.max(localKeys.value.length, remoteKeys.value.length))
const resultStats = computed(() => {
  const configured = result.value?.baseline
  const active = side.value === 'trial' ? (trial.value?.totals ?? null) : configured
  return [
    {
      key: 'source_rows',
      label: 'Source rows',
      value: active?.input_a_rows,
      configured: configured?.input_a_rows,
    },
    {
      key: 'output_rows',
      label: 'Output rows',
      value: active?.output_rows,
      configured: configured?.output_rows,
    },
  ]
})
// The delta is only meaningful against the configured link, so it is shown for
// the trial result and omitted for the configured result itself.
const showDeltas = computed(() => side.value === 'trial' && trial.value?.status === 'complete')

// Explain what the shown join does with source rows that find no match, so the
// effect is clear without a second comparison table.
const joinNote = computed<string | null>(() => {
  const isTrial = side.value === 'trial'
  const settings = isTrial ? trial.value?.settings : result.value?.baseline?.settings
  const joinType = settings?.join_type.effective ?? null
  if (!joinType) {
    return null
  }
  const effect = joinType === 'left' ? 'keeps' : 'removes'
  return `The ${isTrial ? 'trial' : 'configured'} ${joinType} join ${effect} unmatched source rows.`
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
// Paging is bounded by the browsable rows, so a result larger than the browse
// cap does not offer empty pages past the cap.
const pageCount = computed(() => {
  const browsableRows = rowBrowseCap.value > 0 ? Math.min(rowTotalCount.value, rowBrowseCap.value) : rowTotalCount.value
  return Math.max(1, Math.ceil(browsableRows / pageSize.value))
})
watch([side, group, pageSize, trial], () => {
  page.value = 1
})
// A result that just arrived is the one the operator asked for, so show it
// without requiring a second switch. Clearing the trial returns to the configured link.
watch(trial, (value) => {
  side.value = value ? 'trial' : 'baseline'
})
// Headers are not sortable: the backend returns a fixed bounded order from its
// row route, so sorting one page would only reorder the rows already returned.
const exceptionColumns = computed<TroubleshooterGridColumn[]>(() => [
  { field: 'input_position', header: 'Input row', width: 110 },
  ...activeKeyNames.value.map((key, index) => ({ field: `key-${index}`, header: `A key: ${key}` })),
  { field: 'remote_match_count', header: 'Remote matches', align: 'right' as const, width: 150 },
  { field: 'output_row_contribution', header: 'Output rows', align: 'right' as const, width: 130 },
])

// Grid rows are built from the loaded page; the row index is one-based so it
// reads as an input row number rather than a zero-based position.
const gridRows = computed<Record<string, unknown>[]>(() =>
  rows.value.map((row) => {
    const record: Record<string, unknown> = {
      input_position: row.input_position + 1,
      remote_match_count: row.remote_match_count,
      output_row_contribution: row.output_row_contribution,
    }
    activeKeyNames.value.forEach((_, index) => {
      record[`key-${index}`] = formatKeyValue(row.key_values[index])
    })
    return record
  })
)

const joinTypeOptions = [
  { title: 'Inherit configured', value: null },
  { title: 'Inner', value: 'inner' },
  { title: 'Left', value: 'left' },
]
const nullOptionItems = [
  { title: 'Inherit configured', value: null },
  { title: 'Yes', value: true },
  { title: 'No', value: false },
]
const pageSizeOptions = [
  { title: '25', value: 25 },
  { title: '50', value: 50 },
  { title: '100', value: 100 },
  { title: '200', value: 200 },
  // The limit matches the browse cap, so All reads every retained row at once.
  { title: 'All', value: EXCEPTION_ROW_PAGE_LIMIT },
]

watch(
  () => [props.modelValue, props.message] as const,
  async ([isOpen, message]) => {
    integrityRelationship.value = null
    if (!isOpen) {
      stopDialogResize()
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

onBeforeUnmount(stopDialogResize)

function startDialogResize(event: PointerEvent, direction: DialogResizeDirection): void {
  const card = getDialogCard(event.currentTarget)
  if (event.button !== 0 || !card) {
    return
  }

  const bounds = card.getBoundingClientRect()
  const size = constrainDialogSize(dialogSize.value?.width ?? bounds.width, dialogSize.value?.height ?? bounds.height)
  dialogSize.value = size
  resizeStart.value = {
    direction,
    clientX: event.clientX,
    clientY: event.clientY,
    ...size,
  }

  window.addEventListener('pointermove', resizeDialog)
  window.addEventListener('pointerup', stopDialogResize)
  window.addEventListener('pointercancel', stopDialogResize)
  event.preventDefault()
  event.stopPropagation()
}

function resizeDialog(event: PointerEvent): void {
  const start = resizeStart.value
  if (!start) {
    return
  }

  const widthDelta = event.clientX - start.clientX
  const heightDelta = event.clientY - start.clientY
  // The dialog stays centered, so double the pointer delta to keep the dragged edge under the pointer.
  const width = start.width + (start.direction !== 'height' ? widthDelta * 2 : 0)
  const height = start.height + (start.direction !== 'width' ? heightDelta * 2 : 0)
  dialogSize.value = constrainDialogSize(width, height)
}

function resizeDialogWithKeyboard(event: KeyboardEvent, direction: DialogResizeDirection): void {
  const bounds = getDialogCard(event.currentTarget)?.getBoundingClientRect()
  const size =
    dialogSize.value ??
    (bounds
      ? {
          width: bounds.width,
          height: bounds.height,
        }
      : null)
  if (!size) {
    return
  }

  const step = event.shiftKey ? 48 : 24
  const widthDelta = event.key === 'ArrowRight' ? step : event.key === 'ArrowLeft' ? -step : 0
  const heightDelta = event.key === 'ArrowDown' ? step : event.key === 'ArrowUp' ? -step : 0
  const changeWidth = direction !== 'height' ? widthDelta : 0
  const changeHeight = direction !== 'width' ? heightDelta : 0
  if (changeWidth === 0 && changeHeight === 0) {
    return
  }

  event.preventDefault()
  dialogSize.value = constrainDialogSize(size.width + changeWidth, size.height + changeHeight)
}

function getDialogCard(target: EventTarget | null): HTMLElement | null {
  if (!(target instanceof HTMLElement)) {
    return null
  }

  const card = target.closest('.link-troubleshooter-dialog-card')
  return card instanceof HTMLElement ? card : null
}

function constrainDialogSize(width: number, height: number): { width: number; height: number } {
  const maxWidth = Math.max(280, window.innerWidth - 32)
  const maxHeight = Math.max(240, window.innerHeight - 32)
  const minWidth = Math.min(480, maxWidth)
  const minHeight = Math.min(320, maxHeight)

  return {
    width: Math.round(Math.min(maxWidth, Math.max(minWidth, width))),
    height: Math.round(Math.min(maxHeight, Math.max(minHeight, height))),
  }
}

function stopDialogResize(): void {
  window.removeEventListener('pointermove', resizeDialog)
  window.removeEventListener('pointerup', stopDialogResize)
  window.removeEventListener('pointercancel', stopDialogResize)
  resizeStart.value = null
}

function close(): void {
  stopDialogResize()
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

function selectSide(value: LinkExceptionSide): void {
  side.value = value
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

function formatDelta(configured: number | null | undefined, trialValue: number | null | undefined): string {
  if (configured === null || configured === undefined || trialValue === null || trialValue === undefined) {
    return '—'
  }

  const delta = trialValue - configured
  return delta > 0 ? `+${delta.toLocaleString()}` : delta.toLocaleString()
}
</script>

<style scoped>
.link-troubleshooter-dialog-card {
  position: relative;
}

.link-troubleshooter-dialog-card--resizing {
  user-select: none;
}

.link-troubleshooter-resize-handle {
  position: absolute;
  z-index: 5;
  border: 0;
  padding: 0;
  background: transparent;
}

.link-troubleshooter-resize-handle:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}

.link-troubleshooter-resize-handle--right {
  top: 0;
  right: 0;
  width: 10px;
  height: 100%;
  cursor: ew-resize;
}

.link-troubleshooter-resize-handle--bottom {
  bottom: 0;
  left: 0;
  width: 100%;
  height: 10px;
  cursor: ns-resize;
}

.link-troubleshooter-resize-handle--corner {
  right: 0;
  bottom: 0;
  width: 20px;
  height: 20px;
  cursor: nwse-resize;
}

.link-troubleshooter-resize-handle--corner::after {
  position: absolute;
  right: 2px;
  bottom: 2px;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 0 0 12px 12px;
  border-color: transparent transparent rgba(var(--v-theme-on-surface), 0.3) transparent;
  content: '';
}

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

.link-troubleshooter-heading {
  min-width: 0;
}

.link-result-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
}

.link-result-stat-value {
  font-size: 1.75rem;
  font-weight: 600;
  line-height: 1.2;
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
