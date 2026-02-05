<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2">mdi-database-cog</v-icon>
      Visual Query Builder
      <v-spacer />
      <v-chip v-if="generatedSql" color="success" size="small"> SQL Generated </v-chip>
    </v-card-title>

    <v-card-text>
      <!-- Data Source Selector -->
      <v-select
        v-model="selectedDataSource"
        :items="dataSourceNames"
        label="Select Data Source"
        prepend-icon="mdi-database"
        density="comfortable"
        class="mb-4"
        :disabled="loadingTables"
        @update:model-value="onDataSourceChange"
      />

      <!-- Table Selector -->
      <v-select
        v-model="selectedTable"
        :items="tables"
        item-title="table_name"
        item-value="table_name"
        label="Select Table"
        prepend-icon="mdi-table"
        density="comfortable"
        class="mb-4"
        :disabled="!selectedDataSource || loadingTables"
        :loading="loadingTables"
        @update:model-value="onTableChange"
      >
        <template #item="{ props, item }">
          <v-list-item v-bind="props">
            <template #prepend>
              <v-icon>mdi-table</v-icon>
            </template>
            <template #subtitle v-if="item.raw.schema_name"> Schema: {{ item.raw.schema_name }} </template>
          </v-list-item>
        </template>
      </v-select>

      <!-- Column Selector -->
      <v-select
        v-model="selectedColumns"
        :items="availableColumns"
        label="Select Columns (* for all)"
        prepend-icon="mdi-table-column"
        density="comfortable"
        class="mb-4"
        multiple
        chips
        closable-chips
        :disabled="!selectedTable || loadingSchema"
        :loading="loadingSchema"
        clearable
      >
        <template #prepend-item>
          <v-list-item @click="toggleAllColumns">
            <template #prepend>
              <v-checkbox-btn
                :model-value="selectedColumns.length === availableColumns.length"
                :indeterminate="selectedColumns.length > 0 && selectedColumns.length < availableColumns.length"
              />
            </template>
            <v-list-item-title>Select All</v-list-item-title>
          </v-list-item>
          <v-divider class="mt-2" />
        </template>
      </v-select>

      <!-- WHERE Conditions -->
      <v-expansion-panels v-model="conditionsPanel" class="mb-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon class="mr-2">mdi-filter</v-icon>
            WHERE Conditions
            <v-chip v-if="conditions.length > 0" size="small" class="ml-2">
              {{ conditions.length }}
            </v-chip>
          </v-expansion-panel-title>

          <v-expansion-panel-text>
            <!-- Logic Operator for multiple conditions -->
            <v-radio-group
              v-if="conditions.length > 1"
              v-model="conditionLogic"
              inline
              density="compact"
              class="mb-3"
              hide-details
            >
              <v-radio label="AND (all must match)" value="AND" />
              <v-radio label="OR (any can match)" value="OR" />
            </v-radio-group>

            <!-- Condition List -->
            <QueryCondition
              v-for="(_, index) in conditions"
              :key="index"
              v-model="conditions[index]!"
              :available-columns="availableColumns"
              @delete="removeCondition(index)"
            />

            <!-- Add Condition Button -->
            <v-btn
              prepend-icon="mdi-plus"
              variant="outlined"
              color="primary"
              block
              @click="addCondition"
              :disabled="!selectedTable"
            >
              Add Condition
            </v-btn>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- ORDER BY -->
      <v-expansion-panels v-model="orderByPanel" class="mb-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon class="mr-2">mdi-sort</v-icon>
            ORDER BY
            <v-chip v-if="orderBy.length > 0" size="small" class="ml-2">
              {{ orderBy.length }}
            </v-chip>
          </v-expansion-panel-title>

          <v-expansion-panel-text>
            <!-- Order By List -->
            <div v-for="(order, index) in orderBy" :key="index" class="d-flex align-center mb-2">
              <v-select
                v-model="order.column"
                :items="availableColumns"
                label="Column"
                density="compact"
                style="flex: 1"
                class="mr-2"
                hide-details
              >
                <template #prepend-inner>
                  <v-icon size="small">mdi-table-column</v-icon>
                </template>
              </v-select>

              <v-select
                v-model="order.direction"
                :items="['ASC', 'DESC']"
                label="Direction"
                density="compact"
                style="max-width: 120px"
                class="mr-2"
                hide-details
              />

              <v-btn icon="mdi-delete" variant="text" color="error" size="small" @click="removeOrderBy(index)" />
            </div>

            <!-- Add Order By Button -->
            <v-btn
              prepend-icon="mdi-plus"
              variant="outlined"
              color="primary"
              block
              @click="addOrderBy"
              :disabled="!selectedTable"
            >
              Add ORDER BY
            </v-btn>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- LIMIT -->
      <v-text-field
        v-model.number="limit"
        label="LIMIT (max rows)"
        prepend-icon="mdi-speedometer"
        type="number"
        density="comfortable"
        class="mb-4"
        min="1"
        max="10000"
        hint="Maximum 10,000 rows"
        persistent-hint
      />

      <!-- SQL Preview -->
      <v-card variant="tonal" class="mb-4" v-if="generatedSql">
        <v-card-title class="text-subtitle-1">
          <v-icon class="mr-2" size="small">mdi-code-tags</v-icon>
          Generated SQL
        </v-card-title>
        <v-card-text>
          <pre class="sql-preview">{{ generatedSql }}</pre>
        </v-card-text>
      </v-card>

      <!-- Action Buttons -->
      <div class="d-flex gap-2">
        <v-btn
          prepend-icon="mdi-refresh"
          color="primary"
          variant="elevated"
          @click="generateSql"
          :disabled="!canGenerateSql"
        >
          Generate SQL
        </v-btn>

        <v-btn
          prepend-icon="mdi-send"
          color="success"
          variant="elevated"
          @click="useGeneratedSql"
          :disabled="!generatedSql"
        >
          Use This Query
        </v-btn>

        <v-spacer />

        <v-btn prepend-icon="mdi-close" variant="text" @click="resetBuilder"> Clear </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useDataSourceStore } from '@/stores/data-source'
