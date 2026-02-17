<template>
  <v-container fluid class="pa-4 schema-explorer-container">
    <div class="d-flex align-center mb-4">
      <v-icon icon="mdi-database-search" size="large" class="mr-3" />
      <h1 class="text-h4">Schema Explorer</h1>
      <v-spacer />
      <v-btn prepend-icon="mdi-refresh" variant="outlined" :loading="refreshing" @click="refreshAll">
        Refresh All
      </v-btn>
    </div>

    <v-row>
      <!-- Left Panel: Table Selector with Embedded Details -->
      <v-col cols="12" md="3">
        <SchemaTreeView :auto-load="true" @table-selected="onTableSelected">
          <template #details>
            <TableDetailsPanel
              ref="detailsPanel"
              :data-source="selectedDataSource ?? undefined"
              :table-name="selectedTable ?? undefined"
              :schema="selectedSchema"
              :auto-load="true"
              embedded
            />
          </template>
        </SchemaTreeView>
      </v-col>

      <!-- Right Panel: Data Preview (Expanded) -->
      <v-col cols="12" md="9">
        <DataPreviewTable
          ref="previewTable"
          :data-source="selectedDataSource ?? undefined"
          :table-name="selectedTable ?? undefined"
          :schema="selectedSchema"
          :auto-load="true"
          :default-limit="50"
        />
      </v-col>
    </v-row>

    <!-- Help Dialog -->
    <v-dialog v-model="showHelp" max-width="600">
      <template #activator="{ props: activatorProps }">
        <v-btn
          icon="mdi-help-circle"
          size="small"
          variant="text"
          v-bind="activatorProps"
          style="position: fixed; bottom: 20px; right: 20px"
        />
      </template>

      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon icon="mdi-help-circle" class="mr-2" />
          Schema Explorer Help
        </v-card-title>

        <v-card-text>
          <h3 class="text-h6 mb-2">How to Use</h3>

          <div class="mb-4">
            <p class="font-weight-medium mb-1">1. Select a Data Source</p>
            <p class="text-body-2 text-grey-darken-1">
              Choose a database data source from the dropdown in the left panel. Only database sources (PostgreSQL, MS
              Access, SQLite) are available.
            </p>
          </div>

          <div class="mb-4">
            <p class="font-weight-medium mb-1">2. Browse Tables</p>
            <p class="text-body-2 text-grey-darken-1">
              Tables will load automatically. Select a table from the dropdown to view its details. For PostgreSQL, you can
              specify a schema (defaults to 'public').
            </p>
          </div>

          <div class="mb-4">
            <p class="font-weight-medium mb-1">3. View Table Details</p>
            <p class="text-body-2 text-grey-darken-1">
              Select a table to automatically view its column details below the table selector and preview data in the right panel. You'll see:
            </p>
            <ul class="text-body-2 text-grey-darken-1 ml-4">
              <li>Column names and data types</li>
              <li>Primary keys (marked with PK)</li>
              <li>Nullable columns</li>
              <li>Default values</li>
              <li>Foreign keys (if available)</li>
              <li>Indexes (if available)</li>
            </ul>
          </div>

          <div class="mb-4">
            <p class="font-weight-medium mb-1">4. Preview Data</p>
            <p class="text-body-2 text-grey-darken-1">
              The right panel automatically shows sample rows from the selected table. Use pagination controls to navigate through the
              data. You can adjust rows per page (10, 25, 50, or 100). Data preview clears when switching tables.
            </p>
          </div>

          <div class="mb-4">
            <p class="font-weight-medium mb-1">5. Refresh Data</p>
            <p class="text-body-2 text-grey-darken-1">
              Use the refresh button in each panel to reload data manually. The "Refresh All" button at the top clears the cache and reloads everything.
            </p>
          </div>

          <h3 class="text-h6 mb-2 mt-4">Icon Legend</h3>

          <div class="d-flex align-center mb-2">
            <v-icon icon="mdi-key" color="amber" size="small" class="mr-2" />
            <span class="text-body-2">Primary Key</span>
          </div>

          <div class="d-flex align-center mb-2">
            <v-icon icon="mdi-numeric" color="blue" size="small" class="mr-2" />
            <span class="text-body-2">Numeric Type</span>
          </div>

          <div class="d-flex align-center mb-2">
            <v-icon icon="mdi-format-text" size="small" class="mr-2" />
            <span class="text-body-2">Text Type</span>
          </div>

          <div class="d-flex align-center mb-2">
            <v-icon icon="mdi-calendar-clock" size="small" class="mr-2" />
            <span class="text-body-2">Date/Time Type</span>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showHelp = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useDataSourceStore } from '@/stores/data-source'
import SchemaTreeView from '@/components/SchemaTreeView.vue'
import TableDetailsPanel from '@/components/TableDetailsPanel.vue'
import DataPreviewTable from '@/components/DataPreviewTable.vue'
import type { TableMetadata } from '@/types/schema'

// Store
const dataSourceStore = useDataSourceStore()

// State
const selectedDataSource = ref<string | null>(null)
const selectedTable = ref<string | null>(null)
const selectedSchema = ref<string | undefined>(undefined)
const refreshing = ref(false)
const showHelp = ref(false)

// Refs to child components
const detailsPanel = ref<InstanceType<typeof TableDetailsPanel> | null>(null)
const previewTable = ref<InstanceType<typeof DataPreviewTable> | null>(null)

// Methods
function onTableSelected(table: TableMetadata, dataSource: string, schema?: string) {
  selectedDataSource.value = dataSource
  selectedTable.value = table.name
  selectedSchema.value = schema
  // Schema and preview will automatically load via watchers since auto-load="true"
}

async function refreshAll() {
  if (!selectedDataSource.value) return

  refreshing.value = true
  try {
    // Invalidate cache
    await dataSourceStore.invalidateSchemaCache(selectedDataSource.value)

    // Reload everything
    if (selectedTable.value) {
      await Promise.all([detailsPanel.value?.refreshSchema(), previewTable.value?.refreshData()])
    }
  } catch (error) {
    console.error('Failed to refresh:', error)
  } finally {
    refreshing.value = false
  }
}
</script>

<style scoped>
.schema-explorer-container {
  max-width: 100%;
  height: calc(100vh - 100px); /* Subtract app bar height + margin */
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.v-row {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.v-col {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
</style>
