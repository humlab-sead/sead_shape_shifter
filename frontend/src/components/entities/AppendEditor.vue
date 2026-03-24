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
            <template v-if="item.type === 'fixed' && !item.source">
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
            <template v-else-if="item.type === 'sql'">
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
            <template v-else-if="item.type === 'entity'">
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

              <div v-if="item.source" class="mb-3">
                <div class="text-caption font-weight-medium mb-2">Target columns</div>
                <div class="d-flex flex-wrap ga-1 mb-3">
                  <v-chip v-for="column in parentColumns" :key="`target-${column}`" size="small" variant="outlined">
                    {{ column }}
                  </v-chip>
                  <span v-if="parentColumns.length === 0" class="text-caption text-medium-emphasis">No parent columns configured.</span>
                </div>

                <div class="text-caption font-weight-medium mb-2">Source columns</div>
                <div class="d-flex flex-wrap ga-1">
                  <v-chip
                    v-for="column in getEffectiveSourceColumns(item)"
                    :key="`source-${item.source}-${column}`"
                    size="small"
                    color="secondary"
                    variant="tonal"
                  >
                    {{ column }}
                  </v-chip>
                  <span v-if="getEffectiveSourceColumns(item).length === 0" class="text-caption text-medium-emphasis">
                    No source columns available for this entity.
                  </span>
                </div>
              </div>

              <!-- Column Alignment Options -->
              <v-expansion-panels density="compact" class="mb-3">
                <v-expansion-panel>
                  <template #title>
                    <v-icon size="small" class="mr-2">mdi-cog</v-icon>
                    <span class="text-caption">Column Alignment</span>
                  </template>
                  <v-expansion-panel-text>
                    <div class="pt-2">
                      <p class="text-caption mb-3 text-medium-emphasis">
                        Choose how source columns are matched to target columns:
                      </p>
                      
                      <!-- Alignment Mode Selection -->
                      <v-radio-group
                        :model-value="getAlignmentMode(item)"
                        density="compact"
                        hide-details
                        class="mb-3"
                        @update:model-value="handleAlignmentModeChange(item, $event)"
                      >
                        <v-radio value="name">
                          <template #label>
                            <div>
                              <strong>Match by name</strong>
                              <span class="text-caption text-medium-emphasis ml-2">(default)</span>
                              <div class="text-caption text-medium-emphasis">
                                All target columns must exist in the source with the same names
                              </div>
                            </div>
                          </template>
                        </v-radio>
                        
                        <v-radio value="position" class="mt-2">
                          <template #label>
                            <div>
                              <strong>Match by position</strong>
                              <v-chip size="x-small" color="warning" variant="flat" class="ml-2">advanced</v-chip>
                              <div class="text-caption text-medium-emphasis">
                                Align columns by order, ignoring names (excludes identity columns)
                              </div>
                            </div>
                          </template>
                        </v-radio>
                        
                        <v-radio value="mapping" class="mt-2">
                          <template #label>
                            <div>
                              <strong>Explicit mapping</strong>
                              <div class="text-caption text-medium-emphasis">
                                Manually specify how each source column maps to target
                              </div>
                            </div>
                          </template>
                        </v-radio>
                      </v-radio-group>

                      <div v-if="item.source && getAlignmentMode(item) === 'name'" class="mt-3">
                        <v-divider class="mb-3" />
                        <v-alert
                          :type="getNameAlignmentSummary(item).canMatch ? 'success' : 'warning'"
                          variant="tonal"
                          density="compact"
                        >
                          <div class="text-caption">
                            <strong>
                              {{ getNameAlignmentSummary(item).canMatch ? 'Match by name is possible.' : 'Match by name is not possible.' }}
                            </strong>
                            <div v-if="getNameAlignmentSummary(item).missingColumns.length > 0" class="mt-1">
                              Missing target columns: {{ getNameAlignmentSummary(item).missingColumns.join(', ') }}
                            </div>
                            <div v-else class="mt-1">
                              All target columns are available in the source.
                            </div>
                            <div v-if="getNameAlignmentSummary(item).extraColumns.length > 0" class="mt-1">
                              Extra source columns ignored: {{ getNameAlignmentSummary(item).extraColumns.join(', ') }}
                            </div>
                            <div v-if="getNameAlignmentSummary(item).excludedTargetColumns.length > 0" class="mt-1">
                              Ignored target identity columns: {{ getNameAlignmentSummary(item).excludedTargetColumns.join(', ') }}
                            </div>
                            <div v-if="getNameAlignmentSummary(item).excludedSourceColumns.length > 0" class="mt-1">
                              Ignored source identity columns: {{ getNameAlignmentSummary(item).excludedSourceColumns.join(', ') }}
                            </div>
                            <div v-if="!getNameAlignmentSummary(item).canMatch" class="mt-1">
                              Switch to <strong>Explicit mapping</strong> if you need to rename source columns.
                            </div>
                          </div>
                        </v-alert>

                        <div v-if="getNameAlignmentSummary(item).matchedColumns.length > 0" class="mt-2">
                          <div class="text-caption font-weight-medium mb-1">Matched columns</div>
                          <div class="d-flex flex-wrap ga-1">
                            <v-chip
                              v-for="column in getNameAlignmentSummary(item).matchedColumns"
                              :key="`matched-${item.source}-${column}`"
                              size="small"
                              color="success"
                              variant="tonal"
                            >
                              {{ column }}
                            </v-chip>
                          </div>
                        </div>
                      </div>

                      <div v-if="item.source && getAlignmentMode(item) === 'position'" class="mt-3">
                        <v-divider class="mb-3" />
                        <v-alert
                          :type="getPositionAlignmentSummary(item).canMatch ? 'success' : 'warning'"
                          variant="tonal"
                          density="compact"
                        >
                          <div class="text-caption">
                            <strong>
                              {{ getPositionAlignmentSummary(item).canMatch ? 'Match by position is possible.' : 'Match by position is not possible.' }}
                            </strong>
                            <div class="mt-1">
                              Target columns: {{ getPositionAlignmentSummary(item).targetCount }}
                              | Source columns: {{ getPositionAlignmentSummary(item).sourceCount }}
                            </div>
                            <div v-if="getPositionAlignmentSummary(item).excludedTargetColumns.length > 0" class="mt-1">
                              Ignored target identity columns: {{ getPositionAlignmentSummary(item).excludedTargetColumns.join(', ') }}
                            </div>
                            <div v-if="getPositionAlignmentSummary(item).excludedSourceColumns.length > 0" class="mt-1">
                              Ignored source identity columns: {{ getPositionAlignmentSummary(item).excludedSourceColumns.join(', ') }}
                            </div>
                            <div v-if="!getPositionAlignmentSummary(item).canMatch" class="mt-1">
                              Position matching requires the same number of source and target columns.
                            </div>
                          </div>
                        </v-alert>

                        <div v-if="getPositionAlignmentSummary(item).pairs.length > 0" class="mt-2">
                          <div class="text-caption font-weight-medium mb-1">Inferred position pairs</div>
                          <div class="d-flex flex-column ga-1">
                            <div
                              v-for="pair in getPositionAlignmentSummary(item).pairs"
                              :key="`position-${item.source}-${pair.source}-${pair.target}-${pair.index}`"
                              class="text-caption"
                            >
                              <v-chip size="small" color="secondary" variant="tonal" class="mr-2">{{ pair.source }}</v-chip>
                              <span class="text-medium-emphasis mr-2">→</span>
                              <v-chip size="small" color="success" variant="tonal">{{ pair.target }}</v-chip>
                            </div>
                          </div>
                        </div>
                      </div>

                      <!-- Explicit Mapping Editor -->
                      <div v-if="getAlignmentMode(item) === 'mapping'" class="mt-3">
                        <v-divider class="mb-3" />
                        <p class="text-caption mb-2">
                          <strong>Column Mapping:</strong> Define source → target column mappings
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
                    </div>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>

              <v-expansion-panels density="compact" class="mb-3">
                <v-expansion-panel>
                  <template #title>
                    <v-icon size="small" class="mr-2">mdi-tune</v-icon>
                    <span class="text-caption">Advanced: custom source column subset</span>
                  </template>
                  <v-expansion-panel-text>
                    <div class="pt-2">
                      <p class="text-caption mb-3 text-medium-emphasis">
                        Optional. Restrict which columns are taken from the source entity before alignment.
                        Most source-based append cases should leave this off.
                      </p>
                      <v-checkbox
                        :model-value="item.showColumnsOverride"
                        label="Use custom source column subset"
                        density="compact"
                        hide-details
                        class="mb-2"
                        @update:model-value="handleSourceSubsetToggle(item, $event)"
                      />
                      <v-textarea
                        v-if="item.showColumnsOverride"
                        v-model="item.columnsText"
                        label="Source columns (JSON Array)"
                        hint='Example: ["col1", "col2", "col3"]'
                        persistent-hint
                        variant="outlined"
                        rows="2"
                      />
                    </div>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
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
        <li><strong>From Entity (source):</strong> Fetch rows from another entity's processed data
          <ul class="ml-4 mt-1">
            <li>Uses shorthand: <code>source: entity_name</code> instead of <code>type: entity</code></li>
            <li>Fetches from entity's table_store (not a new data load)</li>
            <li>Does NOT inherit loader properties (type, values, query) from parent</li>
          </ul>
        </li>
      </ul>
      <div class="mt-2">
        For <strong>From Entity</strong>, use <em>column mapping</em> to rename source columns or
        <em>align by position</em> to match columns by order instead of name.
        Safe properties like filters and drop_duplicates are inherited from the parent entity.
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
  parentColumns?: string[]
  parentPublicId?: string | null
  sourceEntityColumns?: Record<string, string[]>
  sourceEntityPublicIds?: Record<string, string | null>
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  availableEntities: () => [],
  parentColumns: () => [],
  parentPublicId: null,
  sourceEntityColumns: () => ({}),
  sourceEntityPublicIds: () => ({}),
})

