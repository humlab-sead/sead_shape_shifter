<template>
  <div class="pa-4">
    <v-alert type="info" variant="tonal" density="comfortable" class="mb-4">
      <div class="text-body-2 font-weight-medium mb-2">Filter stages follow the normalization flow:</div>
      <ol class="text-body-2 pl-5 mb-2">
        <li>extract</li>
        <li>filter - after extract</li>
        <li>deduplicate</li>
        <li>link</li>
        <li>filter - after link</li>
        <li>unnest</li>
        <li>filter - after unnest</li>
        <li>relink</li>
        <li>later cleanup</li>
      </ol>
      <div class="text-body-2">
        Use <strong>Extract</strong> for source columns, <strong>After Link</strong> for linked columns, and
        <strong>After Unnest</strong> for columns created by unnesting such as <code>value_name</code>.
      </div>
    </v-alert>

    <v-list>
      <v-list-item v-for="(filter, index) in filters" :key="index" class="px-0 mb-2">
        <v-card variant="outlined">
          <v-card-text>
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="d-flex ga-2 flex-wrap flex-grow-1">
                <v-select
                  v-model="filter.type"
                  :items="filterTypes"
                  label="Filter Type"
                  variant="outlined"
                  density="compact"
                  style="max-width: 250px"
                  @update:model-value="handleFilterTypeChange(index)"
                />
                <v-select
                  :model-value="getFilterStage(filter)"
                  :items="stageOptions"
                  label="Stage"
                  variant="outlined"
                  density="compact"
                  style="max-width: 250px"
                  @update:model-value="setFilterStage(index, $event)"
                />
              </div>
              <v-btn icon="mdi-delete" variant="text" size="small" color="error" @click="handleRemoveFilter(index)" />
            </div>

            <!-- Dynamic fields based on filter schema -->
            <v-row dense v-if="filter.type">
              <v-col
                v-for="field in getFieldsForFilter(filter.type)"
                :key="field.name"
                cols="12"
                :md="getColumnWidth(filter.type)"
              >
                <!-- Entity autocomplete -->
                <v-autocomplete
                  v-if="field.type === 'entity'"
                  v-model="filter[field.name]"
                  :items="availableEntities"
                  :label="field.description || field.name"
                  :placeholder="field.placeholder"
                  :rules="field.required ? [required] : []"
                  variant="outlined"
                  density="compact"
                />

                <!-- String/Column text field -->
                <v-text-field
                  v-else-if="field.type === 'string' || field.type === 'column'"
                  v-model="filter[field.name]"
                  :label="field.description || field.name"
                  :placeholder="field.placeholder"
                  :rules="field.required ? [required] : []"
                  variant="outlined"
                  density="compact"
                />

                <!-- Boolean checkbox -->
                <v-checkbox
                  v-else-if="field.type === 'boolean'"
                  v-model="filter[field.name]"
                  :label="field.description || field.name"
                  density="compact"
                />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-list-item>
    </v-list>

    <v-btn variant="outlined" prepend-icon="mdi-plus" size="small" block @click="handleAddFilter">Add Filter</v-btn>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useFilterSchema } from '@/composables/useFilterSchema'
import type { FilterConfig, FilterStage } from '@/types/filter-schema'

interface Props {
  modelValue?: FilterConfig[]
  availableEntities?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  availableEntities: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: FilterConfig[] | undefined]
}>()

const { loadFilterSchemas, getFilterSchema, getFilterTypes } = useFilterSchema()

const filters = ref<FilterConfig[]>(props.modelValue || [])
const filterTypes = ref<Array<{ title: string; value: string }>>([])
const stageOptions: Array<{ title: string; value: FilterStage }> = [
  { title: 'Extract (after extract)', value: 'extract' },
  { title: 'After Link (after link)', value: 'after_link' },
  { title: 'After Unnest (after unnest)', value: 'after_unnest' },
]

// Validation rule
const required = (v: any) => !!v || 'This field is required'

onMounted(async () => {
  await loadFilterSchemas()
  filterTypes.value = getFilterTypes()
})

function getFieldsForFilter(filterType: string) {
  const schema = getFilterSchema(filterType)
  return schema?.fields || []
}

function getColumnWidth(filterType: string): number {
  // Distribute fields across 12 columns
  const fieldsCount = getFieldsForFilter(filterType).length
  if (fieldsCount === 1) return 12
  if (fieldsCount === 2) return 6
  if (fieldsCount === 3) return 4
  return 3 // 4+ fields get 3 columns each
}

function handleFilterTypeChange(index: number) {
  // Reset filter config when type changes, keeping only the type
  const filter = filters.value[index]
  if (!filter) {
    return
  }

  const currentType = filter.type
  const currentStage = filter.stage
  const schema = getFilterSchema(currentType)

  const newConfig: FilterConfig = { type: currentType }
  if (currentStage) {
    newConfig.stage = currentStage
  }

  // Initialize fields with defaults
  schema?.fields.forEach((field) => {
    if (field.default !== undefined) {
      newConfig[field.name] = field.default
    }
  })

  filters.value[index] = newConfig
}

function getFilterStage(filter: FilterConfig): FilterStage {
  return (filter.stage as FilterStage | undefined) || 'extract'
}

function setFilterStage(index: number, stage: FilterStage) {
  const filter = filters.value[index]
  if (!filter) {
    return
  }

  if (stage === 'extract') {
    delete filter.stage
    return
  }

  filter.stage = stage
}

function handleAddFilter() {
  const firstFilterType = filterTypes.value[0]?.value || 'query'
  const schema = getFilterSchema(firstFilterType)

  const newFilter: FilterConfig = { type: firstFilterType }

  // Initialize with defaults
  schema?.fields.forEach((field) => {
    if (field.default !== undefined) {
      newFilter[field.name] = field.default
    }
  })

  filters.value.push(newFilter)
}

function handleRemoveFilter(index: number) {
  filters.value.splice(index, 1)
}

watch(
  filters,
  (newValue) => {
    emit('update:modelValue', newValue.length > 0 ? newValue : undefined)
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      filters.value = newValue
    }
  },
  { deep: true }
)
</script>
