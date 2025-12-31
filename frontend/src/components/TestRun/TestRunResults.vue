<template>
  <div class="test-run-results">
    <h3 class="text-h6 mb-4">Test Run Results</h3>

    <!-- Summary -->
    <v-card variant="tonal" class="mb-4">
      <v-card-text>
        <div class="d-flex flex-wrap ga-4">
          <div><strong>Config:</strong> {{ result.project_name }}</div>
          <div><strong>Total Time:</strong> {{ formatTime(result.total_time_ms) }}</div>
          <div><strong>Entities:</strong> {{ result.entities_total }}</div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Global Validation Issues -->
    <v-alert v-if="result.validation_issues.length > 0" type="warning" variant="tonal" class="mb-4">
      <strong>Validation Issues ({{ result.validation_issues.length }})</strong>
      <br />
      Found {{ result.validation_issues.length }} validation issue(s) across entities
    </v-alert>

    <!-- Entity Results Tabs -->
    <v-tabs v-model="activeTab" class="mb-4">
      <v-tab value="all">All ({{ result.entities_processed.length }})</v-tab>
      <v-tab value="success">Success ({{ groupedEntities.success.length }})</v-tab>
      <v-tab value="failed">Failed ({{ groupedEntities.failed.length }})</v-tab>
      <v-tab value="skipped">Skipped ({{ groupedEntities.skipped.length }})</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="all">
        <EntityResultsList :entities="result.entities_processed" />
      </v-window-item>
      <v-window-item value="success">
        <EntityResultsList :entities="groupedEntities.success" />
      </v-window-item>
      <v-window-item value="failed">
        <EntityResultsList :entities="groupedEntities.failed" />
      </v-window-item>
      <v-window-item value="skipped">
        <EntityResultsList :entities="groupedEntities.skipped" />
      </v-window-item>
    </v-window>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { TestRunResult } from '@/types/testRun'
import EntityResultsList from './EntityResultsList.vue'

interface Props {
  result: TestRunResult
}

const props = defineProps<Props>()

const activeTab = ref('all')

const groupedEntities = computed(() => ({
  success: props.result.entities_processed.filter((e) => e.status === 'success'),
  failed: props.result.entities_processed.filter((e) => e.status === 'failed'),
  skipped: props.result.entities_processed.filter((e) => e.status === 'skipped'),
}))

const formatTime = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}
</script>

<style scoped>
.test-run-results {
  width: 100%;
}
</style>