const emit = defineEmits<{
  'update:modelValue': [value: AppendConfigInternal[] | undefined]
}>()

const append = ref<AppendConfigInternal[]>([])
const lastEmittedValue = ref<string>('[]')

const appendTypes = [
  { title: 'Fixed Values', value: 'fixed' },
  { title: 'SQL Query', value: 'sql' },
  { title: 'From Entity', value: 'entity' },
]

const availableEntities = computed(() => props.availableEntities || [])
const parentColumns = computed(() => (props.parentColumns || []).filter((column) => typeof column === 'string' && column.trim().length > 0))

function parseColumnsText(columnsText?: string): string[] {
  if (!columnsText?.trim()) {
    return []
  }

  try {
    const parsed = JSON.parse(columnsText)
    return Array.isArray(parsed) ? parsed.filter((column): column is string => typeof column === 'string' && column.trim().length > 0) : []
  } catch {
    return []
  }
}

function getAvailableSourceColumns(item: AppendConfigInternal): string[] {
  if (!item.source) {
    return []
  }

  return props.sourceEntityColumns?.[item.source] || []
}

function getSourcePublicId(item: AppendConfigInternal): string | null {
  if (!item.source) {
    return null
  }

  return props.sourceEntityPublicIds?.[item.source] || null
}

function getAlignableColumns(columns: string[], publicId?: string | null): { alignable: string[]; excluded: string[] } {
  const excludedSet = new Set(['system_id'])
  if (publicId?.trim()) {
    excludedSet.add(publicId.trim())
  }

  const alignable: string[] = []
  const excluded: string[] = []

  for (const column of columns) {
    if (excludedSet.has(column)) {
      excluded.push(column)
    } else {
      alignable.push(column)
    }
  }

  return { alignable, excluded }
}

