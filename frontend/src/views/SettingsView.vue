<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-2">Settings</h1>
        <p class="text-subtitle-1 text-medium-emphasis">Customize your Shape Shifter experience</p>
      </v-col>
    </v-row>

    <v-row>
      <!-- Theme Presets -->
      <v-col cols="12" lg="8">
        <v-card>
          <v-card-title>Theme</v-card-title>
          <v-card-subtitle> Choose a theme preset or customize your own colors </v-card-subtitle>

          <v-card-text>
            <v-row>
              <v-col v-for="preset in theme.presets" :key="preset.name" cols="12" sm="6" md="4">
                <v-card
                  :variant="theme.currentThemeName.value === preset.name ? 'tonal' : 'outlined'"
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
                v-if="theme.currentThemeName.value !== 'light' || theme.hasCustomColors.value"
                variant="outlined"
                prepend-icon="mdi-restore"
                @click="handleResetToDefault"
              >
                Reset to Default
              </v-btn>

              <v-spacer />

              <v-chip v-if="theme.hasCustomColors.value" color="info" variant="tonal" prepend-icon="mdi-palette">
                Custom colors applied
              </v-chip>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Theme Preview -->
      <v-col cols="12" lg="4">
        <v-card>
          <v-card-title>
            Preview
            <v-chip v-if="appSettings.compactMode.value" size="small" color="info" variant="tonal" class="ml-2">
              Compact
            </v-chip>
          </v-card-title>
          <v-card-text>
            <div class="preview-container">
              <!-- Color swatches -->
              <div class="color-swatches mb-4">
                <div
                  v-for="colorKey in ['primary', 'secondary', 'accent', 'success', 'warning', 'error']"
                  :key="colorKey"
                  class="color-swatch-item mb-2"
                >
                  <div
                    class="color-swatch"
                    :style="{ backgroundColor: theme.vuetifyTheme.current.value.colors[colorKey] }"
                  />
                  <span class="text-caption text-capitalize">{{ colorKey }}</span>
                </div>
              </div>

              <!-- Component preview -->
              <div class="components-preview">
                <v-btn color="primary" size="small" class="mb-2">Primary Button</v-btn>
                <v-btn color="secondary" size="small" variant="outlined" class="mb-2"> Secondary Button </v-btn>
                <v-text-field
                  model-value="Text input"
                  density="comfortable"
                  variant="outlined"
                  hide-details
                  class="mb-2"
                />
                <v-alert type="info" variant="tonal" density="compact" class="mb-2"> Info message </v-alert>
                <v-alert type="success" variant="tonal" density="compact" class="mb-2"> Success message </v-alert>
                <v-alert type="warning" variant="tonal" density="compact"> Warning message </v-alert>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Custom Colors Section -->
    <v-row>
      <v-col cols="12">
        <ThemeColorPicker />
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
              <template #append>
                <v-tooltip location="top">
                  <template #activator="{ props }">
                    <v-icon icon="mdi-information-outline" size="small" v-bind="props" />
                  </template>
                  Reduces spacing and component sizes throughout the interface
                </v-tooltip>
              </template>
            </v-switch>

            <v-switch
              v-model="appSettings.animationsEnabled.value"
              label="Enable animations"
              color="primary"
              hide-details
              class="mb-3"
            >
              <template #append>
                <v-tooltip location="top">
                  <template #activator="{ props }">
                    <v-icon icon="mdi-information-outline" size="small" v-bind="props" />
                  </template>
                  Enable smooth transitions and animations
                </v-tooltip>
              </template>
            </v-switch>

            <v-switch
              v-model="appSettings.railNavigation.value"
              label="Auto-collapse navigation"
              color="primary"
              hide-details
            >
              <template #append>
                <v-tooltip location="top">
                  <template #activator="{ props }">
                    <v-icon icon="mdi-information-outline" size="small" v-bind="props" />
                  </template>
                  Automatically collapse navigation drawer to icons only
                </v-tooltip>
              </template>
            </v-switch>

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
import { ref } from 'vue'
import { useTheme } from '@/composables/useTheme'
import { useSettings } from '@/composables/useSettings'
import ThemeColorPicker from '@/components/ThemeColorPicker.vue'

const theme = useTheme()
const appSettings = useSettings()

const version = ref('0.1.0')
const showResetDialog = ref(false)
const showResetSettingsDialog = ref(false)

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

.preview-container {
  padding: 16px;
}

.color-swatches {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.color-swatch-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.color-swatch {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  border: 2px solid rgba(0, 0, 0, 0.12);
}

.components-preview {
  display: flex;
  flex-direction: column;
}
</style>
