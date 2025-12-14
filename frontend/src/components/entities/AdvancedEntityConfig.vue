<template>
  <v-expansion-panels variant="accordion" multiple>
    <!-- Filters Section -->
    <v-expansion-panel>
      <v-expansion-panel-title>
        <v-icon icon="mdi-filter" class="mr-2" />
        Filters
        <v-chip v-if="filters.length > 0" size="small" class="ml-2">
          {{ filters.length }}
        </v-chip>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <v-list>
          <v-list-item
            v-for="(filter, index) in filters"
            :key="index"
            class="px-0 mb-2"
          >
            <v-card variant="outlined">
              <v-card-text>
                <div class="d-flex align-center justify-space-between mb-2">
                  <v-select
                    v-model="filter.type"
                    :items="filterTypes"
                    label="Filter Type"
                    variant="outlined"
                    density="compact"
                    style="max-width: 200px"
                  />
                  <v-btn
                    icon="mdi-delete"
                    variant="text"
                    size="small"
                    color="error"
                    @click="handleRemoveFilter(index)"
                  />
                </div>

                <v-row dense v-if="filter.type === 'exists_in'">
                  <v-col cols="12" md="4">
                    <v-autocomplete
                      v-model="filter.entity"
                      :items="availableEntities"
                      label="Entity"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-text-field
                      v-model="filter.column"
                      label="Column"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-text-field
                      v-model="filter.remote_column"
                      label="Remote Column"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-list-item>
        </v-list>

        <v-btn
          variant="outlined"
          prepend-icon="mdi-plus"
          size="small"
          block
          @click="handleAddFilter"
        >
          Add Filter
        </v-btn>
      </v-expansion-panel-text>
    </v-expansion-panel>

    <!-- Unnest Section -->
    <v-expansion-panel>
      <v-expansion-panel-title>
        <v-icon icon="mdi-table-pivot" class="mr-2" />
        Unnest Configuration
        <v-chip v-if="unnest" size="small" color="success" class="ml-2">
          Enabled
        </v-chip>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <v-switch
          v-model="unnestEnabled"
          label="Enable Unnest"
          density="compact"
          hide-details
          class="mb-4"
        />

        <template v-if="unnestEnabled">
          <v-combobox
            v-model="unnest.id_vars"
            label="ID Variables"
            hint="Columns to keep as-is"
            persistent-hint
            chips
            multiple
            variant="outlined"
            density="compact"
            class="mb-4"
          />

          <v-combobox
            v-model="unnest.value_vars"
            label="Value Variables"
            hint="Columns to unpivot"
            persistent-hint
            chips
            multiple
            variant="outlined"
            density="compact"
            class="mb-4"
          />

          <v-text-field
            v-model="unnest.var_name"
            label="Variable Name Column"
            hint="Name for the new column containing variable names"
            persistent-hint
            variant="outlined"
            density="compact"
            class="mb-4"
          />

          <v-text-field
            v-model="unnest.value_name"
            label="Value Name Column"
            hint="Name for the new column containing values"
            persistent-hint
            variant="outlined"
            density="compact"
          />
        </template>
      </v-expansion-panel-text>
    </v-expansion-panel>

    <!-- Append Section -->
    <v-expansion-panel>
      <v-expansion-panel-title>
        <v-icon icon="mdi-table-row-plus-after" class="mr-2" />
        Append Data
        <v-chip v-if="append.length > 0" size="small" class="ml-2">
          {{ append.length }}
        </v-chip>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <v-list>
          <v-list-item
            v-for="(item, index) in append"
            :key="index"
            class="px-0 mb-2"
          >
            <v-card variant="outlined">
              <v-card-text>
                <div class="d-flex align-center justify-space-between mb-2">
                  <v-select
                    v-model="item.type"
                    :items="appendTypes"
                    label="Append Type"
                    variant="outlined"
                    density="compact"
                    style="max-width: 200px"
                  />
                  <v-btn
                    icon="mdi-delete"
                    variant="text"
                    size="small"
                    color="error"
                    @click="handleRemoveAppend(index)"
                  />
                </div>

                <v-textarea
                  v-if="item.type === 'fixed'"
                  v-model="item.valuesText"
                  label="Values (JSON Array)"
                  hint='Example: [["value1", "value2"], ["value3", "value4"]]'
                  persistent-hint
                  variant="outlined"
                  rows="3"
                />

                <template v-else-if="item.type === 'sql'">
                  <v-text-field
                    v-model="item.data_source"
                    label="Data Source"
                    variant="outlined"
                    density="compact"
                    class="mb-2"
                  />
                  <v-textarea
                    v-model="item.query"
                    label="SQL Query"
                    variant="outlined"
                    rows="4"
                  />
                </template>
              </v-card-text>
            </v-card>
          </v-list-item>
        </v-list>

        <v-btn
          variant="outlined"
          prepend-icon="mdi-plus"
          size="small"
          block
          @click="handleAddAppend"
        >
          Add Append
        </v-btn>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface FilterConfig {
  type: string
  entity?: string
  column?: string
  remote_column?: string
}

interface UnnestConfig {
  id_vars: string[]
  value_vars: string[]
  var_name: string
  value_name: string
}

interface AppendConfig {
  type: 'fixed' | 'sql'
  values?: any[][]
  valuesText?: string
  data_source?: string
  query?: string
}

interface Props {
  modelValue: {
    filters?: FilterConfig[]
    unnest?: UnnestConfig | null
    append?: AppendConfig[]
  }
  availableEntities?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  availableEntities: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: any]
}>()

// Local state
const filters = ref<FilterConfig[]>(props.modelValue.filters || [])
const unnest = ref<UnnestConfig>(
  props.modelValue.unnest || {
    id_vars: [],
    value_vars: [],
    var_name: '',
    value_name: '',
  }
)
const unnestEnabled = ref(!!props.modelValue.unnest)
const append = ref<AppendConfig[]>(props.modelValue.append || [])

const filterTypes = [
  { title: 'Exists In', value: 'exists_in' },
]

const appendTypes = [
  { title: 'Fixed Values', value: 'fixed' },
  { title: 'SQL Query', value: 'sql' },
]

// Computed
const configValue = computed(() => ({
  filters: filters.value.length > 0 ? filters.value : undefined,
  unnest: unnestEnabled.value ? unnest.value : null,
  append: append.value.length > 0 ? append.value : undefined,
}))

// Methods
function handleAddFilter() {
  filters.value.push({
    type: 'exists_in',
    entity: '',
    column: '',
    remote_column: '',
  })
}

function handleRemoveFilter(index: number) {
  filters.value.splice(index, 1)
}

function handleAddAppend() {
  append.value.push({
    type: 'fixed',
    valuesText: '[]',
  })
}

function handleRemoveAppend(index: number) {
  append.value.splice(index, 1)
}

// Watch for changes and emit
watch(
  [filters, unnest, unnestEnabled, append],
  () => {
    emit('update:modelValue', configValue.value)
  },
  { deep: true }
)

// Sync with prop changes
watch(
  () => props.modelValue,
  (newValue) => {
    filters.value = newValue.filters || []
    unnest.value = newValue.unnest || {
      id_vars: [],
      value_vars: [],
      var_name: '',
      value_name: '',
    }
    unnestEnabled.value = !!newValue.unnest
    append.value = newValue.append || []
  }
)
</script>
