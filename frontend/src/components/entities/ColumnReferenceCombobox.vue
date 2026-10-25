<template>
  <div class="column-reference-combobox">
    <v-combobox
      ref="combobox"
      v-bind="attrs"
      :model-value="modelValue"
      :items="itemsForSearch"
      :search="search"
      :disabled="disabled"
      :clear-on-select="!search.trim().startsWith('@value')"
      auto-select-first
      :loading="completionLoading"
      multiple
      chips
      closable-chips
      @update:model-value="handleModelUpdate"
      @update:search="handleSearchUpdate"
    >
      <template #chip="{ props: chipProps, item, index }">
        <v-chip v-bind="chipProps" size="small">
          <span>{{ chipText(item) }}</span>
          <template v-if="isSimpleColumnReference(chipText(item))" #append>
            <v-btn
              icon="mdi-eye-outline"
              size="x-small"
              variant="text"
              :disabled="disabled"
              :aria-label="`Inspect ${chipText(item)}`"
              @click.stop.prevent="inspect(chipText(item), index)"
            />
          </template>
        </v-chip>
      </template>
      <template #message>
        <slot name="message" />
      </template>
    </v-combobox>

    <v-btn
      v-if="!disabled"
      class="mt-1"
      size="x-small"
      variant="text"
      prepend-icon="mdi-at"
      data-testid="insert-reference"
      @click="beginReferenceEntry"
    >
      Insert reference
    </v-btn>

    <v-alert
      v-if="completionError"
      class="mt-2"
      type="error"
      variant="tonal"
      density="compact"
      data-testid="reference-completion-error"
    >
      {{ completionError }}
    </v-alert>

    <v-card
      v-if="inspectionLoading || inspection || inspectionError"
      class="mt-2 pa-2"
      variant="tonal"
      data-testid="reference-inspection"
      aria-live="polite"
    >
      <div v-if="inspectionDirective" class="text-caption font-weight-medium mb-1">
        {{ inspectionDirective }}
      </div>
      <v-progress-linear v-if="inspectionLoading" indeterminate color="primary" />
      <v-alert v-else-if="inspectionError" type="error" variant="tonal" density="compact">
        {{ inspectionError }}
      </v-alert>
      <template v-else-if="inspection?.status === 'resolved'">
        <ol v-if="inspection.columns?.length" class="column-reference-list">
          <li v-for="(column, index) in inspection.columns" :key="`${index}:${column}`">
            <span>{{ column }}</span>
            <div v-for="issue in issuesForColumn(column)" :key="`${issue.code}:${issue.message}`" class="mt-1">
              <v-chip
                size="x-small"
                class="mr-1"
                :color="issue.severity === 'error' ? 'error' : issue.severity === 'warning' ? 'warning' : 'info'"
              >
                {{ issue.severity }}
              </v-chip>
              <span class="text-caption">{{ issue.message }}</span>
            </div>
          </li>
        </ol>
        <div v-else class="text-caption">This reference returns no columns.</div>
        <v-alert v-if="validationLoading" type="info" variant="tonal" density="compact" class="mt-2">
          Checking current draft findings…
        </v-alert>
        <v-alert
          v-if="validationError"
          type="error"
          variant="tonal"
          density="compact"
          class="mt-2"
          data-testid="draft-validation-error"
        >
          Could not read current draft findings: {{ validationError }}
        </v-alert>
        <template v-if="canReplaceInspectedReference">
          <p class="text-caption mt-2 mb-1">
            Replacing this reference saves these column names as a snapshot. They will not follow later source changes.
          </p>
          <v-btn size="small" variant="tonal" data-testid="replace-reference" @click="replaceInspectedReference">
            Replace with columns
          </v-btn>
        </template>
      </template>
      <v-alert v-else-if="inspection" type="warning" variant="tonal" density="compact">
        {{ inspection.reason || 'This reference could not be resolved.' }}
      </v-alert>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, useAttrs, watch } from 'vue'
import type { ValidationError } from '@/types'
import type { ColumnReferenceContext } from '@/composables/useColumnReferences'
import { isSimpleColumnReference, useColumnReferences } from '@/composables/useColumnReferences'

defineOptions({ inheritAttrs: false })

interface Props {
  modelValue: string[]
  items: string[]
  projectName: string
  entityName: string
  originalEntityName?: string
  entityDraft: Record<string, unknown>
  editedFieldPath: string
  preferredEntity?: string
  disabled?: boolean
  validationIssues?: ValidationError[]
  validationLoading?: boolean
  validationError?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  originalEntityName: undefined,
  preferredEntity: undefined,
  disabled: false,
  validationIssues: () => [],
  validationLoading: false,
  validationError: null,
})

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
  'inspect-reference': []
  'replace-reference': [replacement: { fieldPath: string; before: string[]; after: string[] }]
}>()

const attrs = useAttrs()
const combobox = ref<{ focus?: () => void } | null>(null)
const search = ref('')
const pendingManualDirective = ref<string | null>(null)
const inspectionIndex = ref<number | null>(null)
const referenceState = useColumnReferences()

