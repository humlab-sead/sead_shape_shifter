<template>
  <div class="pa-4">
    <div class="d-flex flex-wrap align-center ga-2 mb-4">
      <span class="text-caption text-medium-emphasis">Quick patterns:</span>
      <v-chip size="small" variant="outlined" color="primary" @click="insertExample('copy')">Copy</v-chip>
      <v-chip size="small" variant="outlined" color="primary" @click="insertExample('constant')">Constant</v-chip>
      <v-chip size="small" variant="outlined" color="primary" @click="insertExample('interpolation')">Interpolation</v-chip>
      <v-chip size="small" variant="outlined" color="primary" @click="insertExample('formula')">Formula</v-chip>
      <v-chip size="small" variant="outlined" color="primary" @click="insertExample('escaped')">Literal =</v-chip>
    </div>

    <!-- Header Row -->
    <v-row dense class="mb-2">
      <v-col cols="12" md="5">
        <div class="text-caption text-medium-emphasis font-weight-medium">New Column Name</div>
      </v-col>
      <v-col cols="12" md="6">
        <div class="text-caption text-medium-emphasis font-weight-medium">Expression (or leave empty for null)</div>
      </v-col>
      <v-col cols="12" md="1">
        <div class="text-caption text-medium-emphasis font-weight-medium"></div>
      </v-col>
    </v-row>

    <v-list density="compact" class="py-0">
      <v-list-item v-for="(item, index) in extraColumns" :key="index" class="px-0 py-1">
        <v-row dense>
          <v-col cols="12" md="5">
            <v-text-field
              v-model="item.column"
              variant="outlined"
              density="compact"
              placeholder="e.g., new_column"
              :error-messages="columnMessages(index)"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="item.source"
              variant="outlined"
              density="compact"
              placeholder="e.g., existing_column"
              clearable
              :hint="expressionHint(index)"
              persistent-hint
              :messages="expressionMessages(index)"
            />
          </v-col>
          <v-col cols="12" md="1" class="d-flex align-center">
            <v-btn
              icon="mdi-delete"
              variant="text"
              size="small"
              color="error"
              @click="handleRemoveExtraColumn(index)"
            />
          </v-col>
          <v-col cols="12">
            <div v-if="rowSuggestions(index).length" class="d-flex flex-wrap align-center ga-2 mt-1 mb-2">
              <span class="text-caption text-medium-emphasis">Suggestions:</span>
              <v-chip
                v-for="suggestion in rowSuggestions(index).slice(0, maxSuggestionsPerRow)"
                :key="`${index}-${suggestion.category}-${suggestion.value}`"
                size="x-small"
                variant="outlined"
                :color="suggestionColor(suggestion.category)"
                @click="applySuggestion(index, suggestion)"
              >
                {{ suggestion.label }}
              </v-chip>
            </div>
          </v-col>
        </v-row>
      </v-list-item>
    </v-list>

    <v-btn variant="outlined" prepend-icon="mdi-plus" size="small" block @click="handleAddExtraColumn">
      Add Extra Column
    </v-btn>

    <v-alert
      type="info"
      variant="tonal"
      density="compact"
      class="mt-3 text-caption"
    >
      <strong>Extra columns</strong> are the canonical way to add lightweight derived values to an entity.
      Use them for copies, constants, interpolation, and small formulas:
      <ul class="mt-2 mb-0 pl-4">
        <li><strong>Copy:</strong> <code>existing_column</code> - Reuse a source column under a new name</li>
        <li><strong>Constant:</strong> <code>"literal_value"</code>, <code>123</code>, or leave empty for null</li>
        <li><strong>Interpolation:</strong> <code>"{first_name} {last_name}"</code> - Build a label from multiple columns</li>
        <li><strong>Formula:</strong> <code>=concat(upper(code), '-', trim(name))</code> - Apply a lightweight transformation</li>
        <li><strong>Null values:</strong> Leave empty for null</li>
      </ul>
      Interpolated strings are null-safe and can reference FK columns added during linking.
      If you need a literal value that starts with <code>=</code>, escape it as <code>==value</code>.
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import {
  applySuggestionToExpression,
  getExtraColumnDiagnostics,
  getExtraColumnSuggestions,
  type ExtraColumnSuggestion,
} from './extraColumnsEditorUtils'

interface ExtraColumnConfig {
  column: string
  source: string | null
}

