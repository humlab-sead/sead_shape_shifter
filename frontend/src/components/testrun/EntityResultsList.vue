<template>
  <div class="entity-results-list">
    <div v-if="entities.length === 0" class="text-center text-medium-emphasis py-8">No entities in this category</div>

    <v-expansion-panels v-else>
      <v-expansion-panel v-for="entity in entities" :key="entity.entity_name">
        <v-expansion-panel-title>
          <div class="d-flex justify-space-between align-center w-100 pr-4">
            <div class="d-flex align-center ga-2">
              <v-icon :color="getStatusColor(entity.status)" size="small">
                {{ getStatusIcon(entity.status) }}
              </v-icon>
              <strong>{{ entity.entity_name }}</strong>
              <v-chip :color="getStatusColor(entity.status)" size="small">
                {{ entity.status }}
              </v-chip>
            </div>
            <div class="d-flex ga-4 text-caption">
              <span>{{ entity.rows_in }} → {{ entity.rows_out }} rows</span>
              <span class="text-medium-emphasis">{{ formatTime(entity.execution_time_ms) }}</span>
            </div>
          </div>
        </v-expansion-panel-title>

        <v-expansion-panel-text>
          <v-container fluid>
            <!-- Error Message -->
            <v-alert v-if="entity.error_message" type="error" variant="tonal" class="mb-4">
              <strong>Error:</strong>
              <pre class="mt-2">{{ entity.error_message }}</pre>
            </v-alert>

            <!-- Warnings -->
            <div v-if="entity.warnings.length > 0" class="mb-4">
              <h4 class="text-subtitle-2 mb-2">Warnings ({{ entity.warnings.length }})</h4>
              <v-alert
                v-for="(warning, idx) in entity.warnings"
                :key="idx"
                type="warning"
                variant="tonal"
                density="compact"
                class="mb-2"
              >
                {{ warning }}
              </v-alert>
            </div>

            <!-- Validation Issues -->
            <div v-if="entity.validation_issues.length > 0" class="mb-4">
              <h4 class="text-subtitle-2 mb-2">Validation Issues ({{ entity.validation_issues.length }})</h4>
              <v-alert
                v-for="(issue, idx) in entity.validation_issues"
                :key="idx"
                :type="issue.severity === 'error' ? 'error' : issue.severity === 'warning' ? 'warning' : 'info'"
                variant="tonal"
                density="compact"
                class="mb-2"
              >
                <div class="d-flex ga-2 mb-1">
                  <v-chip size="x-small">{{ issue.issue_type }}</v-chip>
                  <v-chip size="x-small" variant="outlined">{{ issue.severity }}</v-chip>
                </div>
                {{ issue.message }}
              </v-alert>
            </div>

            <!-- Preview Data -->
            <div v-if="entity.preview_rows && entity.preview_rows.length > 0">
              <h4 class="text-subtitle-2 mb-2">Preview ({{ entity.preview_rows.length }} rows)</h4>
              <v-table density="compact">
                <thead>
                  <tr>
                    <th v-for="col in Object.keys(entity.preview_rows?.[0] || {})" :key="col">
                      {{ col }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in entity.preview_rows" :key="idx">
                    <td v-for="(val, colIdx) in Object.values(row)" :key="colIdx">
                      <span v-if="val === null || val === undefined" class="text-medium-emphasis font-italic">
                        null
                      </span>
                      <span v-else>{{ val }}</span>
                    </td>
                  </tr>
                </tbody>
              </v-table>
            </div>
          </v-container>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import type { EntityTestResult } from '@/types/testRun'

interface Props {
  entities: EntityTestResult[]
}

defineProps<Props>()

const getStatusIcon = (status: string): string => {
  switch (status) {
    case 'success':
      return 'mdi-check-circle'
    case 'failed':
      return 'mdi-close-circle'
    case 'skipped':
      return 'mdi-alert-circle'
    default:
      return 'mdi-help-circle'
  }
}

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
      return 'error'
    case 'skipped':
      return 'warning'
    default:
      return 'grey'
  }
}

const formatTime = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}
</script>

<style scoped>
pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: monospace;
  font-size: 0.875rem;
}
</style>
