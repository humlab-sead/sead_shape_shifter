<template>
  <v-card class="append-editor-compact">
    <v-card-title class="d-flex align-center justify-space-between py-2">
      <span class="text-body-2">Append</span>
      <v-btn variant="text" size="x-small" prepend-icon="mdi-plus" @click="handleAddAppend"> Add </v-btn>
    </v-card-title>

    <v-divider />

    <v-card-text class="pa-4">
      <v-expansion-panels v-if="append.length > 0" variant="accordion" density="compact" class="mb-3">
        <v-expansion-panel v-for="(item, index) in append" :key="index">
          <v-expansion-panel-title class="py-2">
            <div class="d-flex align-center justify-space-between flex-grow-1">
              <span class="text-caption">{{ getAppendLabel(item) }}</span>
              <v-btn
                icon="mdi-delete"
                variant="text"
                size="x-small"
                color="error"
                @click.stop="handleRemoveAppend(index)"
              />
            </div>
          </v-expansion-panel-title>

          <v-expansion-panel-text class="pt-2">
            <!-- Header: Type selector + source selector + alignment toggle -->
            <v-row align="start" class="mb-3">
              <v-col cols="12" sm="5" md="4">
                <v-select
                  v-model="item.type"
                  :items="appendTypes"
                  label="Append Type"
                  variant="outlined"
                  density="compact"
                />
              </v-col>

              <v-col v-if="item.type === 'entity'" cols="12" sm="4" md="4">
                <v-select
                  :model-value="item.source"
                  :items="availableEntities"
                  label="Source Entity"
                  variant="outlined"
                  density="compact"
                  persistent-hint
                  @update:model-value="handleSourceChange(item, $event)"
                />
              </v-col>

              <v-col v-if="item.type === 'entity'" cols="12" sm="3" md="2">
                <v-btn-toggle
                  :model-value="getAlignmentMode(item)"
                  mandatory
                  divided
                  variant="outlined"
                  density="compact"
                  class="append-alignment-toggle"
                  @update:model-value="handleAlignmentModeChange(item, $event)"
                >
                  <v-btn value="name" size="small" class="text-caption">Name</v-btn>
                  <v-btn value="position" size="small" class="text-caption">Position</v-btn>
                </v-btn-toggle>
              </v-col>

            </v-row>

            <!-- Fixed Values Type -->
            <template v-if="item.type === 'fixed' && !item.source">
              <FixedValuesGrid
                v-if="fixedValuesColumns.length > 0"
                :model-value="item.values || []"
                :columns="fixedValuesColumns"
                :public-id="parentPublicId || undefined"
                height="320px"
                @update:model-value="handleFixedValuesChange(item, $event)"
              />
              <v-alert v-else type="info" variant="tonal" density="compact">
                <v-alert-title>No Columns Defined</v-alert-title>
                Add keys and/or columns in the Basic tab to define the fixed append grid structure.
              </v-alert>
            </template>

            <!-- SQL Query Type -->
            <template v-else-if="item.type === 'sql'">
              <v-autocomplete
                v-model="item.data_source"
                :items="availableDataSources"
                label="Data Source"
                variant="outlined"
                density="compact"
                class="mb-2"
                hint="Data source name from project configuration"
                persistent-hint
                clearable
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
              <div v-if="item.source" class="mb-3">
                <v-row align="start" class="mb-0">
                  <v-col cols="12" md="4">
                    <div class="text-caption font-weight-medium mb-2">Target columns</div>
                    <div class="d-flex flex-wrap ga-1">
                      <v-chip v-for="column in parentColumns" :key="`target-${column}`" size="small" variant="outlined">
                        {{ column }}
                      </v-chip>
                      <span v-if="parentColumns.length === 0" class="text-caption text-medium-emphasis">No parent columns configured.</span>
                    </div>
                  </v-col>

                  <v-col cols="12" md="6">
                    <v-select
                      :model-value="getSourceColumnsSelection(item)"
                      :items="getAvailableSourceColumns(item)"
                      label="Source columns"
                      variant="outlined"
                      density="compact"
                      chips
                      closable-chips
                      multiple
                      clearable
                      persistent-hint
                      @update:model-value="handleSourceColumnsChange(item, $event)"
                    />
                  </v-col>
                </v-row>
              </div>

              <div class="mb-3">
                <div v-if="item.source && getAlignmentMode(item) === 'name'" class="mt-2">
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
                    </div>
                  </v-alert>
                </div>

                <div v-if="item.source && getAlignmentMode(item) === 'position'" class="mt-2">
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
                    </div>
                  </v-alert>
                </div>

                <div v-if="item.source && getAlignmentMode(item) === 'position' && getPositionAlignmentSummary(item).pairs.length > 0" class="mt-2">
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

                <v-alert
                  v-if="item.source && item.column_mapping && Object.keys(item.column_mapping).length > 0"
                  type="info"
                  variant="tonal"
                  density="compact"
                  class="mt-2"
                >
                  <div class="text-caption">
                    Explicit mapping is configured for this append item. Edit the YAML to change it, or switch to
                    <strong>Match by name</strong> or <strong>Match by position</strong> here to replace it.
                  </div>
                </v-alert>
              </div>

            </template>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

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
        For <strong>From Entity</strong>, use <em>Match by name</em> for straightforward matching or
        <em>Match by position</em> to match columns by order instead of name.
        Safe properties like filters and drop_duplicates are inherited from the parent entity.
      </div>
      <div class="mt-2">
        <strong>Alignment modes:</strong> <em>Match by name</em> requires matching payload column names,
        <em>Match by position</em> pairs payload columns by order.
        Use the <strong>Source columns</strong> selector to limit or reorder the source payload columns used during alignment.
        Identity columns such as <code>system_id</code> and <code>public_id</code> are excluded from alignment.
        <em>Explicit mapping</em> is still supported in YAML, but it is not edited in this UI.
      </div>
      </v-alert>

    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import FixedValuesGrid from './FixedValuesGrid.vue'

