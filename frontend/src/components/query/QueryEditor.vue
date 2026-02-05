<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2">mdi-database-search</v-icon>
      Query Editor
      <v-spacer />
      <v-chip v-if="validation" :color="validation.is_valid ? 'success' : 'error'" size="small" class="mr-2">
        {{ validation.is_valid ? 'Valid' : 'Invalid' }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <!-- Data Source Selector -->
      <v-select
        v-model="selectedDataSource"
        :items="dataSourceNames"
        label="Data Source"
        prepend-icon="mdi-database"
        density="comfortable"
        class="mb-4"
        :disabled="executing"
      />

      <!-- SQL Editor -->
      <div class="sql-editor-container mb-4">
        <div class="text-caption text-grey mb-2">SQL Query</div>
        <vue-monaco-editor
          v-model:value="query"
          language="sql"
          :options="editorOptions"
          height="300px"
          @mount="handleEditorMount"
        />
        <!-- Line numbers hint -->
        <div class="text-caption text-grey mt-2">Press Ctrl+Enter (⌘+Enter on Mac) to execute query</div>
      </div>

      <!-- Validation Messages -->
      <v-alert
        v-if="validation && validation.errors.length > 0"
        type="error"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        <div class="text-subtitle-2 mb-2">Validation Errors:</div>
        <ul class="pl-4">
          <li v-for="(error, idx) in validation.errors" :key="idx">
            {{ error }}
          </li>
        </ul>
      </v-alert>

      <v-alert
        v-if="validation && validation.warnings.length > 0"
        type="warning"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        <div class="text-subtitle-2 mb-2">Warnings:</div>
        <ul class="pl-4">
          <li v-for="(warning, idx) in validation.warnings" :key="idx">
            {{ warning }}
          </li>
        </ul>
      </v-alert>

      <!-- Query Info -->
      <v-row v-if="validation && validation.statement_type" class="mb-4">
        <v-col cols="12" md="6">
          <v-chip size="small" label>
            <v-icon start size="small">mdi-code-braces</v-icon>
            {{ validation.statement_type }}
          </v-chip>
        </v-col>
        <v-col v-if="validation.tables.length > 0" cols="12" md="6">
          <v-chip v-for="table in validation.tables" :key="table" size="small" class="mr-1" label>
            <v-icon start size="small">mdi-table</v-icon>
            {{ table }}
          </v-chip>
        </v-col>
      </v-row>

      <!-- Action Buttons -->
      <v-row>
        <v-col cols="12" class="d-flex gap-2">
          <v-btn
            color="primary"
            :loading="executing"
            :disabled="!selectedDataSource || !query || executing"
            @click="executeQuery"
          >
            <v-icon start>mdi-play</v-icon>
            Execute Query
          </v-btn>

          <v-btn
            variant="outlined"
            :loading="validating"
            :disabled="!selectedDataSource || !query || validating"
            @click="validateQueryOnly"
          >
            <v-icon start>mdi-check-circle-outline</v-icon>
            Validate
          </v-btn>

          <v-spacer />

          <v-btn variant="text" :disabled="!query" @click="clearQuery">
            <v-icon start>mdi-close</v-icon>
            Clear
          </v-btn>
        </v-col>
      </v-row>

      <!-- Execution Stats -->
      <v-row v-if="lastResult" class="mt-2">
        <v-col cols="12">
          <v-alert type="success" variant="tonal" density="compact">
            <div class="d-flex align-center">
              <v-icon start>mdi-check-circle</v-icon>
              <span>
                Query executed successfully in {{ lastResult.execution_time_ms }}ms • {{ lastResult.row_count }}
                {{ lastResult.row_count === 1 ? 'row' : 'rows' }}
                <span v-if="lastResult.is_truncated" class="text-warning">
                  (truncated at {{ lastResult.row_count }} rows)
                </span>
              </span>
            </div>
          </v-alert>
        </v-col>
      </v-row>

      <!-- Error Display -->
      <!-- @ts-ignore -->
      <ErrorAlert
        v-if="error"
        v-bind="errorProps"
        closable
        show-context
        @close="clearError"
        class="mt-4"
      />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { useDataSourceStore } from '@/stores/data-source'
import { queryApi } from '@/api/query'
import { useErrorHandler } from '@/composables'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import type { QueryResult, QueryValidation } from '@/types/query'
import type * as monacoType from 'monaco-editor'

const props = defineProps<{
  initialQuery?: string
  initialDataSource?: string
}>()

const emit = defineEmits<{
  result: [result: QueryResult]
  error: [error: string]
}>()

const dataSourceStore = useDataSourceStore()

// Error handling
const { error, errorProps, handleError, clearError } = useErrorHandler({
  showContext: true,
})

// State
const query = ref(props.initialQuery || '')
const selectedDataSource = ref(props.initialDataSource || '')
const validation = ref<QueryValidation | null>(null)
const lastResult = ref<QueryResult | null>(null)
const executing = ref(false)
const validating = ref(false)

// Computed
const dataSourceNames = computed(() => dataSourceStore.dataSources.map((ds) => ds.name))

// Monaco editor configuration
const editorOptions = {
  automaticLayout: true,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  fontSize: 14,
  lineNumbers: 'on' as const,
  roundedSelection: false,
  readOnly: false,
  theme: 'vs-dark',
  wordWrap: 'on' as const,
  folding: true,
  tabSize: 2,
  insertSpaces: true,
  scrollbar: {
    vertical: 'auto' as const,
    horizontal: 'auto' as const,
  },
  suggestOnTriggerCharacters: true,
  quickSuggestions: true,
  model: null,
}

function handleEditorMount(editorInstance: monacoType.editor.IStandaloneCodeEditor, monacoRef: typeof monacoType) {
  // Add keyboard shortcut for executing query (Ctrl+Enter or Cmd+Enter)
  editorInstance.addCommand(monacoRef.KeyMod.CtrlCmd | monacoRef.KeyCode.Enter, () => {
    executeQuery()
  })
}

// Methods
async function executeQuery() {
  if (!selectedDataSource.value || !query.value) return

  executing.value = true
  clearError()
  lastResult.value = null

  try {
    const result = await queryApi.executeQuery(selectedDataSource.value, {
      query: query.value,
      limit: 100,
      timeout: 30,
    })

    lastResult.value = result
    emit('result', result)

    // Auto-validate on successful execution
    await validateQueryOnly()
  } catch (err: any) {
    handleError(err)
    emit('error', err.response?.data?.message || err.message || 'Query execution failed')
  } finally {
    executing.value = false
  }
}

async function validateQueryOnly() {
  if (!selectedDataSource.value || !query.value) return

  validating.value = true
  clearError()

  try {
    validation.value = await queryApi.validateQuery(selectedDataSource.value, { query: query.value })
  } catch (err: any) {
    handleError(err)
  } finally {
    validating.value = false
  }
}


function clearQuery() {
  query.value = ''
  validation.value = null
  lastResult.value = null
  clearError()
}

// Load data sources on mount
onMounted(async () => {
  if (dataSourceStore.dataSources.length === 0) {
    await dataSourceStore.fetchDataSources()
  }

  // Select first data source if none selected
  if (!selectedDataSource.value && dataSourceNames.value.length > 0) {
    const firstDataSource = dataSourceNames.value[0]
    if (firstDataSource) {
      selectedDataSource.value = firstDataSource
    }
  }
})
</script>

<style scoped>
.sql-editor-container {
  position: relative;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  overflow: hidden;
}

.query-plan {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  background-color: rgb(var(--v-theme-surface-variant));
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
