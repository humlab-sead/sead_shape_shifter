<template>
  <v-dialog
    v-model="isOpen"
    :max-width="isMaximized ? '100vw' : dialogWidth"
    :persistent="false"
    scrollable
    :scrim="false"
    :style="dialogPositionStyle"
    content-class="log-viewer-dialog"
  >
    <v-card :style="cardStyle">
      <v-card-title 
        class="d-flex align-center justify-space-between pa-2 drag-handle" 
        @mousedown="startDrag"
      >
        <div class="d-flex align-center">
          <v-icon icon="mdi-console-line" class="mr-2" />
          <span>Application Logs</span>
        </div>
        <div class="d-flex align-center gap-1">
          <v-btn
            icon="mdi-window-minimize"
            variant="text"
            size="small"
            density="compact"
            @click.stop="toggleMinimize"
          />
          <v-btn
            :icon="isMaximized ? 'mdi-window-restore' : 'mdi-window-maximize'"
            variant="text"
            size="small"
            density="compact"
            @click.stop="toggleMaximize"
          />
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            density="compact"
            @click.stop="close"
          />
        </div>
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-3" :style="{ height: isMinimized ? '0px' : contentHeight }">
        <v-row dense class="mb-3">
          <v-col cols="12" sm="3">
            <v-select
              v-model="selectedLogType"
              :items="logTypes"
              label="Log Type"
              variant="outlined"
              density="compact"
              hide-details
              @update:model-value="refreshLogs"
            />
          </v-col>
          <v-col cols="12" sm="3">
            <v-select
              v-model="selectedLogLevel"
              :items="logLevels"
              label="Filter by Level"
              variant="outlined"
              density="compact"
              clearable
              hide-details
              @update:model-value="refreshLogs"
            />
          </v-col>
          <v-col cols="12" sm="3">
            <v-select
              v-model="selectedLines"
              :items="lineOptions"
              label="Lines"
              variant="outlined"
              density="compact"
              hide-details
              @update:model-value="refreshLogs"
            />
          </v-col>
          <v-col cols="12" sm="3">
            <div class="d-flex gap-1">
              <v-btn
                size="small"
                variant="tonal"
                icon="mdi-refresh"
                :loading="logsLoading"
                @click="refreshLogs"
              />
              <v-btn
                size="small"
                variant="tonal"
                icon="mdi-download"
                @click="downloadLogs"
              />
              <v-tooltip location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    size="small"
                    :variant="autoRefresh ? 'tonal' : 'outlined'"
                    :color="autoRefresh ? 'primary' : undefined"
                    icon="mdi-reload"
                    @click="toggleAutoRefresh(!autoRefresh)"
                  />
                </template>
                Auto-refresh (30s)
              </v-tooltip>
            </div>
          </v-col>
        </v-row>

        <v-alert v-if="logsError" type="error" density="compact" class="mb-3" closable>
          {{ logsError }}
        </v-alert>

        <div v-if="logLines.length === 0 && !logsLoading" class="text-center text-medium-emphasis py-8">
          <v-icon icon="mdi-text-box-outline" size="64" class="mb-2" />
          <div>No logs found</div>
        </div>

        <div v-else class="logs-container">
          <pre class="logs-content">{{ logLines.join('\n') }}</pre>
        </div>

        <div v-if="logLines.length > 0" class="text-caption text-medium-emphasis mt-2">
          Showing {{ logLines.length }} lines
          <span v-if="autoRefresh" class="ml-2">
            <v-icon icon="mdi-autorenew" size="x-small" />
            Auto-refreshing
          </span>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, computed } from 'vue'
import { api } from '@/api'
import type { LogType, LogLevel } from '@/api/logs'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Dialog state
const isMinimized = ref(false)
const isMaximized = ref(false)
const dialogWidth = ref('800px')
const contentHeight = ref('500px')

// Drag state
const isDragging = ref(false)
const dialogPosition = ref({ x: 0, y: 0 })
const initialMousePos = ref({ x: 0, y: 0 })
const initialDialogPos = ref({ x: 0, y: 0 })

// Logs state
const logLines = ref<string[]>([])
const logsLoading = ref(false)
const logsError = ref<string | null>(null)
const selectedLogType = ref<LogType>('app')
const selectedLogLevel = ref<LogLevel | null>(null)
const selectedLines = ref(500)
const autoRefresh = ref(false)
let autoRefreshInterval: number | null = null