function getEffectiveSourceColumns(item: AppendConfigInternal): string[] {
  if (item.showColumnsOverride) {
    const parsedColumns = parseColumnsText(item.columnsText)
    if (parsedColumns.length > 0) {
      return parsedColumns
    }

    if (item.columns?.length) {
      return item.columns.filter((column): column is string => typeof column === 'string' && column.trim().length > 0)
    }
  }

  return getAvailableSourceColumns(item)
}

function handleSourceSubsetToggle(item: AppendConfigInternal, enabled: boolean | null): void {
  item.showColumnsOverride = Boolean(enabled)

  if (!item.showColumnsOverride) {
    item.columns = undefined
    item.columnsText = ''
  }
}

function getNameAlignmentSummary(item: AppendConfigInternal): {
  matchedColumns: string[]
  missingColumns: string[]
  extraColumns: string[]
  excludedTargetColumns: string[]
  excludedSourceColumns: string[]
  canMatch: boolean
} {
  const { alignable: target, excluded: excludedTargetColumns } = getAlignableColumns(parentColumns.value, props.parentPublicId)
  const { alignable: source, excluded: excludedSourceColumns } = getAlignableColumns(
    getEffectiveSourceColumns(item),
    getSourcePublicId(item)
  )
  const sourceSet = new Set(source)
  const targetSet = new Set(target)

  const matchedColumns = target.filter((column) => sourceSet.has(column))
  const missingColumns = target.filter((column) => !sourceSet.has(column))
  const extraColumns = source.filter((column) => !targetSet.has(column))

  return {
    matchedColumns,
    missingColumns,
    extraColumns,
    excludedTargetColumns,
    excludedSourceColumns,
    canMatch: target.length > 0 && missingColumns.length === 0,
  }
}

