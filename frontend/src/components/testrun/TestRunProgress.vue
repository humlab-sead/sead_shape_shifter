<template>
  <div class="test-run-progress">
    <!-- Status and Time -->
    <div class="d-flex justify-space-between align-center mb-4">
      <div class="d-flex align-center ga-2">
        <strong>Status:</strong>
        <v-chip :color="getStatusColor(progress.status)" size="small">
          {{ progress.status }}
        </v-chip>
      </div>
      <div class="text-caption">Elapsed: {{ formatTime(getElapsedTime()) }}</div>
    </div>

    <!-- Progress Bar -->
    <div class="mb-4">
      <div class="d-flex justify-space-between mb-2">
        <span class="text-caption">
          Progress: {{ progress.entities_completed }} / {{ progress.entities_total }} entities
        </span>
        <span class="text-caption font-weight-bold"> {{ getProgressPercent() }}% </span>
      </div>
      <v-progress-linear
        :model-value="getProgressPercent()"
        :color="getStatusColor(progress.status)"
        height="20"
        rounded
      />
    </div>

    <!-- Current Entity -->
    <v-alert v-if="progress.current_entity && progress.status === 'running'" type="info" variant="tonal" class="mb-4">
      <strong>Currently processing:</strong> {{ progress.current_entity }}
    </v-alert>

    <!-- Entity Stats -->
    <v-row>
      <v-col cols="12" md="4">
        <v-card color="success" variant="tonal">
          <v-card-text>
            <div class="text-caption mb-1">Succeeded</div>
            <div class="text-h4 text-success">{{ progress.entities_succeeded }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card color="error" variant="tonal">
          <v-card-text>
            <div class="text-caption mb-1">Failed</div>
            <div class="text-h4 text-error">{{ progress.entities_failed }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card color="warning" variant="tonal">
          <v-card-text>
            <div class="text-caption mb-1">Skipped</div>
            <div class="text-h4 text-warning">{{ progress.entities_skipped }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Error Message -->
    <v-alert v-if="'error_message' in progress && progress.error_message" type="error" variant="tonal" class="mt-4">
      <strong>Error:</strong> {{ progress.error_message }}
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { TestRunStatus, type TestProgress, type TestRunResult } from '@/types/testRun'

interface Props {
  progress: TestProgress | TestRunResult
}

const props = defineProps<Props>()

const getStatusColor = (status: TestRunStatus): string => {
  switch (status) {
    case TestRunStatus.PENDING:
      return 'grey'
    case TestRunStatus.RUNNING:
      return 'primary'
    case TestRunStatus.COMPLETED:
      return 'success'
    case TestRunStatus.FAILED:
      return 'error'
    case TestRunStatus.CANCELLED:
      return 'warning'
    default:
      return 'grey'
  }
}

const getProgressPercent = (): number => {
  if (props.progress.entities_total === 0) return 0
  return Math.round((props.progress.entities_completed / props.progress.entities_total) * 100)
}

const formatTime = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`
  const seconds = Math.round(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

const getElapsedTime = (): number => {
  const progress = props.progress as any
  if ('elapsed_time_ms' in progress) {
    return progress.elapsed_time_ms
  }
  if ('total_time_ms' in progress) {
    return progress.total_time_ms
  }
  // Calculate from started_at
  if (progress.started_at) {
    const startedAt = new Date(progress.started_at)
    return Date.now() - startedAt.getTime()
  }
  return 0
}
</script>

<style scoped>
.test-run-progress {
  width: 100%;
}
</style>
