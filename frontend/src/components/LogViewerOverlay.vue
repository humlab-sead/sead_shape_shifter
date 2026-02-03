<template>
  <v-dialog
    v-model="isOpen"
    :max-width="isMaximized ? '100vw' : dialogWidth + 'px'"
    :persistent="false"
    scrollable
    :scrim="false"
    :style="dialogPositionStyle"
    content-class="log-viewer-dialog"
  >
    <v-card :style="cardStyle" class="resizable-card">
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

      <v-card-text class="pa-3 log-card-content" :style="cardTextStyle">
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

      <!-- Resize handles -->
      <div 
        v-if="!isMaximized"
        class="resize-handle resize-handle-right"
        @mousedown="startResize($event, 'right')"
      />
      <div 
        v-if="!isMaximized"
        class="resize-handle resize-handle-bottom"
        @mousedown="startResize($event, 'bottom')"
      />
      <div 
        v-if="!isMaximized"
        class="resize-handle resize-handle-corner"
        @mousedown="startResize($event, 'corner')"
      />
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
const dialogWidth = ref(800)
const dialogHeight = ref(600)

// Drag state
const isDragging = ref(false)
const dialogPosition = ref({ x: 0, y: 0 })
const initialMousePos = ref({ x: 0, y: 0 })
const initialDialogPos = ref({ x: 0, y: 0 })

// Resize state
const isResizing = ref(false)
const resizeDirection = ref<'right' | 'bottom' | 'corner'>('corner')
const initialSize = ref({ width: 0, height: 0 })

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
  return {
    width: `${dialogWidth.value}px`,
    height: `${dialogHeight.value}px`,
  }
})

const cardTextStyle = computed(() => {
  if (isMinimized.value) {
    return { height: '0px', overflow: 'hidden' }
  }
  // Make content area flexible - it will fill available space
  return { 
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  }
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

// Resize functionality
function startResize(event: MouseEvent, direction: 'right' | 'bottom' | 'corner') {
  if (isMaximized.value) return
  
  resizeDirection.value = direction
  
  // Store initial mouse position
  initialMousePos.value = {
    x: event.clientX,
    y: event.clientY
  }
  
  // Store current dialog size
  initialSize.value = {
    width: dialogWidth.value,
    height: dialogHeight.value
  }
  
  isResizing.value = true
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  event.preventDefault()
  event.stopPropagation()
}

function onResize(event: MouseEvent) {
  if (!isResizing.value) return
  
  const deltaX = event.clientX - initialMousePos.value.x
  const deltaY = event.clientY - initialMousePos.value.y
  
  if (resizeDirection.value === 'right' || resizeDirection.value === 'corner') {
    dialogWidth.value = Math.max(400, initialSize.value.width + deltaX)
  }
  
  if (resizeDirection.value === 'bottom' || resizeDirection.value === 'corner') {
    dialogHeight.value = Math.max(300, initialSize.value.height + deltaY)
  }
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
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
  stopResize()
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

.resizable-card {
  display: flex;
  flex-direction: column;
  position: relative;
}

.log-card-content {
  flex: 1;
  min-height: 0; /* Important for flexbox scrolling */
}

.logs-container {
  flex: 1;
  overflow-y: auto;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  padding: 12px;
  min-height: 0; /* Important for flexbox scrolling */
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

/* Resize handles */
.resize-handle {
  position: absolute;
  background-color: transparent;
  z-index: 10;
}

.resize-handle-right {
  top: 0;
  right: 0;
  width: 8px;
  height: 100%;
  cursor: ew-resize;
}

.resize-handle-bottom {
  bottom: 0;
  left: 0;
  width: 100%;
  height: 8px;
  cursor: ns-resize;
}

.resize-handle-corner {
  bottom: 0;
  right: 0;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
}

.resize-handle-corner::after {
  content: '';
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 0 0 12px 12px;
  border-color: transparent transparent rgba(var(--v-theme-on-surface), 0.3) transparent;
}
</style>
