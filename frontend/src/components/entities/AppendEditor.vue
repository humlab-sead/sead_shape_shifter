<template>
  <div class="pa-4">
    <v-list>
      <v-list-item v-for="(item, index) in append" :key="index" class="px-0 mb-2">
        <v-card variant="outlined">
          <v-card-text>
            <!-- Header: Type selector + Delete button -->
            <div class="d-flex align-center justify-space-between mb-3">
              <v-select
                v-model="item.type"
                :items="appendTypes"
                label="Append Type"
                variant="outlined"
                density="compact"
                style="max-width: 250px"
              />
              <v-btn icon="mdi-delete" variant="text" size="small" color="error" @click="handleRemoveAppend(index)" />
            </div>

            <!-- Fixed Values Type -->
            <template v-if="item.appendType === 'fixed'">
              <v-textarea
                v-model="item.valuesText"
                label="Values (JSON Array)"
                hint='Example: [["value1", "value2"], ["value3", "value4"]]'
                persistent-hint
                variant="outlined"
                rows="3"
              />
            </template>

            <!-- SQL Query Type -->
            <template v-else-if="item.appendType === 'sql'">
              <v-text-field
                v-model="item.data_source"
                label="Data Source"
                variant="outlined"
                density="compact"
                class="mb-2"
                hint="Data source name from project configuration"
                persistent-hint
              />
              <v-textarea
                v-model="item.query"
                label="SQL Query"
                variant="outlined"
                rows="4"
                hint="SQL query to append data from"
                persistent-hint
              />
            </template>

            <!-- Entity Source Type -->
            <template v-else-if="item.appendType === 'entity'">
              <div class="mb-3">
                <v-select
                  v-model="item.source"
                  :items="availableEntities"
                  label="Source Entity"
                  variant="outlined"
                  density="compact"
                  hint="Select an existing entity to append rows from"
                  persistent-hint
                />
              </div>

              <!-- Column Alignment Options -->
              <v-expansion-panels density="compact" class="mb-3">
                <v-expansion-panel>
                  <template #title>
                    <v-icon size="small" class="mr-2">mdi-cog</v-icon>
                    <span class="text-caption">Column Alignment Options</span>
                  </template>
                  <v-expansion-panel-text>
                    <div class="pt-2">
                      <v-checkbox
                        v-model="item.align_by_position"
                        label="Align by position"
                        density="compact"
                        hide-details
                        class="mb-2"
                        @update:model-value="handleAlignByPositionChange(item)"
                      />
                      <v-divider class="my-2" />
                      <p class="text-caption mb-2">
                        <strong>Column Mapping:</strong> Explicitly map source columns to target columns
                      </p>
                      <v-text-field
                        v-for="(targetCol, sourceCol) in item.column_mapping || {}"
                        :key="sourceCol"
                        :label="`${sourceCol} →`"
                        :model-value="targetCol"
                        variant="outlined"
                        density="compact"
                        class="mb-2"
                        hint="Target column name"
                        persistent-hint
                        @update:model-value="updateColumnMapping(item, sourceCol, $event)"
                      />
                      <v-btn
                        size="small"
                        variant="tonal"
                        prepend-icon="mdi-plus"
                        @click="addColumnMapping(item)"
                        class="mt-2"
                      >
                        Add Mapping
                      </v-btn>
                    </div>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>

              <!-- Column Override -->
              <v-checkbox
                v-model="item.showColumnsOverride"
                label="Override inherited columns"
                density="compact"
                hide-details
                class="mb-2"
              />
              <v-textarea
                v-if="item.showColumnsOverride"
                v-model="item.columnsText"
                label="Columns (JSON Array)"
                hint='Example: ["col1", "col2", "col3"]'
                persistent-hint
                variant="outlined"
                rows="2"
              />
            </template>
          </v-card-text>
        </v-card>
      </v-list-item>
    </v-list>

    <v-alert type="info" variant="tonal" density="compact" class="mt-3 text-caption">
      <strong>Append</strong> adds rows from multiple sources to this entity.
      <ul class="mt-2">
        <li><strong>Fixed Values:</strong> Manually specify rows as arrays</li>
        <li><strong>SQL Query:</strong> Execute query against a data source</li>
        <li><strong>From Entity:</strong> Append rows from another entity with optional column mapping</li>
      </ul>
      <div class="mt-2">
        For <strong>From Entity</strong>, use <em>column mapping</em> to rename source columns or
        <em>align by position</em> to match columns by order instead of name.
      </div>
    </v-alert>

    <v-btn variant="outlined" prepend-icon="mdi-plus" size="small" block class="mt-3" @click="handleAddAppend">
      Add Append
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface AppendConfigInternal {
  type?: 'fixed' | 'sql' | 'entity'
  appendType?: 'fixed' | 'sql' | 'entity' // Computed from type or source
  values?: any[][]
  valuesText?: string
  data_source?: string
  query?: string
  source?: string
  columns?: string[]
  columnsText?: string
  showColumnsOverride?: boolean
  align_by_position?: boolean
  column_mapping?: Record<string, string>
}

