<template>
  <div class="pa-4">
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

    <v-alert type="info" variant="tonal" density="comfortable" class="mt-4">
      <div class="text-body-2 font-weight-medium mb-2">Filter "stages" follow this processing pipeline:</div>
      <ol class="sr-only">
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
      <div class="filter-flow-diagram" aria-hidden="true">
        <svg
          viewBox="0 0 1100 220"
          xmlns="http://www.w3.org/2000/svg"
          role="img"
          aria-label="Horizontal processing flow with filter hook markers"
          preserveAspectRatio="xMidYMid meet"
        >
        <defs>
          <!-- Smaller arrowheads -->
          <marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M 0 0 L 7 3.5 L 0 7 z" fill="#667085"/>
          </marker>

          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#000000" flood-opacity="0.12"/>
          </filter>
        </defs>

        <rect class="bg" x="0" y="0" width="1100" height="220" rx="24"/>

        <!-- Main nodes -->
        <rect class="node" x="40"  y="120" width="130" height="44" rx="14"/>
        <text class="nodeText" x="105" y="142">extract</text>

        <rect class="node" x="220" y="120" width="150" height="44" rx="14"/>
        <text class="nodeText" x="295" y="142">deduplicate</text>

        <rect class="node" x="420" y="120" width="110" height="44" rx="14"/>
        <text class="nodeText" x="475" y="142">link</text>

        <rect class="node" x="580" y="120" width="120" height="44" rx="14"/>
        <text class="nodeText" x="640" y="142">unnest</text>

        <rect class="node" x="750" y="120" width="110" height="44" rx="14"/>
        <text class="nodeText" x="805" y="142">relink</text>

        <rect class="node" x="910" y="120" width="130" height="44" rx="14"/>
        <text class="nodeText" x="975" y="142">cleanup</text>

        <!-- Main flow arrows -->
        <line class="flow" x1="170" y1="142" x2="220" y2="142"/>
        <line class="flow" x1="370" y1="142" x2="420" y2="142"/>
        <line class="flow" x1="530" y1="142" x2="580" y2="142"/>
        <line class="flow" x1="700" y1="142" x2="750" y2="142"/>
        <line class="flow" x1="860" y1="142" x2="910" y2="142"/>

        <!-- Hook labels -->
        <text class="hookText" x="195" y="52">after extract</text>
        <text class="hookText" x="555" y="52">after link</text>
        <text class="hookText" x="725" y="52">after unnest</text>

        <!-- Hook arrows -->
        <line class="hook" x1="195" y1="64" x2="195" y2="118"/>
        <line class="hook" x1="555" y1="64" x2="555" y2="118"/>
        <line class="hook" x1="725" y1="64" x2="725" y2="118"/>
        </svg>
      </div>
      <div class="text-body-2">
        Use <strong>Extract</strong> for source columns, <strong>After Link</strong> for linked columns, and
        <strong>After Unnest</strong> for columns created by unnesting such as <code>value_name</code>.
      </div>
    </v-alert>
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
  { title: 'After Extract', value: 'extract' },
  { title: 'After Link', value: 'after_link' },
  { title: 'After Unnest', value: 'after_unnest' },
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

<style scoped>
.filter-flow-diagram {
  width: 100%;
  overflow-x: auto;
  margin-bottom: 12px;
}

.filter-flow-diagram svg {
  display: block;
  width: 100%;
  height: auto;
  min-width: 640px;
}

.filter-flow-diagram .bg {
  fill: #f8fafc;
}

.filter-flow-diagram .node {
  fill: #ffffff;
  stroke: #cbd5e1;
  stroke-width: 1.5;
  filter: url(#shadow);
}

.filter-flow-diagram .nodeText {
  font: 600 15px Inter, Segoe UI, Roboto, Arial, sans-serif;
  fill: #1e293b;
  text-anchor: middle;
  dominant-baseline: middle;
}

.filter-flow-diagram .flow {
  stroke: #667085;
  stroke-width: 2.2;
  fill: none;
  marker-end: url(#arrow);
}

.filter-flow-diagram .hook {
  stroke: #0f766e;
  stroke-width: 2;
  fill: none;
  marker-end: url(#arrow);
}

.filter-flow-diagram .hookText {
  font: 600 13px Inter, Segoe UI, Roboto, Arial, sans-serif;
  fill: #0f766e;
  text-anchor: middle;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
