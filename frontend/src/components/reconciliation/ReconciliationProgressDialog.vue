<template>
  <v-dialog v-model="isOpen" max-width="600" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-sync" class="mr-2" />
        Reconciliation Progress
      </v-card-title>

      <v-card-text>
        <div v-if="progress">
          <!-- Status Message -->
          <div class="text-h6 mb-4">
            {{ progress.message || 'Processing...' }}
          </div>

          <!-- Progress Bar -->
          <v-progress-linear
            :model-value="progress.progress_percent"
            :indeterminate="progress.total === 0"
            color="primary"
            height="25"
            class="mb-2"
          >
            <template v-if="progress.total > 0" #default>
              <strong class="text-white">{{ Math.round(progress.progress_percent) }}%</strong>
            </template>
          </v-progress-linear>

          <!-- Progress Details -->
          <div class="text-caption text-medium-emphasis mb-4">
            <div v-if="progress.total > 0">
              {{ progress.current }} / {{ progress.total }} queries processed
            </div>
            <div v-if="progress.elapsed_seconds">
              Elapsed: {{ formatDuration(progress.elapsed_seconds) }}
            </div>
            <div v-if="progress.estimated_remaining_seconds">
              Estimated time remaining: {{ formatDuration(progress.estimated_remaining_seconds) }}
            </div>
          </div>

          <!-- Status Chips -->
          <div class="d-flex flex-wrap gap-2 mb-4">
            <v-chip
              :color="getStatusColor(progress.status)"
              variant="flat"
              size="small"
            >
              <v-icon :icon="getStatusIcon(progress.status)" start size="small" />
              {{ progress.status.toUpperCase() }}
            </v-chip>
          </div>

          <!-- Error Message -->
          <v-alert
            v-if="progress.error"
            type="error"
            variant="tonal"
            class="mb-4"
          >
            {{ progress.error }}
          </v-alert>
        </div>

        <div v-else class="text-center py-4">
          <v-progress-circular indeterminate color="primary" />
          <div class="text-caption mt-2">Connecting...</div>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        
        <!-- Cancel Button (only for running operations) -->
        <v-btn
          v-if="progress && progress.status === 'running'"
          color="error"
          variant="text"
          :loading="cancelling"
          @click="handleCancel"
        >
          Cancel
        </v-btn>

        <!-- Close Button (for completed/failed/cancelled) -->
        <v-btn
          v-if="progress && ['completed', 'failed', 'cancelled'].includes(progress.status)"
          color="primary"
          variant="flat"
          @click="handleClose"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { apiClient } from '@/api/client'

interface OperationProgress {
  operation_id: string
  operation_type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  current: number
  total: number
  progress_percent: number
  message: string
  started_at: string
  completed_at: string | null
  elapsed_seconds: number
  estimated_remaining_seconds: number | null
  error: string | null
  metadata: Record<string, any>
}

interface Props {
  operationId: string | null
}

interface Emits {
  (e: 'close'): void
  (e: 'complete', result: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isOpen = ref(false)
const progress = ref<OperationProgress | null>(null)
const cancelling = ref(false)
let eventSource: EventSource | null = null

// Watch for operation ID changes
watch(
  () => props.operationId,
  (newOperationId) => {
    if (newOperationId) {
      startProgressTracking(newOperationId)
    } else {
      stopProgressTracking()
    }
  },
  { immediate: true }
)

function startProgressTracking(operationId: string) {
  isOpen.value = true
  progress.value = null

  // Create SSE connection
  const streamUrl = `/api/v1/operations/${operationId}/stream`
  eventSource = new EventSource(apiClient.defaults.baseURL + streamUrl)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as OperationProgress
      progress.value = data

      // If completed successfully, emit complete event
      if (data.status === 'completed') {
        emit('complete', data.metadata)
      }
    } catch (error) {
      console.error('Error parsing SSE message:', error)
    }
  }

  eventSource.onerror = (error) => {
    console.error('SSE error:', error)
    eventSource?.close()
    eventSource = null
  }
}

function stopProgressTracking() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  isOpen.value = false
  progress.value = null
}

async function handleCancel() {
  if (!props.operationId) return

  cancelling.value = true
  try {
    await apiClient.post(`/api/v1/operations/${props.operationId}/cancel`)
  } catch (error) {
    console.error('Failed to cancel operation:', error)
  } finally {
    cancelling.value = false
  }
}

function handleClose() {
  stopProgressTracking()
  emit('close')
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'pending':
      return 'grey'
    case 'running':
      return 'primary'
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'cancelled':
      return 'warning'
    default:
      return 'grey'
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'pending':
      return 'mdi-clock-outline'
    case 'running':
      return 'mdi-sync'
    case 'completed':
      return 'mdi-check-circle'
    case 'failed':
      return 'mdi-alert-circle'
    case 'cancelled':
      return 'mdi-cancel'
    default:
      return 'mdi-help-circle'
  }
}

// Cleanup on unmount
onUnmounted(() => {
  stopProgressTracking()
})
</script>

<style scoped>
.gap-2 {
  gap: 8px;
}
</style>
