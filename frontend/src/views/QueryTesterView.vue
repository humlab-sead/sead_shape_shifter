<template>
  <v-container fluid class="pa-6">
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center mb-4">
          <v-icon size="large" class="mr-3">mdi-database-search</v-icon>
          <div>
            <h1 class="text-h4">SQL Query Tester</h1>
            <p class="text-subtitle-1 text-grey">Test SQL queries against your data sources</p>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Query Input Tabs -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-tabs v-model="activeTab" bg-color="primary">
            <v-tab value="editor">
              <v-icon class="mr-2">mdi-code-tags</v-icon>
              SQL Editor
            </v-tab>
            <v-tab value="builder">
              <v-icon class="mr-2">mdi-database-cog</v-icon>
              Visual Builder
            </v-tab>
          </v-tabs>

          <v-window v-model="activeTab">
            <!-- SQL Editor Tab -->
            <v-window-item value="editor">
              <div class="pa-4">
                <QueryEditor
                  :key="editorKey"
                  :initial-query="initialQuery"
                  :initial-data-source="initialDataSource"
                  @result="handleQueryResult"
                  @error="handleQueryError"
                />
              </div>
            </v-window-item>

            <!-- Visual Builder Tab -->
            <v-window-item value="builder">
              <div class="pa-4">
                <QueryBuilder @use-query="handleUseQuery" />
              </div>
            </v-window-item>
          </v-window>
        </v-card>
      </v-col>
    </v-row>

    <!-- Query Results -->
    <v-row>
      <v-col v-if="queryResult || showResults" cols="12">
        <QueryResults :result="queryResult" />
      </v-col>
    </v-row>

    <!-- Help Section -->
    <v-row>
      <v-col cols="12">
        <v-expansion-panels>
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon start>mdi-help-circle-outline</v-icon>
              Query Tester Help
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-row>
                <v-col cols="12" md="6">
                  <h3 class="text-h6 mb-2">Keyboard Shortcuts</h3>
                  <v-list density="compact">
                    <v-list-item>
                      <v-list-item-title> <kbd>Ctrl</kbd> + <kbd>Enter</kbd> (⌘ + Enter on Mac) </v-list-item-title>
                      <v-list-item-subtitle>Execute query</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-col>

                <v-col cols="12" md="6">
                  <h3 class="text-h6 mb-2">Security & Limits</h3>
                  <v-list density="compact">
                    <v-list-item>
                      <v-list-item-title>Only SELECT queries allowed</v-list-item-title>
                      <v-list-item-subtitle> INSERT, UPDATE, DELETE, DROP are blocked for safety </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title>Results limited to 10,000 rows</v-list-item-title>
                      <v-list-item-subtitle> Prevents excessive memory usage </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title>30 second timeout</v-list-item-title>
                      <v-list-item-subtitle> Queries exceeding this will be cancelled </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-col>

                <v-col cols="12">
                  <h3 class="text-h6 mb-2 mt-4">Example Queries</h3>
                  <v-list density="compact">
                    <v-list-item
                      v-for="example in exampleQueries"
                      :key="example.title"
                      @click="loadExample(example.query)"
                      class="cursor-pointer"
                    >
                      <template #prepend>
                        <v-icon>mdi-code-tags</v-icon>
                      </template>
                      <v-list-item-title>{{ example.title }}</v-list-item-title>
                      <v-list-item-subtitle>{{ example.description }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-col>
    </v-row>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false"> Close </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import QueryEditor from '@/components/query/QueryEditor.vue'
import QueryBuilder from '@/components/query/QueryBuilder.vue'
import QueryResults from '@/components/query/QueryResults.vue'
import type { QueryResult } from '@/types/query'

const route = useRoute()

// State
const activeTab = ref<'editor' | 'builder'>('editor')
const queryResult = ref<QueryResult | null>(null)
const showResults = ref(false)
const editorKey = ref(0) // For forcing re-render
const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
})

// Initial values from route params
const initialQuery = ref((route.query.query as string) || '')
const initialDataSource = ref((route.query.dataSource as string) || '')

// Example queries
const exampleQueries = [
  {
    title: 'Select all rows',
    description: 'Retrieve all columns from a table',
    query: 'SELECT * FROM table_name LIMIT 100',
  },
  {
    title: 'Filter with WHERE',
    description: 'Select rows matching a condition',
    query: 'SELECT * FROM table_name WHERE column_name = value',
  },
  {
    title: 'Join tables',
    description: 'Combine data from multiple tables',
    query: `SELECT t1.*, t2.column
FROM table1 t1
JOIN table2 t2 ON t1.id = t2.foreign_id`,
  },
  {
    title: 'Aggregate with GROUP BY',
    description: 'Count or sum values by group',
    query: `SELECT category, COUNT(*) as count
FROM table_name
GROUP BY category
ORDER BY count DESC`,
  },
  {
    title: 'Date filtering',
    description: 'Filter by date range',
    query: `SELECT *
FROM table_name
WHERE created_at >= '2024-01-01'
  AND created_at < '2024-02-01'`,
  },
]

// Methods
function handleQueryResult(result: QueryResult) {
  queryResult.value = result
  showResults.value = true
  snackbar.value = {
    show: true,
    message: `Query executed successfully: ${result.row_count} rows returned`,
    color: 'success',
  }
}

function handleQueryError(error: string) {
  snackbar.value = {
    show: true,
    message: error,
    color: 'error',
  }
}

function handleUseQuery(sql: string, dataSource: string) {
  // Switch to editor tab and populate with generated SQL
  activeTab.value = 'editor'
  initialQuery.value = sql
  initialDataSource.value = dataSource
  editorKey.value++ // Force re-render

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' })

  // Show success message
  snackbar.value = {
    show: true,
    message: 'SQL query loaded into editor. Click "Execute Query" to run it.',
    color: 'success',
  }
}

function loadExample(query: string) {
  initialQuery.value = query
  editorKey.value++ // Force re-render
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<style scoped>
kbd {
  background-color: rgb(var(--v-theme-surface-variant));
  border: 1px solid rgb(var(--v-theme-outline));
  border-radius: 3px;
  padding: 2px 6px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
}

.cursor-pointer {
  cursor: pointer;
}

.cursor-pointer:hover {
  background-color: rgba(var(--v-theme-primary), 0.1);
}
</style>