interface AppendConfigInternal {
  type?: 'fixed' | 'sql' | 'entity'
  appendType?: 'fixed' | 'sql' | 'entity' // Computed from type or source
  values?: any[][]
  valuesText?: string
  data_source?: string
  query?: string
  source?: string
  columns?: string[]
  align_by_position?: boolean
  column_mapping?: Record<string, string>
  sourceColumnsState?: 'default' | 'custom' | 'position-default'
}

interface Props {
  modelValue?: AppendConfigInternal[]
  availableEntities?: string[]
  dataSourceNames?: string[]
  parentColumns?: string[]
  parentPublicId?: string | null
  fixedValuesColumns?: string[]
  sourceEntityColumns?: Record<string, string[]>
  sourceEntityPublicIds?: Record<string, string | null>
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  availableEntities: () => [],
  dataSourceNames: () => [],
  parentColumns: () => [],
  parentPublicId: null,
  fixedValuesColumns: () => [],
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
const availableDataSources = computed(() => props.dataSourceNames || [])
const parentColumns = computed(() => (props.parentColumns || []).filter((column) => typeof column === 'string' && column.trim().length > 0))
const fixedValuesColumns = computed(() => (props.fixedValuesColumns || []).filter((column) => typeof column === 'string' && column.trim().length > 0))

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

function normalizeSourceColumns(columns: string[], availableColumns: string[]): string[] {
  const availableSet = new Set(availableColumns)
  const normalized: string[] = []

  for (const column of columns) {
    if (availableSet.has(column) && !normalized.includes(column)) {
      normalized.push(column)
    }
  }

  return normalized
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
  const availableColumns = getAvailableSourceColumns(item)

  if (item.sourceColumnsState === 'position-default') {
    return []
  }

  if (item.sourceColumnsState === 'custom') {
    return normalizeSourceColumns(item.columns || [], availableColumns)
  }

  return availableColumns
}

function getSourceColumnsSelection(item: AppendConfigInternal): string[] {
  return getEffectiveSourceColumns(item)
}

function handleSourceChange(item: AppendConfigInternal, source: string | null): void {
  item.source = source || undefined
  item.columns = undefined

  if (getAlignmentMode(item) === 'position') {
    item.sourceColumnsState = 'position-default'
  } else {
    item.sourceColumnsState = 'default'
  }
}

function handleSourceColumnsChange(item: AppendConfigInternal, value: string[]): void {
  const normalized = normalizeSourceColumns(value, getAvailableSourceColumns(item))
  item.columns = normalized
  item.sourceColumnsState = 'custom'
}

function handleFixedValuesChange(item: AppendConfigInternal, value: any[][]): void {
  item.values = Array.isArray(value) ? value : []
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
      initialized.values = Array.isArray(item.values) ? item.values : []
    } else if (item.type === 'sql') {
      initialized.type = 'sql'
      initialized.appendType = 'sql'
    }

