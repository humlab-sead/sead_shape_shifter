<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon icon="mdi-table-cog" class="mr-2" />
      {{ tableSchema?.table_name || 'Table Details' }}
      <v-spacer />
      <v-btn
        icon="mdi-refresh"
        size="small"
        variant="text"
        :loading="loading"
        :disabled="!dataSource || !tableName"
        @click="refreshSchema"
      />
    </v-card-title>

    <v-card-text>
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" />
        <p class="text-caption mt-2">Loading schema...</p>
      </div>

      <!-- Error Display -->
      <v-alert
        v-else-if="error"
        type="error"
        variant="tonal"
        density="compact"
        closable
        @click:close="clearError"
      >
        {{ error }}
      </v-alert>

      <!-- Empty State -->
      <v-alert
        v-else-if="!tableSchema"
        type="info"
        variant="tonal"
        density="compact"
      >
        Select a table to view its schema
      </v-alert>

      <!-- Schema Details -->
      <div v-else>
        <!-- Table Info -->
        <v-list density="compact" class="mb-4">
          <v-list-item>
            <template #prepend>
              <v-icon icon="mdi-table" size="small" />
            </template>
            <v-list-item-title>Table Name</v-list-item-title>
            <v-list-item-subtitle>{{ tableSchema.table_name }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="tableSchema.schema">
            <template #prepend>
              <v-icon icon="mdi-folder-outline" size="small" />
            </template>
            <v-list-item-title>Schema</v-list-item-title>
            <v-list-item-subtitle>{{ tableSchema.schema }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="tableSchema.row_count !== null && tableSchema.row_count !== undefined">
            <template #prepend>
              <v-icon icon="mdi-counter" size="small" />
            </template>
            <v-list-item-title>Row Count</v-list-item-title>
            <v-list-item-subtitle>{{ tableSchema.row_count.toLocaleString() }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="tableSchema.comment">
            <template #prepend>
              <v-icon icon="mdi-comment-text-outline" size="small" />
            </template>
            <v-list-item-title>Comment</v-list-item-title>
            <v-list-item-subtitle>{{ tableSchema.comment }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <!-- Primary Keys -->
        <v-card v-if="tableSchema.primary_keys.length > 0" variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-1">
            <v-icon icon="mdi-key" size="small" class="mr-2" />
            Primary Keys
          </v-card-title>
          <v-card-text>
            <v-chip
              v-for="pk in tableSchema.primary_keys"
              :key="pk"
              size="small"
              color="amber"
              class="mr-1 mb-1"
            >
              {{ pk }}
            </v-chip>
          </v-card-text>
        </v-card>

        <!-- Columns -->
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1 d-flex align-center flex-wrap">
            <v-icon icon="mdi-table-column" size="small" class="mr-2" />
            Columns ({{ tableSchema.columns.length }})
            <v-spacer />
            <v-btn
              v-if="!showTypeMappings"
              prepend-icon="mdi-account-convert"
              size="small"
              variant="outlined"
              color="primary"
              :loading="loadingTypeMappings"
              @click="loadTypeMappings"
              class="mr-2"
            >
              Show Type Suggestions
            </v-btn>
            <v-btn
              v-else
              prepend-icon="mdi-close"
              size="small"
              variant="text"
              @click="showTypeMappings = false"
              class="mr-2"
            >
              Hide Suggestions
            </v-btn>
            <v-text-field
              v-model="columnSearchQuery"
              label="Search columns"
              density="compact"
              variant="outlined"
              clearable
              hide-details
              style="max-width: 250px"
            >
              <template #prepend-inner>
                <v-icon icon="mdi-magnify" size="small" />
              </template>
            </v-text-field>
          </v-card-title>

          <v-divider />

          <v-list density="compact">
            <v-list-item
              v-for="column in filteredColumns"
              :key="column.name"
              class="column-item"
            >
              <template #prepend>
                <v-icon
                  :icon="getColumnIcon(column)"
                  :color="getColumnColor(column)"
                  size="small"
                />
              </template>

              <v-list-item-title>
                <span class="font-weight-medium">{{ column.name }}</span>
                <v-chip
                  v-if="column.is_primary_key"
                  size="x-small"
                  color="amber"
                  class="ml-2"
                >
                  PK
                </v-chip>
              </v-list-item-title>

              <v-list-item-subtitle>
                <div class="d-flex align-center flex-wrap">
                  <span class="text-monospace mr-2">{{ formatDataType(column) }}</span>
                  <v-chip
                    v-if="column.default"
                    size="x-small"
                    variant="outlined"
                    class="mr-1"
                  >
                    default: {{ column.default }}
                  </v-chip>
                  <v-chip
                    v-if="column.comment"
                    size="x-small"
                    variant="text"
                  >
                    {{ column.comment }}
                  </v-chip>
                </div>
                <!-- Type Mapping Suggestion -->
                <div v-if="showTypeMappings && typeMappings[column.name]" class="mt-2">
                  <v-chip
                    size="small"
                    :color="getConfidenceColor(typeMappings[column.name]?.confidence ?? 0)"
                    variant="flat"
                    class="mr-1"
                  >
                    <v-icon icon="mdi-arrow-right-thin" size="small" class="mr-1" />
                    {{ typeMappings[column.name]?.suggested_type }}
                    <v-tooltip activator="parent" location="bottom">
                      {{ typeMappings[column.name]?.reason }}
                      <br>Confidence: {{ ((typeMappings[column.name]?.confidence ?? 0) * 100).toFixed(0) }}%
                    </v-tooltip>
                  </v-chip>
                  <span v-if="(typeMappings[column.name]?.alternatives?.length ?? 0) > 0" class="text-caption text-grey">
                    or {{ typeMappings[column.name]?.alternatives?.join(', ') }}
                  </span>
                </div>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>

        <!-- Foreign Keys -->
        <v-card
          v-if="tableSchema.foreign_keys && tableSchema.foreign_keys.length > 0"
          variant="outlined"
          class="mt-4"
        >
          <v-card-title class="text-subtitle-1">
            <v-icon icon="mdi-link-variant" size="small" class="mr-2" />
            Foreign Keys
          </v-card-title>
          <v-list density="compact">
            <v-list-item
              v-for="(fk, index) in tableSchema.foreign_keys"
              :key="index"
            >
              <template #prepend>
                <v-icon icon="mdi-arrow-right-thin" size="small" />
              </template>
              <v-list-item-title>
                {{ fk.column }} → {{ fk.referenced_table }}.{{ fk.referenced_column }}
              </v-list-item-title>
              <v-list-item-subtitle v-if="fk.name">
                {{ fk.name }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>

        <!-- Indexes -->
        <v-card
          v-if="tableSchema.indexes && tableSchema.indexes.length > 0"
          variant="outlined"
          class="mt-4"
        >
          <v-card-title class="text-subtitle-1">
            <v-icon icon="mdi-speedometer" size="small" class="mr-2" />
            Indexes
          </v-card-title>
          <v-list density="compact">
            <v-list-item
              v-for="index in tableSchema.indexes"
              :key="index.name"
            >
              <template #prepend>
                <v-icon
                  :icon="index.is_unique ? 'mdi-key-variant' : 'mdi-speedometer'"
                  size="small"
                />
              </template>
              <v-list-item-title>
                {{ index.name }}
                <v-chip
                  v-if="index.is_unique"
                  size="x-small"
                  color="blue"
                  class="ml-2"
                >
                  UNIQUE
                </v-chip>
                <v-chip
                  v-if="index.is_primary"
                  size="x-small"
                  color="amber"
                  class="ml-2"
                >
                  PRIMARY
                </v-chip>
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ index.columns.join(', ') }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useDataSourceStore } from '@/stores/data-source'
import schemaApi from '@/api/schema'
import type { TableSchema, TypeMapping } from '@/types/schema'
import {
  formatDataType,
  getColumnIcon,
  getColumnColor,
} from '@/types/schema'

// Props
interface Props {
  dataSource?: string
  tableName?: string
  schema?: string
  autoLoad?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  autoLoad: true,
})

// Store
const dataSourceStore = useDataSourceStore()

// State
const tableSchema = ref<TableSchema | null>(null)
const columnSearchQuery = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

// Type mappings state
const typeMappings = ref<Record<string, TypeMapping>>({})
const showTypeMappings = ref(false)
const loadingTypeMappings = ref(false)

// Computed
const filteredColumns = computed(() => {
  if (!tableSchema.value) return []
  if (!columnSearchQuery.value) return tableSchema.value.columns

  const query = columnSearchQuery.value.toLowerCase()
  return tableSchema.value.columns.filter((column) =>
    column.name.toLowerCase().includes(query) ||
    column.data_type.toLowerCase().includes(query) ||
    (column.comment && column.comment.toLowerCase().includes(query))
  )
})

// Methods
async function loadSchema() {
  if (!props.dataSource || !props.tableName) return

  loading.value = true
  error.value = null

  try {
    tableSchema.value = await dataSourceStore.fetchTableSchema(
      props.dataSource,
      props.tableName,
      props.schema
    )
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load table schema'
    tableSchema.value = null
  } finally {
    loading.value = false
  }
}

function refreshSchema() {
  if (props.dataSource) {
    // Invalidate cache and reload
    dataSourceStore.invalidateSchemaCache(props.dataSource)
      .then(() => loadSchema())
      .catch((e) => {
        error.value = e instanceof Error ? e.message : 'Failed to refresh schema'
      })
  }
}

function clearError() {
  error.value = null
}

async function loadTypeMappings() {
  if (!props.dataSource || !props.tableName) return

  loadingTypeMappings.value = true

  try {
    typeMappings.value = await schemaApi.getTypeMappings(
      props.dataSource,
      props.tableName,
      { schema: props.schema }
    )
    showTypeMappings.value = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load type mappings'
  } finally {
    loadingTypeMappings.value = false
  }
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'green'
  if (confidence >= 0.7) return 'blue'
  if (confidence >= 0.5) return 'orange'
  return 'grey'
}

// Watchers
watch(
  () => [props.dataSource, props.tableName, props.schema],
  () => {
    if (props.autoLoad) {
      loadSchema()
    }
  },
  { immediate: props.autoLoad }
)

// Expose methods for parent components
defineExpose({
  loadSchema,
  refreshSchema,
})
</script>

<style scoped>
.column-item {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.column-item:last-child {
  border-bottom: none;
}

.text-monospace {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}
</style>