import schemaApi from '@/api/schema'
import type { TableMetadata } from '@/types/schema'
import QueryCondition, { type QueryConditionData } from './QueryCondition.vue'

const emit = defineEmits<{
  'use-query': [sql: string, dataSource: string]
}>()

const dataSourceStore = useDataSourceStore()

// Data sources
const dataSourceNames = computed(() => dataSourceStore.dataSources.map((ds: any) => ds.name))

// Load data sources on mount
onMounted(async () => {
  if (dataSourceStore.dataSources.length === 0) {
    await dataSourceStore.fetchDataSources()
  }
})

// State
const selectedDataSource = ref<string>('')
const selectedTable = ref<string>('')
const selectedColumns = ref<string[]>([])
const conditions = ref<QueryConditionData[]>([])
const conditionLogic = ref<'AND' | 'OR'>('AND')
const orderBy = ref<Array<{ column: string; direction: 'ASC' | 'DESC' }>>([])
const limit = ref<number>(100)
const generatedSql = ref<string>('')

// UI state
const loadingTables = ref(false)
const loadingSchema = ref(false)
const tables = ref<TableMetadata[]>([])
const availableColumns = ref<string[]>([])
const conditionsPanel = ref<number | undefined>(undefined)
const orderByPanel = ref<number | undefined>(undefined)

// Computed
const canGenerateSql = computed(() => {
  return selectedDataSource.value && selectedTable.value && selectedColumns.value.length > 0
})

// Methods
const onDataSourceChange = async () => {
  selectedTable.value = ''
  selectedColumns.value = []
  tables.value = []
  availableColumns.value = []
  generatedSql.value = ''

  if (!selectedDataSource.value) return

  loadingTables.value = true
  try {
    tables.value = await schemaApi.listTables(selectedDataSource.value)
  } catch (error) {
    console.error('Failed to load tables:', error)
  } finally {
    loadingTables.value = false
  }
}

const onTableChange = async () => {
  selectedColumns.value = []
  availableColumns.value = []
  generatedSql.value = ''

  if (!selectedTable.value || !selectedDataSource.value) return

  loadingSchema.value = true
  try {
    const schema = await schemaApi.getTableSchema(selectedDataSource.value, selectedTable.value)
    // Backend returns 'name' field, not 'column_name'
    availableColumns.value = schema.columns.map((col: any) => col.name)
  } catch (error) {
    console.error('Failed to load table schema:', error)
  } finally {
    loadingSchema.value = false
  }
}

const toggleAllColumns = () => {
  if (selectedColumns.value.length === availableColumns.value.length) {
    selectedColumns.value = []
  } else {
    selectedColumns.value = [...availableColumns.value]
  }
}