interface Props {
  modelValue?: Record<string, string | null>
  availableColumns?: string[]
  reservedNames?: string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, string | null> | undefined]
}>()

function toModelValue(value: ExtraColumnConfig[]): Record<string, string | null> | undefined {
  const entries = value
    .map((item) => ({ column: item.column?.trim() || '', source: item.source ?? null }))
    .filter((item) => item.column.length > 0)
    .map((item) => [item.column, item.source] as const)

  if (entries.length === 0) return undefined
  return Object.fromEntries(entries)
}

// Convert extra_columns from object to array for editing
const extraColumns = ref<ExtraColumnConfig[]>(
  props.modelValue
    ? Object.entries(props.modelValue).map(([column, source]) => ({
        column,
        source: source || null,
      }))
    : []
)

function handleAddExtraColumn() {
  extraColumns.value.push({
    column: '',
    source: null,
  })
}

function handleRemoveExtraColumn(index: number) {
  extraColumns.value.splice(index, 1)
}

const examplePatterns: Record<'copy' | 'constant' | 'interpolation' | 'formula' | 'escaped', ExtraColumnConfig> = {
  copy: { column: 'copied_value', source: 'existing_column' },
  constant: { column: 'record_type', source: 'sample' },
  interpolation: { column: 'display_label', source: '{first_name} {last_name}' },
  formula: { column: 'normalized_code', source: '=concat(upper(code), "-", trim(name))' },
  escaped: { column: 'literal_equals', source: '==SEAD' },
}

const maxSuggestionsPerRow = 8

const rowDiagnostics = computed(() =>
  extraColumns.value.map((_, index) =>
    getExtraColumnDiagnostics(extraColumns.value, index, {
      availableColumns: props.availableColumns ?? [],
      reservedNames: props.reservedNames ?? [],
    })
  )
)

const suggestionsByRow = computed(() =>
  extraColumns.value.map((item) => getExtraColumnSuggestions(item.source, props.availableColumns ?? []))
)

function insertExample(kind: keyof typeof examplePatterns) {
  extraColumns.value.push({ ...examplePatterns[kind] })
}

function rowSuggestions(index: number): ExtraColumnSuggestion[] {
  return suggestionsByRow.value[index] ?? []
}

function applySuggestion(index: number, suggestion: ExtraColumnSuggestion) {
  const row = extraColumns.value[index]
  if (!row) return

  row.source = applySuggestionToExpression(row.source, suggestion, props.availableColumns ?? [])
}

function suggestionColor(category: ExtraColumnSuggestion['category']): string {
  if (category === 'function') return 'primary'
  if (category === 'column') return 'success'
  return 'info'
}

function columnMessages(index: number): string[] {
  return rowDiagnostics.value[index]
    ?.filter((diagnostic) => diagnostic.severity === 'error')
    .map((diagnostic) => diagnostic.message) ?? []
}

function expressionHint(index: number): string {
  const diagnostics = rowDiagnostics.value[index] ?? []
  const info = diagnostics.find((diagnostic) => diagnostic.severity === 'info')
  return info?.message ?? 'Empty expression stores null.'
}

function expressionMessages(index: number): string[] {
  return rowDiagnostics.value[index]
    ?.filter((diagnostic) => diagnostic.severity !== 'error')
    .map((diagnostic) => diagnostic.message) ?? []
}

watch(
  extraColumns,
  (newValue) => {
    emit('update:modelValue', toModelValue(newValue))
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  (newValue) => {
    // Avoid overwriting local edits if this prop update matches what we'd emit ourselves.
    const currentAsModel = toModelValue(extraColumns.value)
    if (JSON.stringify(newValue) === JSON.stringify(currentAsModel)) {
      return
    }

    extraColumns.value = newValue
      ? Object.entries(newValue).map(([column, source]) => ({
          column,
          source: source || null,
        }))
      : []
  },
  { deep: true }
)
</script>

<style scoped>
/* Component-specific dense input styling */
:deep(.v-field__input) {
  min-height: max(20px, 1.rem + var(--v-field-input-padding-top) + var(--v-field-input-padding-bottom)) !important;
}

:deep(.v-field__field) {
  --v-field-padding-top: 8px;
  --v-field-padding-bottom: 8px;
}

/* Reduce spacing between fields */
:deep(.v-input) {
  margin-bottom: 12px;
}
</style>