const context = computed<ColumnReferenceContext>(() => ({
  projectName: props.projectName,
  entityName: props.entityName,
  entityDraft: props.entityDraft,
  editedFieldPath: props.editedFieldPath,
  preferredEntity: props.preferredEntity,
  ...(props.originalEntityName && props.originalEntityName !== props.entityName
    ? { originalEntityName: props.originalEntityName }
    : {}),
}))

const contextKey = computed(() =>
  JSON.stringify([
    props.projectName,
    props.entityName,
    props.originalEntityName,
    props.editedFieldPath,
    props.preferredEntity,
    props.disabled,
    props.entityDraft,
  ])
)

const itemsForSearch = computed(() => {
  const ordinaryItems = props.items ?? []
  if (!search.value.trim().startsWith('@value')) return ordinaryItems
  return [...new Set([...ordinaryItems, ...referenceState.candidates.value])]
})

const {
  candidates,
  completionLoading,
  completionError,
  inspection,
  inspectionDirective,
  inspectionError,
  inspectionLoading,
} = referenceState

watch(
  contextKey,
  () => {
    referenceState.clear()
    inspectionIndex.value = null
    if (!props.disabled && search.value.trim().startsWith('@value')) {
      referenceState.scheduleCompletion(context.value, search.value)
    }
  },
  { flush: 'post' }
)

function normalizeValues(value: unknown): string[] {
  const values = Array.isArray(value) ? value : value == null || value === '' ? [] : [value]
  return values.map((item) => {
    if (typeof item === 'string') return item
    if (typeof item === 'object' && item !== null && 'value' in item) {
      return String((item as { value: unknown }).value)
    }
    return String(item)
  })
}

const canReplaceInspectedReference = computed(() => {
  const index = inspectionIndex.value
  return (
    !props.disabled &&
    !!props.editedFieldPath &&
    index !== null &&
    props.modelValue[index] === inspectionDirective.value &&
    isSimpleColumnReference(inspectionDirective.value ?? '') &&
    inspection?.value?.status === 'resolved'
  )
})

function issuesForColumn(column: string): ValidationError[] {
  return props.validationIssues.filter((issue) => issue.related_columns?.includes(column))
}

function isIncompleteReferenceEntry(value: string): boolean {
  return /^@value(?:\s*:\s*(?:entities(?:\.[A-Za-z0-9_-]+)?\.?)?)?$/.test(value.trim())
}

function chipText(item: unknown): string {
  if (typeof item === 'string') return item
  if (typeof item === 'object' && item !== null) {
    const record = item as Record<string, unknown>
    const value = record.value ?? record.raw ?? record.title
    if (typeof value === 'string') return value
  }
  return String(item ?? '')
}

function handleSearchUpdate(value: string | null): void {
  search.value = value ?? ''
  if (props.disabled) {
    referenceState.clear()
    return
  }

  const prefix = search.value.trim()
  if (prefix.startsWith('@value')) {
    referenceState.scheduleCompletion(context.value, prefix)
  } else if (pendingManualDirective.value) {
    referenceState.clearCompletion()
  } else {
    referenceState.clear()
  }
}

async function handleModelUpdate(value: unknown): Promise<void> {
  if (props.disabled) return
  const nextValues = normalizeValues(value)
  const addedValues = nextValues.filter((item) => !props.modelValue.includes(item))
  const incomplete = addedValues.find(isIncompleteReferenceEntry)

  if (incomplete) {
    search.value = incomplete
    await nextTick()
    handleSearchUpdate(incomplete)
    return
  }

  referenceState.clearInspection()
  inspectionIndex.value = null
  const manuallyEntered = addedValues.find((item) => isSimpleColumnReference(item) && !candidates.value.includes(item))
  search.value = ''
  pendingManualDirective.value = manuallyEntered ?? null
  emit('update:modelValue', nextValues)

  if (manuallyEntered) {
    await nextTick()
    if (props.modelValue.includes(manuallyEntered) && !props.disabled) {
      inspect(manuallyEntered, nextValues.lastIndexOf(manuallyEntered))
    }
    pendingManualDirective.value = null
  }
}

function inspect(directive: string, index: number): void {
  if (props.disabled || !isSimpleColumnReference(directive)) return
  inspectionIndex.value = index
  emit('inspect-reference')
  void referenceState.resolveReference(context.value, directive)
}

function replaceInspectedReference(): void {
  if (!canReplaceInspectedReference.value || inspectionIndex.value === null) return

  const before = [...props.modelValue]
  const after = [...before]
  after.splice(inspectionIndex.value, 1, ...(inspection.value?.columns ?? []))
  emit('update:modelValue', after)
  emit('replace-reference', { fieldPath: props.editedFieldPath, before, after: [...after] })
  inspectionIndex.value = null
  referenceState.clearInspection()
}

async function beginReferenceEntry(): Promise<void> {
  search.value = '@value'
  await nextTick()
  combobox.value?.focus?.()
  handleSearchUpdate(search.value)
}
</script>

<style scoped>
.column-reference-list {
  margin: 0;
  padding-left: 1.25rem;
}
</style>
