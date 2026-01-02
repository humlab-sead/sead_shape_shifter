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
      <v-col cols="12">
        <v-card>
          <v-card-title>Theme</v-card-title>
          <v-card-subtitle> Choose a theme preset </v-card-subtitle>

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
</style>
