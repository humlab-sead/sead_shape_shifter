<template>
  <v-card variant="outlined">
    <v-card-title class="d-flex align-center justify-space-between">
      <span>Validation Results</span>
      <v-btn
        size="small"
        prepend-icon="mdi-refresh"
        :loading="loading"
        @click="emit('validate')"
      >
        Re-validate
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Not Validated State -->
      <div v-if="!validationResult" class="text-center py-8">
        <v-icon icon="mdi-help-circle-outline" size="64" color="grey" />
        <p class="text-h6 mt-4 mb-2">Not Validated</p>
        <p class="text-grey mb-4">
          Run validation to check for configuration errors and warnings
        </p>
        <v-btn
          color="primary"
          prepend-icon="mdi-check-circle-outline"
          :loading="loading"
          @click="emit('validate')"
        >
          Validate Now
        </v-btn>
      </div>

      <!-- Loading State -->
      <div v-else-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" />
        <p class="mt-2 text-grey">Validating configuration...</p>
      </div>

      <!-- Validation Results -->
      <div v-else>
        <!-- Summary Card -->
        <v-card variant="tonal" :color="summaryColor" class="mb-4">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon :icon="summaryIcon" size="48" class="mr-4" />
              <div>
                <p class="text-h6 mb-1">{{ summaryTitle }}</p>
                <p class="text-body-2">
                  {{ errorCount }} {{ errorCount === 1 ? 'error' : 'errors' }},
                  {{ warningCount }} {{ warningCount === 1 ? 'warning' : 'warnings' }}
                </p>
              </div>
            </div>
          </v-card-text>
        </v-card>

        <!-- Tabs for Errors and Warnings -->
        <v-tabs v-model="activeTab" bg-color="transparent" class="mb-4">
          <v-tab value="all">
            All Issues
            <v-badge
              v-if="errorCount + warningCount > 0"
              :content="errorCount + warningCount"
              inline
              class="ml-2"
            />
          </v-tab>
          <v-tab value="errors">
            Errors
            <v-badge
              v-if="errorCount > 0"
              :content="errorCount"
              color="error"
              inline
              class="ml-2"
            />
          </v-tab>
          <v-tab value="warnings">
            Warnings
            <v-badge
              v-if="warningCount > 0"
              :content="warningCount"
              color="warning"
              inline
              class="ml-2"
            />
          </v-tab>
        </v-tabs>

        <!-- Messages List -->
        <v-window v-model="activeTab">
          <!-- All Issues -->
          <v-window-item value="all">
            <validation-message-list
              :messages="allMessages"
              :empty-message="'No validation issues found. Configuration looks good!'"
            />
          </v-window-item>

          <!-- Errors Only -->
          <v-window-item value="errors">
            <validation-message-list
              :messages="errors"
              :empty-message="'No errors found'"
            />
          </v-window-item>

          <!-- Warnings Only -->
          <v-window-item value="warnings">
            <validation-message-list
              :messages="warnings"
              :empty-message="'No warnings found'"
            />
          </v-window-item>
        </v-window>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ValidationResult } from '@/types'
import ValidationMessageList from './ValidationMessageList.vue'

interface Props {
  configName: string
  validationResult: ValidationResult | null
  loading: boolean
}

interface Emits {
  (e: 'validate'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const activeTab = ref('all')

// Computed
const errorCount = computed(() => props.validationResult?.error_count ?? 0)
const warningCount = computed(() => props.validationResult?.warning_count ?? 0)
const errors = computed(() => props.validationResult?.errors ?? [])
const warnings = computed(() => props.validationResult?.warnings ?? [])
const allMessages = computed(() => [...errors.value, ...warnings.value])

const summaryColor = computed(() => {
  if (errorCount.value > 0) return 'error'
  if (warningCount.value > 0) return 'warning'
  return 'success'
})

const summaryIcon = computed(() => {
  if (errorCount.value > 0) return 'mdi-alert-circle'
  if (warningCount.value > 0) return 'mdi-alert'
  return 'mdi-check-circle'
})

const summaryTitle = computed(() => {
  if (errorCount.value > 0) return 'Validation Failed'
  if (warningCount.value > 0) return 'Validation Passed with Warnings'
  return 'Validation Passed'
})
</script>
