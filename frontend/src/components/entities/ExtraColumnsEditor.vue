<template>
  <div class="pa-4">
    <v-list>
      <v-list-item v-for="(item, index) in extraColumns" :key="index" class="px-0 mb-2">
        <v-card variant="outlined">
          <v-card-text>
            <v-row dense>
              <v-col cols="12" md="5">
                <v-text-field
                  v-model="item.column"
                  label="New Column Name"
                  variant="outlined"
                  density="compact"
                  placeholder="e.g., new_column"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="item.source"
                  label="Source Column (or leave empty for null)"
                  variant="outlined"
                  density="compact"
                  placeholder="e.g., existing_column"
                  clearable
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
          </v-card-text>
        </v-card>
      </v-list-item>
    </v-list>

    <v-btn variant="outlined" prepend-icon="mdi-plus" size="small" block @click="handleAddExtraColumn">
      Add Extra Column
    </v-btn>
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
