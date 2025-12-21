<template>
  <v-card variant="outlined">
    <v-card-title class="d-flex align-center justify-space-between">
      <span>Validation Results</span>
      <div class="d-flex gap-2">
        <v-tooltip text="Check configuration structure and references" location="bottom">
          <template v-slot:activator="{ props }">
            <v-btn
              v-bind="props"
              size="small"
              prepend-icon="mdi-check-circle-outline"
              :loading="loading"
              @click="emit('validate')"
            >
              Structural
            </v-btn>
          </template>
        </v-tooltip>
        <v-tooltip text="Validate data against schema with sampling" location="bottom">
          <template v-slot:activator="{ props }">
            <v-btn
              v-bind="props"
              size="small"
              prepend-icon="mdi-database-check"
              color="info"
              :loading="dataValidationLoading"
              @click="emit('validate-data')"
            >
              Data
            </v-btn>
          </template>
        </v-tooltip>
      </div>
    </v-card-title>

    <v-card-text>
      <!-- Data Validation Configuration -->
      <data-validation-config
        v-if="showDataConfig"
        :available-entities="availableEntities"
        :loading="dataValidationLoading"
        class="mb-4"
        @run="handleDataValidationRun"
      />

      <!-- Not Validated State -->
      <div v-if="!validationResult" class="text-center py-8">
        <v-icon icon="mdi-help-circle-outline" size="64" color="grey" />
        <p class="text-h6 mt-4 mb-2">Not Validated</p>
        <p class="text-grey mb-4">
          Run validation to check for configuration errors and warnings
        </p>
        <div class="d-flex gap-2 justify-center">
          <v-btn
            color="primary"
            prepend-icon="mdi-check-circle-outline"
            :loading="loading"
            @click="emit('validate')"
          >
            Structural Validation
          </v-btn>
          <v-btn
            color="info"
            variant="outlined"
            prepend-icon="mdi-cog"
            @click="showDataConfig = !showDataConfig"
          >
            Configure Data Validation
          </v-btn>
        </div>
      </div>

      <!-- Loading State -->
      <div v-else-if="loading" class="py-4">
        <v-skeleton-loader
          type="article, list-item-three-line, list-item-three-line, list-item-three-line"
          class="mb-4"
        />
        <div class="text-center">
          <v-progress-circular indeterminate color="primary" size="32" />
          <p class="mt-2 text-grey">Validating configuration...</p>
        </div>
      </div>

      <!-- Validation Results -->
      <div v-else>
        <!-- Auto-fix Suggestions -->
        <validation-suggestion
          v-if="result && autoFixableIssues.length > 0"
          :issues="allMessages"
          class="mb-4"
          @apply-fix="handleApplyFix"
          @apply-all="handleApplyAll"
          @dismiss="showSuggestions = false"
        />

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
          <v-tab value="by-category">
            By Category
            <v-badge
              v-if="errorCount + warningCount > 0"
              :content="errorCount + warningCount"
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

          <!-- By Category -->
          <v-window-item value="by-category">
            <v-expansion-panels variant="accordion">
              <!-- Structural Issues -->
              <v-expansion-panel
                v-if="structuralIssues.length > 0"
                value="structural"
              >
                <v-expansion-panel-title>
                  <div class="d-flex align-center">
                    <v-icon icon="mdi-file-tree-outline" class="mr-2" />
                    <span class="font-weight-medium">Structural</span>
                    <v-chip size="small" class="ml-2">
                      {{ structuralIssues.length }}
                    </v-chip>
                    <v-chip
                      v-if="structuralErrors.length > 0"
                      size="small"
                      color="error"
                      class="ml-2"
                    >
                      {{ structuralErrors.length }} errors
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <validation-message-list :messages="structuralIssues" />
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- Data Issues -->
              <v-expansion-panel
                v-if="dataIssues.length > 0"
                value="data"
              >
                <v-expansion-panel-title>
                  <div class="d-flex align-center">
                    <v-icon icon="mdi-database-alert" class="mr-2" />
                    <span class="font-weight-medium">Data</span>
                    <v-chip size="small" class="ml-2">
                      {{ dataIssues.length }}
                    </v-chip>
                    <v-chip
                      v-if="dataErrors.length > 0"
                      size="small"
                      color="error"
                      class="ml-2"
                    >
                      {{ dataErrors.length }} errors
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <validation-message-list :messages="dataIssues" />
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- Performance Issues -->
              <v-expansion-panel
                v-if="performanceIssues.length > 0"
                value="performance"
              >
                <v-expansion-panel-title>
                  <div class="d-flex align-center">
                    <v-icon icon="mdi-speedometer" class="mr-2" />
                    <span class="font-weight-medium">Performance</span>
                    <v-chip size="small" class="ml-2">
                      {{ performanceIssues.length }}
                    </v-chip>
                    <v-chip
                      v-if="performanceErrors.length > 0"
                      size="small"
                      color="error"
                      class="ml-2"
                    >
                      {{ performanceErrors.length }} errors
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <validation-message-list :messages="performanceIssues" />
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-window-item>
        </v-window>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ValidationResult, ValidationError } from '@/types'
import ValidationMessageList from './ValidationMessageList.vue'
import ValidationSuggestion from './ValidationSuggestion.vue'
import DataValidationConfig from './DataValidationConfig.vue'

interface Props {
  configName: string
  validationResult: ValidationResult | null
  loading: boolean
  dataValidationLoading?: boolean
  availableEntities?: string[]
}

interface ValidationConfig {
  entities?: string[]
  sampleSize?: number
  validators?: string[]
}

interface Emits {
  (e: 'validate'): void
  (e: 'validate-data', config?: ValidationConfig): void
  (e: 'apply-fix', issue: ValidationError): void
  (e: 'apply-all-fixes'): void
}

const props = withDefaults(defineProps<Props>(), {
  availableEntities: () => [],
})
const emit = defineEmits<Emits>()

const activeTab = ref('all')
const showDataConfig = ref(false)
const showSuggestions = ref(true)

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

// Category-based grouping
const result = computed(() => props.validationResult)

const structuralIssues = computed(() => {
  return allMessages.value.filter(msg => msg.category === 'structural' || !msg.category)
})

const dataIssues = computed(() => {
  return allMessages.value.filter(msg => msg.category === 'data')
})

const performanceIssues = computed(() => {
  return allMessages.value.filter(msg => msg.category === 'performance')
})

const structuralErrors = computed(() => {
  return structuralIssues.value.filter(msg => msg.severity === 'error')
})

const dataErrors = computed(() => {
  return dataIssues.value.filter(msg => msg.severity === 'error')
})

const performanceErrors = computed(() => {
  return performanceIssues.value.filter(msg => msg.severity === 'error')
})

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _totalIssues = computed(() => {
  return errorCount.value + warningCount.value
})

const autoFixableIssues = computed(() => {
  return allMessages.value.filter(msg => msg.auto_fixable === true)
})

// Methods
function handleDataValidationRun(config: ValidationConfig) {
  showDataConfig.value = false
  emit('validate-data', config)
}

function handleApplyFix(issue: ValidationError) {
  emit('apply-fix', issue)
}

function handleApplyAll() {
  emit('apply-all-fixes')
}
</script>
