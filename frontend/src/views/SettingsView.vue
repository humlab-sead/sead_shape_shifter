<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-2">Settings</h1>
        <p class="text-subtitle-1 text-medium-emphasis">Customize your Shape Shifter experience</p>
      </v-col>
    </v-row>

    <v-tabs v-model="activeTab" class="mb-4">
      <v-tab value="general">General</v-tab>
      <v-tab value="logs">Logs</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- General Settings Tab -->
      <v-window-item value="general">
        <v-row>
          <!-- Theme Presets -->
          <v-col cols="12">
            <v-card>
              <v-card-title>Theme</v-card-title>
              <v-card-subtitle> Choose a theme preset </v-card-subtitle>

              <v-card-text>
            <v-row>
              <v-col v-for="preset in theme.presets" :key="preset.name" cols="12" sm="6" md="2">
                <v-card
                  :variant="theme.currentThemeName.value === preset.name ? 'tonal' : 'plain'"
                  :color="theme.currentThemeName.value === preset.name ? 'primary' : undefined"
                  class="theme-preset-card"
                  @click="selectTheme(preset.name)"
                >
                  <v-card-text class="text-center">
                    <v-icon
                      :icon="preset.icon"
                      size="48"
                      :color="theme.currentThemeName.value === preset.name ? 'primary' : undefined"
                      class="mb-2"
                    />
                    <div class="text-h6">{{ preset.displayName }}</div>
                    <div class="text-caption text-medium-emphasis">
                      {{ preset.description }}
                    </div>

                    <!-- Current theme indicator -->
                    <v-chip
                      v-if="theme.currentThemeName.value === preset.name"
                      size="x-small"
                      color="primary"
                      class="mt-2"
                    >
                      Current
                    </v-chip>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <v-divider class="my-4" />

            <!-- Quick Actions -->
            <div class="d-flex flex-wrap gap-2">
              <v-btn
                :color="theme.isDark.value ? 'primary' : undefined"
                variant="outlined"
                :prepend-icon="theme.isDark.value ? 'mdi-moon-waning-crescent' : 'mdi-white-balance-sunny'"
                @click="theme.toggleDarkMode()"
              >
                {{ theme.isDark.value ? 'Dark Mode' : 'Light Mode' }}
              </v-btn>

              <v-btn
                v-if="theme.currentThemeName.value !== 'light'"
                variant="outlined"
                prepend-icon="mdi-restore"
                @click="handleResetToDefault"
              >
                Reset to Default
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Additional Settings -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Interface</v-card-title>
          <v-card-subtitle> Customize the interface density and behavior </v-card-subtitle>
          <v-card-text>
            <v-switch
              v-model="appSettings.compactMode.value"
              label="Compact mode"
              color="primary"
              hide-details
              class="mb-3"
            >
              <!-- <template #append>
                <v-tooltip location="top">
                  <template #activator="{ props }">
                    <v-icon icon="mdi-information-outline" size="small" v-bind="props" />
                  </template>
                  Reduces spacing and component sizes throughout the interface
                </v-tooltip>
              </template> -->
            </v-switch>

            <v-switch
              v-model="appSettings.animationsEnabled.value"
              label="Enable animations"
              color="primary"
              hide-details
              class="mb-3"
            >
              <!-- <template #append>
                <v-tooltip location="top">
                  <template #activator="{ props }">
                    <v-icon icon="mdi-information-outline" size="small" v-bind="props" />
                  </template>
                  Enable smooth transitions and animations
                </v-tooltip>
              </template> -->
            </v-switch>

            <v-switch
              v-model="appSettings.railNavigation.value"
              label="Auto-collapse navigation"
              color="primary"
              hide-details
            >
              <!-- <template #append>
                <v-tooltip location="top">
                  <template #activator="{ props }">
                    <v-icon icon="mdi-information-outline" size="small" v-bind="props" />
                  </template>
                  Automatically collapse navigation drawer to icons only
                </v-tooltip>
              </template> -->
            </v-switch>

            <v-switch
              v-model="appSettings.enableFkSuggestions.value"
              label="Enable foreign key suggestions"
              color="primary"
              hide-details
              class="mt-3"
            />

            <v-divider class="my-4" />

            <div class="d-flex gap-2">
              <v-btn variant="outlined" size="small" prepend-icon="mdi-restore" @click="handleResetSettings">
                Reset Interface Settings
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>About</v-card-title>
          <v-card-text>
            <div class="d-flex align-center mb-2">
              <v-icon icon="mdi-information" class="mr-2" />
              <span class="text-body-2">SEAD Shape Shifter Project Editor</span>
            </div>
            <div class="d-flex align-center mb-2">
              <v-icon icon="mdi-tag" class="mr-2" />
              <span class="text-body-2">Version: {{ version }}</span>
            </div>
            <div class="d-flex align-center">
              <v-icon icon="mdi-github" class="mr-2" />
              <a href="https://github.com/humlab-sead/sead_shape_shifter" target="_blank" class="text-body-2">
                GitHub Repository
              </a>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
      </v-window-item>

      <!-- Logs Tab -->
      <v-window-item value="logs">
        <v-row>
          <v-col cols="12">
            <v-card>
              <v-card-title class="d-flex align-center justify-space-between">
                <span>Application Logs</span>
                <div class="d-flex gap-2">
                  <v-btn
                    size="small"
                    variant="tonal"
                    prepend-icon="mdi-refresh"
                    :loading="logsLoading"
                    @click="refreshLogs"
                  >
                    Refresh
                  </v-btn>
                  <v-btn
                    size="small"
                    variant="tonal"
                    prepend-icon="mdi-download"
                    @click="downloadLogs"
                  >
                    Download
                  </v-btn>
                </div>
              </v-card-title>

              <v-card-text>
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
                      label="Lines to Show"
                      variant="outlined"
                      density="compact"
                      hide-details
                      @update:model-value="refreshLogs"
                    />
                  </v-col>
                  <v-col cols="12" sm="3">
                    <v-switch
                      v-model="autoRefresh"
                      label="Auto-refresh (30s)"
                      density="compact"
                      hide-details
                      @update:model-value="toggleAutoRefresh"
                    />
                  </v-col>
                </v-row>

                <v-alert v-if="logsError" type="error" density="compact" class="mb-3">
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
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>
    </v-window>

    <!-- Confirmation Dialog -->
    <v-dialog v-model="showResetDialog" max-width="400">
      <v-card>
        <v-card-title>Reset Theme</v-card-title>
        <v-card-text>
          Are you sure you want to reset to the default theme? This will remove all custom colors.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showResetDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" @click="confirmReset">Reset</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Reset Settings Dialog -->
    <v-dialog v-model="showResetSettingsDialog" max-width="400">
      <v-card>
        <v-card-title>Reset Interface Settings</v-card-title>
        <v-card-text> Are you sure you want to reset all interface settings to defaults? </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showResetSettingsDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" @click="confirmResetSettings">Reset</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useTheme } from '@/composables/useTheme'