const addCondition = () => {
  conditions.value.push({
    column: availableColumns.value[0] || '',
    operator: '=',
    value: '',
  })
  // Auto-expand conditions panel
  conditionsPanel.value = 0
}

const removeCondition = (index: number) => {
  conditions.value.splice(index, 1)
}

const addOrderBy = () => {
  orderBy.value.push({
    column: availableColumns.value[0] || '',
    direction: 'ASC',
  })
  // Auto-expand order by panel
  orderByPanel.value = 0
}

const removeOrderBy = (index: number) => {
  orderBy.value.splice(index, 1)
}

const escapeIdentifier = (identifier: string): string => {
  // Escape identifiers with double quotes for SQL compliance
  return `"${identifier.replace(/"/g, '""')}"`
}

const escapeLiteral = (value: string): string => {
  // Escape string literals with single quotes
  return `'${value.replace(/'/g, "''")}'`
}

const buildWhereClause = (): string => {
  if (conditions.value.length === 0) return ''

  const clauses = conditions.value
    .filter((c) => c.column) // Only include conditions with a column selected
    .map((c) => {
      const column = escapeIdentifier(c.column)

      switch (c.operator) {
        case 'IS NULL':
        case 'IS NOT NULL':
          return `${column} ${c.operator}`

        case 'IN':
        case 'NOT IN': {
          // Parse comma-separated values
          const values = c.value
            .split(',')
            .map((v) => escapeLiteral(v.trim()))
            .join(', ')
          return `${column} ${c.operator} (${values})`
        }

        case 'BETWEEN': {
          // Expect format: "value1 AND value2"
          const parts = c.value.split(/\s+AND\s+/i)
          if (parts.length === 2 && parts[0] && parts[1]) {
            return `${column} BETWEEN ${escapeLiteral(parts[0].trim())} AND ${escapeLiteral(parts[1].trim())}`
          }
          return `${column} = ${escapeLiteral(c.value)}`
        }

        case 'LIKE':
        case 'NOT LIKE':
          return `${column} ${c.operator} ${escapeLiteral(c.value)}`

        default: {
          // Numeric operators: =, !=, <, <=, >, >=
          // Check if value looks like a number
          const isNumeric = /^-?\d+\.?\d*$/.test(c.value.trim())
          const formattedValue = isNumeric ? c.value.trim() : escapeLiteral(c.value)
          return `${column} ${c.operator} ${formattedValue}`
        }
      }
    })

  if (clauses.length === 0) return ''

  return '\nWHERE ' + clauses.join(`\n  ${conditionLogic.value} `)
}

const buildOrderByClause = (): string => {
  if (orderBy.value.length === 0) return ''

  const clauses = orderBy.value.filter((o) => o.column).map((o) => `${escapeIdentifier(o.column)} ${o.direction}`)

  if (clauses.length === 0) return ''

  return '\nORDER BY ' + clauses.join(', ')
}

const generateSql = () => {
  if (!canGenerateSql.value) return

  // Build SELECT clause
  const columns =
    selectedColumns.value.length === availableColumns.value.length
      ? '*'
      : selectedColumns.value.map(escapeIdentifier).join(', ')

  let sql = `SELECT ${columns}\nFROM ${escapeIdentifier(selectedTable.value)}`

  // Add WHERE clause
  sql += buildWhereClause()

  // Add ORDER BY clause
  sql += buildOrderByClause()

  // Add LIMIT
  if (limit.value > 0) {
    sql += `\nLIMIT ${limit.value}`
  }

  generatedSql.value = sql
}

const useGeneratedSql = () => {
  if (generatedSql.value && selectedDataSource.value) {
    emit('use-query', generatedSql.value, selectedDataSource.value)
  }
}

const resetBuilder = () => {
  selectedDataSource.value = ''
  selectedTable.value = ''
  selectedColumns.value = []
  conditions.value = []
  orderBy.value = []
  limit.value = 100
  generatedSql.value = ''
  tables.value = []
  availableColumns.value = []
}

// Auto-generate SQL when selections change
watch(
  [selectedColumns, conditions, conditionLogic, orderBy, limit],
  () => {
    if (canGenerateSql.value) {
      generateSql()
    }
  },
  { deep: true }
)
</script>

<style scoped>
.sql-preview {
  background-color: rgb(var(--v-theme-surface-variant));
  padding: 12px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  overflow-x: auto;
  white-space: pre;
}

.gap-2 {
  gap: 8px;
}
</style>
