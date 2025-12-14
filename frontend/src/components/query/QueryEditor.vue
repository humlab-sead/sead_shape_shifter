<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2">mdi-database-search</v-icon>
      Query Editor
      <v-spacer />
      <v-chip
        v-if="validation"
        :color="validation.is_valid ? 'success' : 'error'"
        size="small"
        class="mr-2"
      >
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
      <div class="sql-editor-container">
        <v-textarea
          v-model="query"
          label="SQL Query"
          placeholder="SELECT * FROM table_name WHERE ..."
          rows="10"
          variant="outlined"
          :disabled="executing"
          @keydown.ctrl.enter.prevent="executeQuery"
          @keydown.meta.enter.prevent="executeQuery"
          class="sql-editor"
          auto-grow
        >
          <template #prepend-inner>
            <v-icon size="small" color="grey">mdi-code-tags</v-icon>
          </template>
        </v-textarea>

        <!-- Line numbers hint -->
        <div class="text-caption text-grey mt-n2 mb-2">
          Press Ctrl+Enter (⌘+Enter on Mac) to execute query
        </div>
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
          <v-chip
            v-for="table in validation.tables"
            :key="table"
            size="small"
            class="mr-1"
            label
          >
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

          <v-btn
            variant="outlined"
            :loading="explaining"
            :disabled="!selectedDataSource || !query || explaining"
            @click="explainQueryPlan"
          >
            <v-icon start>mdi-chart-timeline-variant</v-icon>
            Explain
          </v-btn>

          <v-spacer />

          <v-btn
            variant="text"
            :disabled="!query"
            @click="clearQuery"
          >
            <v-icon start>mdi-close</v-icon>
            Clear
          </v-btn>
        </v-col>
      </v-row>

      <!-- Execution Stats -->
      <v-row v-if="lastResult" class="mt-2">
        <v-col cols="12">
          <v-alert
            type="success"
            variant="tonal"
            density="compact"
          >
            <div class="d-flex align-center">
              <v-icon start>mdi-check-circle</v-icon>
              <span>
                Query executed successfully in {{ lastResult.execution_time_ms }}ms
                • {{ lastResult.row_count }} {{ lastResult.row_count === 1 ? 'row' : 'rows' }}
                <span v-if="lastResult.is_truncated" class="text-warning">
                  (truncated at {{ lastResult.row_count }} rows)
                </span>
              </span>
            </div>
          </v-alert>
        </v-col>
      </v-row>

      <!-- Query Plan -->
      <v-expand-transition>
        <v-card v-if="queryPlan" class="mt-4" variant="outlined">
          <v-card-title class="text-subtitle-1">
            <v-icon start>mdi-chart-timeline-variant</v-icon>
            Query Execution Plan
          </v-card-title>
          <v-card-text>
            <pre class="query-plan">{{ queryPlan.plan_text }}</pre>
          </v-card-text>
        </v-card>
      </v-expand-transition>

      <!-- Error Display -->
      <v-alert
        v-if="error"
        type="error"
        variant="tonal"
        closable
        @click:close="error = null"
        class="mt-4"
      >
        {{ error }}
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useDataSourceStore } from '@/stores/data-source';
import { queryApi } from '@/api/query';
import type { QueryResult, QueryValidation, QueryPlan } from '@/types/query';

const props = defineProps<{
  initialQuery?: string;
  initialDataSource?: string;
}>();

const emit = defineEmits<{
  result: [result: QueryResult];
  error: [error: string];
}>();

const dataSourceStore = useDataSourceStore();

// State
const query = ref(props.initialQuery || '');
const selectedDataSource = ref(props.initialDataSource || '');
const validation = ref<QueryValidation | null>(null);
const lastResult = ref<QueryResult | null>(null);
const queryPlan = ref<QueryPlan | null>(null);
const executing = ref(false);
const validating = ref(false);
const explaining = ref(false);
const error = ref<string | null>(null);

// Computed
const dataSourceNames = computed(() => 
  dataSourceStore.dataSources.map(ds => ds.name)
);

// Methods
async function executeQuery() {
  if (!selectedDataSource.value || !query.value) return;

  executing.value = true;
  error.value = null;
  lastResult.value = null;
  queryPlan.value = null;

  try {
    const result = await queryApi.executeQuery(
      selectedDataSource.value,
      { query: query.value, limit: 100, timeout: 30 }
    );
    
    lastResult.value = result;
    emit('result', result);

    // Auto-validate on successful execution
    await validateQueryOnly();
  } catch (err: any) {
    const errorMessage = err.response?.data?.detail || err.message || 'Query execution failed';
    error.value = errorMessage;
    emit('error', errorMessage);
  } finally {
    executing.value = false;
  }
}

async function validateQueryOnly() {
  if (!selectedDataSource.value || !query.value) return;

  validating.value = true;
  error.value = null;

  try {
    validation.value = await queryApi.validateQuery(
      selectedDataSource.value,
      { query: query.value }
    );
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Query validation failed';
  } finally {
    validating.value = false;
  }
}

async function explainQueryPlan() {
  if (!selectedDataSource.value || !query.value) return;

  explaining.value = true;
  error.value = null;
  queryPlan.value = null;

  try {
    queryPlan.value = await queryApi.explainQuery(
      selectedDataSource.value,
      { query: query.value }
    );
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to get query plan';
  } finally {
    explaining.value = false;
  }
}

function clearQuery() {
  query.value = '';
  validation.value = null;
  lastResult.value = null;
  queryPlan.value = null;
  error.value = null;
}

// Load data sources on mount
onMounted(async () => {
  if (dataSourceStore.dataSources.length === 0) {
    await dataSourceStore.fetchDataSources();
  }

  // Select first data source if none selected
  if (!selectedDataSource.value && dataSourceNames.value.length > 0) {
    const firstDataSource = dataSourceNames.value[0];
    if (firstDataSource) {
      selectedDataSource.value = firstDataSource;
    }
  }
});
</script>

<style scoped>
.sql-editor-container {
  position: relative;
}

.sql-editor :deep(textarea) {
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  line-height: 1.5;
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
