<template>
  <v-card>
    <v-card-title class="d-flex align-center py-2">
      <v-icon icon="mdi-eye-outline" class="mr-2" size="small" />
      <span class="text-body-1">Entity Data Preview</span>
      <v-spacer />
      
      <!-- Cache indicator -->
      <v-chip
        v-if="previewData?.cache_hit"
        size="x-small"
        color="info"
        variant="flat"
        class="mr-2"
      >
        <v-icon icon="mdi-cached" start size="x-small" />
        Cached
      </v-chip>

      <!-- Row count -->
      <v-chip
        v-if="previewData"
        size="x-small"
        variant="text"
        class="mr-2"
      >
        {{ previewData.total_rows_in_preview }} / {{ previewData.estimated_total_rows || '?' }} rows
      </v-chip>

      <!-- Refresh button -->
      <v-btn
        icon="mdi-refresh"
        size="small"
        variant="text"
        :loading="loading"
        @click="emit('refresh')"
      />
    </v-card-title>

    <v-divider />

    <v-card-text class="pa-0">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" size="48" />
        <p class="text-caption mt-2">Loading preview...</p>
      </div>

      <!-- Error Display -->
      <v-alert
        v-else-if="error"
        type="error"
        variant="tonal"
        density="compact"
        class="ma-4"
      >
        {{ error }}
      </v-alert>

      <!-- Empty State -->
      <v-alert
        v-else-if="!previewData || !previewData.rows.length"
        type="info"
        variant="tonal"
        density="compact"
        class="ma-4"
      >
        <template v-if="!previewData">
          No preview data available
        </template>
        <template v-else>
          Entity has no data rows
        </template>
      </v-alert>

      <!-- Data Table -->
      <div v-else>
        <!-- Metadata chips -->
        <div class="d-flex flex-wrap gap-2 pa-3 bg-grey-lighten-5">
          <v-chip
            v-if="previewData.has_dependencies"
            size="small"
            variant="outlined"
            color="primary"
          >
            <v-icon icon="mdi-link-variant" start size="small" />
            {{ previewData.dependencies_loaded.length }} dependencies
          </v-chip>
          
          <v-chip
            v-for="transform in previewData.transformations_applied"
            :key="transform"
            size="small"
            variant="outlined"
            color="secondary"
          >
            <v-icon icon="mdi-cog-outline" start size="small" />
            {{ transform }}
          </v-chip>

          <v-chip
            size="small"
            variant="outlined"
            color="success"
          >
            <v-icon icon="mdi-clock-outline" start size="small" />
            {{ previewData.execution_time_ms }}ms
          </v-chip>
        </div>

        <v-divider />

        <!-- Scrollable table container -->
        <div class="preview-table-container">
          <v-table density="compact" fixed-header height="400px">
            <thead>
              <tr>
                <th
                  v-for="column in previewData.columns"
                  :key="column.name"
                  class="text-left"
                >
                  <div class="d-flex align-center gap-1">
                    <v-icon
                      v-if="column.is_key"
                      icon="mdi-key"
                      size="x-small"
                      color="warning"
                      class="mr-1"
                    />
                    <span class="font-weight-medium">{{ column.name }}</span>
                    <v-chip
                      size="x-small"
                      variant="flat"
                      :color="getTypeColor(column.data_type)"
                      class="ml-1"
                    >
                      {{ column.data_type }}
                    </v-chip>
                    <v-icon
                      v-if="column.nullable"
                      icon="mdi-null"
                      size="x-small"
                      color="grey"
                    />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, idx) in previewData.rows"
                :key="idx"
                :class="{ 'bg-grey-lighten-4': idx % 2 === 0 }"
              >
                <td
                  v-for="column in previewData.columns"
                  :key="column.name"
                  class="text-left"
                >
                  <span
                    v-if="row[column.name] === null || row[column.name] === undefined"
                    class="text-grey font-italic"
                  >
                    null
                  </span>
                  <span v-else>{{ formatValue(row[column.name]) }}</span>
                </td>
              </tr>
            </tbody>
          </v-table>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import type { PreviewResult } from '@/composables/useEntityPreview'

interface Props {
  previewData: PreviewResult | null
  loading?: boolean
  error?: string | null
}

withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
})

const emit = defineEmits<{
  refresh: []
}>()

function getTypeColor(dataType: string): string {
  const typeMap: Record<string, string> = {
    string: 'blue-grey',
    integer: 'green',
    number: 'green',
    boolean: 'purple',
    date: 'orange',
    datetime: 'orange',
    object: 'blue',
  }
  return typeMap[dataType.toLowerCase()] || 'grey'
}

function formatValue(value: any): string {
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value)
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  return String(value)
}
</script>

<style scoped>
.preview-table-container {
  max-height: 400px;
  overflow-y: auto;
}

:deep(.v-table) {
  background: white;
}

:deep(.v-table th) {
  background: #f5f5f5;
  font-weight: 600;
  white-space: nowrap;
  position: sticky;
  top: 0;
  z-index: 1;
}

:deep(.v-table td) {
  white-space: nowrap;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