const logTypes = [
  { title: 'Application Logs', value: 'app' },
  { title: 'Error Logs', value: 'error' },
]

const logLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

const lineOptions = [
  { title: '100 lines', value: 100 },
  { title: '250 lines', value: 250 },
  { title: '500 lines', value: 500 },
  { title: '1000 lines', value: 1000 },
  { title: '2500 lines', value: 2500 },
]

const dialogPositionStyle = computed(() => {
  if (isMaximized.value) {
    return {}
  }
  if (dialogPosition.value.x === 0 && dialogPosition.value.y === 0) {
    return {} // Let dialog center itself initially
  }
  return {
    position: 'fixed' as const,
    top: `${dialogPosition.value.y}px`,
    left: `${dialogPosition.value.x}px`,
    transform: 'none', // Override default centering
    margin: '0',
  }
})

const cardStyle = computed(() => {
  if (isMaximized.value) {
    return {
      width: '100vw',
      height: '100vh',
      maxWidth: '100vw !important',
    }
  }
  return {}
})

async function refreshLogs() {
  logsLoading.value = true
  logsError.value = null
  try {
    const response = await api.logs.getLogs(
      selectedLogType.value,
      selectedLines.value,
      selectedLogLevel.value || undefined
    )
    logLines.value = response.lines
  } catch (err) {
    logsError.value = err instanceof Error ? err.message : 'Failed to fetch logs'
    logLines.value = []
  } finally {
    logsLoading.value = false
  }
}

async function downloadLogs() {
  try {
    const response = await api.logs.downloadLogs(selectedLogType.value)
    const blob = new Blob([response.content], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = response.filename
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (err) {
    logsError.value = err instanceof Error ? err.message : 'Failed to download logs'
  }
}

function toggleAutoRefresh(enabled: boolean) {
  autoRefresh.value = enabled
  if (enabled) {
    refreshLogs()
    autoRefreshInterval = window.setInterval(refreshLogs, 30000)
  } else {
    if (autoRefreshInterval !== null) {
      clearInterval(autoRefreshInterval)
      autoRefreshInterval = null
    }
  }
}

function toggleMinimize() {
  isMinimized.value = !isMinimized.value
}

function toggleMaximize() {
  isMaximized.value = !isMaximized.value
  if (isMaximized.value) {
    contentHeight.value = 'calc(100vh - 120px)'
  } else {
    contentHeight.value = '500px'
  }
}

function close() {
  isOpen.value = false
}

// Drag functionality
function startDrag(event: MouseEvent) {
  if (isMaximized.value) return
  
  const dialog = (event.target as HTMLElement).closest('.v-overlay__content') as HTMLElement
  
  if (dialog) {
    const rect = dialog.getBoundingClientRect()
    
    // Store initial mouse position
    initialMousePos.value = {
      x: event.clientX,
      y: event.clientY
    }
    
    // Store current dialog position (or use rect if not yet positioned)
    initialDialogPos.value = {
      x: dialogPosition.value.x || rect.left,
      y: dialogPosition.value.y || rect.top
    }
    
    isDragging.value = true
    document.addEventListener('mousemove', onDrag)
    document.addEventListener('mouseup', stopDrag)
    event.preventDefault()
  }
}

function onDrag(event: MouseEvent) {
  if (!isDragging.value) return
  
  // Calculate how far the mouse has moved
  const deltaX = event.clientX - initialMousePos.value.x
  const deltaY = event.clientY - initialMousePos.value.y
  
  // Apply delta to initial dialog position
  dialogPosition.value = {
    x: initialDialogPos.value.x + deltaX,
    y: initialDialogPos.value.y + deltaY
  }
}

function stopDrag() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

// Load logs when dialog opens
watch(isOpen, (newValue) => {
  if (newValue && logLines.value.length === 0) {
    refreshLogs()
  }
  if (!newValue) {
    // Reset position when dialog closes
    dialogPosition.value = { x: 0, y: 0 }
  }
})

onUnmounted(() => {
  if (autoRefreshInterval !== null) {
    clearInterval(autoRefreshInterval)
  }
  stopDrag()
})
</script>

<style scoped>
.drag-handle {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  cursor: move;
  user-select: none;
}

.drag-handle:active {
  cursor: grabbing;
}

:deep(.log-viewer-dialog) {
  position: fixed !important;
}

.logs-container {
  max-height: 600px;
  overflow-y: auto;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  padding: 12px;
}

.logs-content {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--v-theme-on-surface);
}
</style>