interface Props {
  modelValue?: AppendConfigInternal[]
  availableEntities?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  availableEntities: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: AppendConfigInternal[] | undefined]
}>()

const append = ref<AppendConfigInternal[]>([])

const appendTypes = [
  { title: 'Fixed Values', value: 'fixed' },
  { title: 'SQL Query', value: 'sql' },
  { title: 'From Entity', value: 'entity' },
]

const availableEntities = computed(() => props.availableEntities || [])

/**
 * Initialize append items, detecting whether they use type-based or source-based approach
 */
function initializeAppendItems(): void {
  if (!props.modelValue) {
    append.value = []
    return
  }

  append.value = props.modelValue.map((item) => {
    const initialized: AppendConfigInternal = { ...item }

    // Determine appendType based on the config structure
    if (item.source) {
      initialized.appendType = 'entity'
    } else if (item.type === 'fixed') {
      initialized.appendType = 'fixed'
      if (item.values && !item.valuesText) {
        initialized.valuesText = JSON.stringify(item.values, null, 2)
      }
    } else if (item.type === 'sql') {
      initialized.appendType = 'sql'
    }

    // For columns override
    if (item.columns && !item.columnsText) {
      initialized.columnsText = JSON.stringify(item.columns, null, 2)
    }

    return initialized
  })
}

function handleAddAppend(): void {
  append.value.push({
    type: 'fixed',
    appendType: 'fixed',
    valuesText: '',
  })
}

function handleRemoveAppend(index: number): void {
  append.value.splice(index, 1)
}

function handleAlignByPositionChange(item: AppendConfigInternal): void {
  if (item.align_by_position && item.column_mapping) {
    // Clear column mapping when switching to align_by_position
    item.column_mapping = undefined
  }
}

function addColumnMapping(item: AppendConfigInternal): void {
  if (!item.column_mapping) {
    item.column_mapping = {}
  }
  item.column_mapping['source_column'] = 'target_column'
}

function updateColumnMapping(item: AppendConfigInternal, sourceCol: string, targetCol: string): void {
  if (!item.column_mapping) {
    item.column_mapping = {}
  }
  if (targetCol) {
    item.column_mapping[sourceCol] = targetCol
  } else {
    delete item.column_mapping[sourceCol]
  }
}

/**
 * Convert internal format back to API format
 */
function normalizeForAPI(): (AppendConfigInternal | null)[] {
  return append.value.map((item) => {
    const normalized: Record<string, any> = {}

    // Always set append type
    if (item.appendType === 'fixed') {
      normalized.type = 'fixed'
      if (item.valuesText) {
        try {
          normalized.values = JSON.parse(item.valuesText)
        } catch {
          // Invalid JSON - will be caught by backend validation
          normalized.values = []
        }
      }
    } else if (item.appendType === 'sql') {
      normalized.type = 'sql'
      if (item.data_source) normalized.data_source = item.data_source
      if (item.query) normalized.query = item.query
    } else if (item.appendType === 'entity') {
      normalized.source = item.source
      if (item.showColumnsOverride && item.columnsText) {
        try {
          normalized.columns = JSON.parse(item.columnsText)
        } catch {
          // Invalid JSON - will be caught by backend validation
        }
      }
      if (item.align_by_position) normalized.align_by_position = true
      if (item.column_mapping && Object.keys(item.column_mapping).length > 0) {
        normalized.column_mapping = item.column_mapping
      }
    }

    return Object.keys(normalized).length > 0 ? (normalized as AppendConfigInternal) : null
  }).filter((item): item is AppendConfigInternal => item !== null)
}

watch(
  append,
  () => {
    const normalized = normalizeForAPI()
    emit('update:modelValue', normalized.length > 0 ? normalized : undefined)
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  () => {
    initializeAppendItems()
  },
  { deep: true }
)

// Initialize on mount
initializeAppendItems()
</script>

<style scoped>
.text-caption {
  font-size: 0.75rem;
}
</style>