import { useSettings } from '@/composables/useSettings'
import { api } from '@/api'
import type { LogType, LogLevel } from '@/api/logs'

const theme = useTheme()
const appSettings = useSettings()

const version = ref('loading...')
const showResetDialog = ref(false)
const showResetSettingsDialog = ref(false)

// Tabs
const activeTab = ref('general')

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

function toggleAutoRefresh(enabled: boolean | null) {
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

onMounted(async () => {
  // Fetch version from backend
  try {
    const health = await api.health.getHealth()
    version.value = health.version
  } catch (err) {
    console.error('Failed to fetch version:', err)
    version.value = 'unknown'
  }
  
  refreshLogs()
})

onUnmounted(() => {
  if (autoRefreshInterval !== null) {
    clearInterval(autoRefreshInterval)
  }
})

function selectTheme(themeName: string) {
  theme.setTheme(themeName)
}

function handleResetToDefault() {
  showResetDialog.value = true
}

function confirmReset() {
  theme.resetToDefault()
  showResetDialog.value = false
}

function handleResetSettings() {
  showResetSettingsDialog.value = true
}

function confirmResetSettings() {
  appSettings.resetToDefaults()
  showResetSettingsDialog.value = false
}
</script>

<style scoped>
.theme-preset-card {
  cursor: pointer;
  transition: all 0.2s;
}

.theme-preset-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
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
}

/* Syntax highlighting for log levels */
.logs-content {
  color: var(--v-theme-on-surface);
}
</style>
