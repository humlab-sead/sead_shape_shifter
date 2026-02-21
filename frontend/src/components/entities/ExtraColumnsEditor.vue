<template>
  <div class="pa-4">
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
              hide-details
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="item.source"
              variant="outlined"
              density="compact"
              placeholder="e.g., existing_column"
              clearable
              hide-details
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
      <strong>Extra columns</strong> allow you to add new columns to the output entity using:
      <ul class="mt-2 mb-0 pl-4">
        <li><strong>Template strings:</strong> <code>"{first_name} {last_name}"</code> - Combine multiple columns</li>
        <li><strong>Column copy:</strong> <code>existing_column</code> - Copy values from a source column</li>
        <li><strong>Constants:</strong> <code>"literal_value"</code> or <code>123</code> - Set fixed values</li>
        <li><strong>Null values:</strong> Leave empty for null</li>
      </ul>
      Template strings are null-safe and can reference FK columns added during linking.
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface ExtraColumnConfig {
  column: string
  source: string | null
}

interface Props {
  modelValue?: Record<string, string | null>
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