function getPositionAlignmentSummary(item: AppendConfigInternal): {
  targetCount: number
  sourceCount: number
  canMatch: boolean
  excludedTargetColumns: string[]
  excludedSourceColumns: string[]
  pairs: Array<{ index: number; source: string; target: string }>
} {
  const { alignable: target, excluded: excludedTargetColumns } = getAlignableColumns(
    parentColumns.value,
    props.parentPublicId
  )
  const { alignable: source, excluded: excludedSourceColumns } = getAlignableColumns(
    getEffectiveSourceColumns(item),
    getSourcePublicId(item)
  )
  const pairCount = Math.min(target.length, source.length)

  return {
    targetCount: target.length,
    sourceCount: source.length,
    canMatch: target.length > 0 && target.length === source.length,
    excludedTargetColumns,
    excludedSourceColumns,
    pairs: Array.from({ length: pairCount }, (_, index) => ({
      index,
      source: source[index] || '',
      target: target[index] || '',
    })),
  }
}

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
      initialized.type = 'entity'
      initialized.appendType = 'entity'
    } else if (item.type === 'fixed') {
      initialized.type = 'fixed'
      initialized.appendType = 'fixed'
      if (item.values && !item.valuesText) {
        initialized.valuesText = JSON.stringify(item.values, null, 2)
      }
    } else if (item.type === 'sql') {
      initialized.type = 'sql'
      initialized.appendType = 'sql'
    }

    // For columns override
    if (item.columns && !item.columnsText) {
      initialized.columnsText = JSON.stringify(item.columns, null, 2)
      initialized.showColumnsOverride = true
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

function getAlignmentMode(item: AppendConfigInternal): 'name' | 'position' | 'mapping' {
  if (item.align_by_position) {
    return 'position'
  }
  if (item.column_mapping && Object.keys(item.column_mapping).length > 0) {
    return 'mapping'
  }
  return 'name'
}

function handleAlignmentModeChange(item: AppendConfigInternal, mode: 'name' | 'position' | 'mapping' | null): void {
  if (!mode) {
    return
  }

  // Clear all alignment settings
  item.align_by_position = false
  item.column_mapping = undefined

  // Apply new mode
  if (mode === 'position') {
    item.align_by_position = true
  } else if (mode === 'mapping') {
    item.column_mapping = {}
  }
  // 'name' mode requires no special settings (default behavior)
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
function normalizeForAPI(): AppendConfigInternal[] {
  return append.value.map((item) => {
    const normalized: Record<string, any> = {}
    const effectiveType = item.type ?? (item.source ? 'entity' : undefined)

    // Determine current type based on item state
    if (effectiveType === 'fixed' && !item.source) {
      normalized.type = 'fixed'
      if (item.valuesText) {
        try {
          normalized.values = JSON.parse(item.valuesText)
        } catch {
          // Invalid JSON - will be caught by backend validation
          normalized.values = []
        }
      }
    } else if (effectiveType === 'sql') {
      normalized.type = 'sql'
      if (item.data_source) normalized.data_source = item.data_source
      if (item.query) normalized.query = item.query
    } else if (effectiveType === 'entity') {
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
    const emitValue = normalized.length > 0 ? normalized : undefined
    lastEmittedValue.value = JSON.stringify(emitValue)
    emit('update:modelValue', emitValue)
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  (newValue) => {
    const incomingValue = JSON.stringify(newValue)
    // Only reinitialize if this is NOT the value we just emitted
    if (incomingValue !== lastEmittedValue.value) {
      initializeAppendItems()
    }
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
