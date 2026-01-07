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
    // Convert extra_columns array back to object
    const extraColumnsObj =
      newValue.length > 0
        ? Object.fromEntries(newValue.filter((item) => item.column).map((item) => [item.column, item.source || null]))
        : undefined

    emit('update:modelValue', extraColumnsObj)
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      extraColumns.value = Object.entries(newValue).map(([column, source]) => ({
        column,
        source: source || null,
      }))
    }
  },
  { deep: true }
)
</script>
