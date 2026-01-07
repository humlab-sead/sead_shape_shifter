<template>
  <v-card>
    <v-card-title>Custom Theme Colors</v-card-title>
    <v-card-subtitle> Customize individual colors for the current theme </v-card-subtitle>

    <v-card-text>
      <v-row>
        <v-col v-for="colorKey in colorKeys" :key="colorKey" cols="12" sm="6" md="4">
          <div class="color-picker-item">
            <div class="d-flex align-center mb-2">
              <v-icon :color="getColorValue(colorKey)" class="mr-2"> mdi-circle </v-icon>
              <span class="text-capitalize font-weight-medium">
                {{ colorKey }}
              </span>
            </div>

            <v-text-field
              :model-value="getColorValue(colorKey)"
              :label="`${capitalize(colorKey)} Color`"
              density="compact"
              variant="outlined"
              hide-details
              @update:model-value="updateColor(colorKey, $event)"
            >
              <template #prepend-inner>
                <input
                  type="color"
                  :value="getColorValue(colorKey)"
                  class="color-input"
                  @input="updateColor(colorKey, ($event.target as HTMLInputElement).value)"
                />
              </template>
              <template #append>
                <v-btn v-if="isCustomized(colorKey)" icon size="x-small" variant="text" @click="resetColor(colorKey)">
                  <v-icon size="small">mdi-restore</v-icon>
                  <v-tooltip activator="parent">Reset to default</v-tooltip>
                </v-btn>
              </template>
            </v-text-field>
          </div>
        </v-col>
      </v-row>

      <v-divider class="my-4" />

      <div class="d-flex gap-2">
        <v-btn
          v-if="hasCustomColors"
          color="warning"
          variant="outlined"
          prepend-icon="mdi-restore"
          @click="handleResetAll"
        >
          Reset All Colors
        </v-btn>

        <v-spacer />

        <v-btn variant="outlined" prepend-icon="mdi-download" @click="handleExport"> Export </v-btn>

        <v-btn variant="outlined" prepend-icon="mdi-upload" @click="handleImport"> Import </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTheme } from '@/composables/useTheme'
import type { CustomThemeColors } from '@/composables/useTheme'

const theme = useTheme()

const colorKeys: (keyof CustomThemeColors)[] = ['primary', 'secondary', 'accent', 'error', 'info', 'success', 'warning']

const localColors = ref<CustomThemeColors>({ ...theme.customColors.value })

const hasCustomColors = computed(() => {
  return Object.keys(localColors.value).length > 0
})

function getColorValue(key: keyof CustomThemeColors): string {
  return localColors.value[key] || theme.vuetifyTheme.current.value.colors[key]
}

function isCustomized(key: keyof CustomThemeColors): boolean {
  return key in localColors.value && !!localColors.value[key]
}

function updateColor(key: keyof CustomThemeColors, value: string) {
  if (value && /^#[0-9A-Fa-f]{6}$/.test(value)) {
    localColors.value[key] = value
    theme.applyCustomColors(localColors.value)
  }
}

function resetColor(key: keyof CustomThemeColors) {
  delete localColors.value[key]
  theme.applyCustomColors(localColors.value)
}

function handleResetAll() {
  localColors.value = {}
  theme.resetCustomColors()
}

function handleExport() {
  const config = theme.exportThemeConfig()
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'theme-config.json'
  a.click()
  URL.revokeObjectURL(url)
}

function handleImport() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'application/json'
  input.onchange = (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        try {
          const config = JSON.parse(event.target?.result as string)
          theme.importThemeConfig(config)
          localColors.value = { ...theme.customColors.value }
        } catch (error) {
          console.error('Failed to import theme config:', error)
        }
      }
      reader.readAsText(file)
    }
  }
  input.click()
}

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}
</script>

<style scoped>
.color-picker-item {
  padding: 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.color-picker-item:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

.color-input {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
}

.color-input::-webkit-color-swatch-wrapper {
  padding: 0;
}

.color-input::-webkit-color-swatch {
  border: 2px solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
}
</style>
