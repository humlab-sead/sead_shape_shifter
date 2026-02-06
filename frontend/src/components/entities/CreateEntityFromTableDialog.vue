<template>
  <v-dialog v-model="internalDialog" max-width="700" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-table-arrow-right" class="mr-2" />
        Create Entity from Table
      </v-card-title>

      <v-card-subtitle> Generate a new entity configuration from a database table </v-card-subtitle>

      <v-divider />

      <v-card-text>
        <!-- Data Source Display -->
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          <div class="d-flex align-center">
            <v-icon icon="mdi-database" class="mr-2" />
            <strong>Data Source:</strong>
            <span class="ml-2">{{ dataSource }}</span>
          </div>
        </v-alert>

        <!-- Table Selection -->
        <v-autocomplete
          v-model="selectedTable"
          :items="tables"
          :loading="loadingTables"
          label="Select Table"
          placeholder="Search tables..."
          item-title="name"
          item-value="name"
          variant="outlined"
          density="comfortable"
          clearable
          auto-select-first
          @update:model-value="onTableSelected"
        >
          <template #item="{ props, item }">
            <v-list-item v-bind="props">
              <template #prepend>
                <v-icon icon="mdi-table" />
              </template>
              <template #subtitle>
                <span v-if="item.raw.row_count !== null" class="text-caption">
                  {{ formatRowCount(item.raw.row_count || 0) }} rows
                </span>
                <span v-if="item.raw.schema_name" class="text-caption ml-2"> • {{ item.raw.schema_name }} </span>
              </template>
            </v-list-item>
          </template>

          <template #no-data>
            <v-list-item>
              <v-list-item-title class="text-grey">
                {{ loadingTables ? 'Loading tables...' : 'No tables found' }}
              </v-list-item-title>
            </v-list-item>
          </template>
        </v-autocomplete>

        <!-- Entity Name -->
        <v-text-field
          v-model="entityName"
          label="Entity Name"
          hint="Defaults to table name if not specified"
          persistent-hint
          variant="outlined"
          density="comfortable"
          clearable
          :disabled="!selectedTable"
        />

        <!-- Preview Configuration -->
        <div v-if="previewConfig" class="mt-4">
          <v-label class="text-caption mb-2">Preview Configuration</v-label>
          <div class="preview-box">
            <pre class="preview-yaml">{{ previewConfig }}</pre>
          </div>
        </div>

        <!-- Error Display -->
        <v-alert v-if="error" type="error" variant="tonal" class="mt-4">
          {{ error }}
        </v-alert>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="handleCancel"> Cancel </v-btn>
        <v-btn color="primary" :disabled="!selectedTable || creating" :loading="creating" @click="handleCreate">
          Create Entity
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import yaml from 'js-yaml'
import { schemaApi } from '@/api/schema'
import { entitiesApi } from '@/api/entities'
import type { TableMetadata, TableSchema } from '@/types/schema'

const props = defineProps<{
  modelValue: boolean
  projectName: string
  dataSource: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [entityName: string]
}>()

// State
const loadingTables = ref(false)
const creating = ref(false)
const tables = ref<TableMetadata[]>([])
const selectedTable = ref<string | null>(null)
const entityName = ref<string>('')
const error = ref<string | null>(null)
const selectedTableSchema = ref<TableSchema | null>(null)

// Computed
const internalDialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const previewConfig = computed(() => {
  if (!selectedTable.value || !selectedTableSchema.value) return null

  const primaryKeys = selectedTableSchema.value.columns.filter((col) => col.is_primary_key).map((col) => col.name)

  const schema = tables.value.find((t) => t.name === selectedTable.value)?.schema_name
  const fullTableName = schema ? `${schema}.${selectedTable.value}` : selectedTable.value

  const config = {
    type: 'sql',
    data_source: props.dataSource,
    query: `SELECT * FROM ${fullTableName}`,
    keys: primaryKeys,
    public_id: `${selectedTable.value}_id`,
  }

  return yaml.dump(config, { indent: 2, lineWidth: -1 })
})

// Methods
async function loadTables() {
  loadingTables.value = true
  error.value = null

  try {
    tables.value = await schemaApi.listTables(props.dataSource)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load tables'
    tables.value = []
  } finally {
    loadingTables.value = false
  }
}

async function onTableSelected(tableName: string | null) {
  if (!tableName) {
    selectedTableSchema.value = null
    entityName.value = ''
    return
  }

  // Auto-fill entity name if empty
  if (!entityName.value) {
    entityName.value = tableName
  }

  // Fetch table schema to get primary keys
  try {
    const schema = tables.value.find((t) => t.name === tableName)?.schema_name
    selectedTableSchema.value = await schemaApi.getTableSchema(props.dataSource, tableName, schema ? { schema } : undefined)
  } catch (e) {
    console.warn('Failed to fetch table schema:', e)
    selectedTableSchema.value = null
  }
}

async function handleCreate() {
  if (!selectedTable.value) return

  creating.value = true
  error.value = null

  try {
    const schema = tables.value.find((t) => t.name === selectedTable.value)?.schema_name

    await entitiesApi.generateFromTable(props.projectName, {
      data_source: props.dataSource,
      table_name: selectedTable.value,
      entity_name: entityName.value || undefined,
      schema: schema || undefined,
    })

    const createdEntityName = entityName.value || selectedTable.value
    emit('created', createdEntityName)
    handleCancel()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to create entity'
  } finally {
    creating.value = false
  }
}

function handleCancel() {
  // Reset state
  selectedTable.value = null
  entityName.value = ''
  error.value = null
  selectedTableSchema.value = null

  // Close dialog
  internalDialog.value = false
}

function formatRowCount(count: number | null): string {
  if (count === null) return 'Unknown'
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
  return count.toString()
}

// Watch dialog opening to load tables
watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      loadTables()
    }
  }
)
</script>

<style scoped>
.preview-box {
  background-color: rgb(var(--v-theme-surface-variant));
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
}

.preview-yaml {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