    if (item.columns) {
      initialized.columns = item.columns.filter((column): column is string => typeof column === 'string' && column.trim().length > 0)
      initialized.sourceColumnsState = 'custom'
    } else {
      initialized.sourceColumnsState = 'default'
    }

    return initialized
  })
}

function handleAddAppend(): void {
  append.value.push({
    type: 'fixed',
    appendType: 'fixed',
    values: [],
  })
}

function handleRemoveAppend(index: number): void {
  append.value.splice(index, 1)
}

function getAppendLabel(item: AppendConfigInternal): string {
  if (item.type === 'entity') {
    const modeLabel = getAlignmentMode(item) === 'position' ? 'position' : 'name'
    return item.source ? `From ${item.source} (${modeLabel})` : 'From entity'
  }

  if (item.type === 'sql') {
    return item.data_source ? `SQL append (${item.data_source})` : 'SQL append'
  }

  if (item.type === 'fixed') {
    return 'Fixed values'
  }

  return 'Append item'
}

function getAlignmentMode(item: AppendConfigInternal): 'name' | 'position' {
  if (item.align_by_position) {
    return 'position'
  }
  return 'name'
}

function handleAlignmentModeChange(item: AppendConfigInternal, mode: 'name' | 'position' | null): void {
  if (!mode) {
    return
  }

  const previousMode = getAlignmentMode(item)

  // Clear UI-managed alignment settings. Existing YAML column_mapping is preserved
  // unless the user actively switches alignment mode here.
  item.align_by_position = false

  if (mode === 'position') {
    item.align_by_position = true
    item.column_mapping = undefined
    if (previousMode !== 'position' && item.sourceColumnsState !== 'custom') {
      item.columns = undefined
      item.sourceColumnsState = 'position-default'
    }
  } else {
    item.column_mapping = undefined
    if (item.sourceColumnsState !== 'custom') {
      item.columns = undefined
      item.sourceColumnsState = 'default'
    }
  }

  if (mode === 'name' && item.sourceColumnsState !== 'custom') {
    item.columns = undefined
    item.sourceColumnsState = 'default'
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
      normalized.values = Array.isArray(item.values) ? item.values : []
    } else if (effectiveType === 'sql') {
      normalized.type = 'sql'
      if (item.data_source) normalized.data_source = item.data_source
      if (item.query) normalized.query = item.query
    } else if (effectiveType === 'entity') {
      normalized.source = item.source
      if (item.sourceColumnsState === 'custom' && item.columns) {
        normalized.columns = item.columns
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

.append-editor-compact :deep(.v-expansion-panel-title) {
  min-height: 40px;
  padding-top: 4px;
  padding-bottom: 4px;
}

.append-editor-compact :deep(.v-expansion-panel-text__wrapper) {
  padding: 8px 0 0 0;
}

.append-alignment-toggle {
  flex-wrap: wrap;
  gap: 6px;
}

:deep(.append-alignment-toggle .v-btn) {
  font-size: 0.75rem;
  letter-spacing: normal;
  text-transform: none;
}
</style>
