<template>
  <v-card variant="outlined">
    <v-card-title class="d-flex align-center justify-space-between">
      <span>Validation Results</span>
      <div class="d-flex gap-2">
        <v-tooltip text="Check project structure and references" location="bottom">
          <template v-slot:activator="{ props }">
            <v-btn
              v-bind="props"
              size="small"
              prepend-icon="mdi-check-circle-outline"
              :loading="loading"
              @click="emit('validate')"
            >
              Run YAML Validation
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
              Run Data Validation
            </v-btn>
          </template>
        </v-tooltip>
        <v-tooltip text="Check project entities conform to target model specification" location="bottom">
          <template v-slot:activator="{ props }">
            <v-btn
              v-bind="props"
              size="small"
              prepend-icon="mdi-check-decagram-outline"
              color="deep-purple"
              :loading="conformanceValidationLoading"
              @click="emit('validate-target-model')"
            >
              Check Conformance
            </v-btn>
          </template>
        </v-tooltip>
        <v-tooltip text="Configure data validation options" location="bottom">
          <template v-slot:activator="{ props }">
            <v-btn
              v-bind="props"
              size="small"
              prepend-icon="mdi-cog"
              color="info"
              @click="showDataConfig = !showDataConfig"
            >
              Options
            </v-btn>
          </template>
        </v-tooltip>
        <v-tooltip text="Copy validation results to clipboard" location="bottom">
          <template v-slot:activator="{ props }">
            <v-btn
              v-bind="props"
              size="small"
              prepend-icon="mdi-content-copy"
              :disabled="!validationResult || (errorCount === 0 && warningCount === 0)"
              @click="copyToClipboard"
            >
              Copy
            </v-btn>
          </template>
        </v-tooltip>
      </div>
    </v-card-title>

    <v-card-text>
      <!-- Data Validation Project -->
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
        <p class="text-grey mb-4">Run validation to check for project errors and warnings</p>
      </div>

      <!-- Loading State -->
      <div v-else-if="loading" class="py-4">
        <v-skeleton-loader
          type="article, list-item-three-line, list-item-three-line, list-item-three-line"
          class="mb-4"
        />
        <div class="text-center">
          <v-progress-circular indeterminate color="primary" size="32" />
          <p class="mt-2 text-grey">Validating project...</p>
        </div>
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
                  {{ errorCount }} {{ errorCount === 1 ? 'error' : 'errors' }}, {{ warningCount }}
                  {{ warningCount === 1 ? 'warning' : 'warnings' }}
                </p>
              </div>
            </div>
          </v-card-text>
        </v-card>

        <!-- Tabs for Errors and Warnings -->
        <v-tabs v-model="activeTab" bg-color="transparent" class="mb-4">
          <v-tab value="all">
            All Issues
            <v-badge v-if="errorCount + warningCount > 0" :content="errorCount + warningCount" inline class="ml-2" />
          </v-tab>
          <v-tab value="errors">
            Errors
            <v-badge v-if="errorCount > 0" :content="errorCount" color="error" inline class="ml-2" />
          </v-tab>
          <v-tab value="warnings">
            Warnings
            <v-badge v-if="warningCount > 0" :content="warningCount" color="warning" inline class="ml-2" />
          </v-tab>
          <v-tab value="by-category">
            By Category
            <v-badge v-if="errorCount + warningCount > 0" :content="errorCount + warningCount" inline class="ml-2" />
          </v-tab>
          <v-tab value="by-entity">
            By Entity
            <v-badge v-if="entityScopedIssues.length > 0" :content="entityScopedIssues.length" inline class="ml-2" />
          </v-tab>
        </v-tabs>

        <!-- Messages List -->
        <v-window v-model="activeTab">
          <!-- All Issues -->
          <v-window-item value="all">
            <validation-message-list
              :messages="allMessages"
              :empty-message="'No validation issues found. Project looks good!'"
              @open-entity="handleOpenEntity"
            />
          </v-window-item>

          <!-- Errors Only -->
          <v-window-item value="errors">
            <validation-message-list :messages="errors" :empty-message="'No errors found'" @open-entity="handleOpenEntity" />
          </v-window-item>

          <!-- Warnings Only -->
          <v-window-item value="warnings">
            <validation-message-list :messages="warnings" :empty-message="'No warnings found'" @open-entity="handleOpenEntity" />
          </v-window-item>

          <!-- By Category -->
          <v-window-item value="by-category">
            <v-expansion-panels variant="accordion">
              <!-- Structural Issues -->
              <v-expansion-panel v-if="structuralIssues.length > 0" value="structural">
                <v-expansion-panel-title>
                  <div class="d-flex align-center">
                    <v-icon icon="mdi-file-tree-outline" class="mr-2" />
                    <span class="font-weight-medium">Structural</span>
                    <v-chip size="small" class="ml-2">
                      {{ structuralIssues.length }}
                    </v-chip>
                    <v-chip v-if="structuralErrors.length > 0" size="small" color="error" class="ml-2">
                      {{ structuralErrors.length }} errors
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <validation-message-list :messages="structuralIssues" @open-entity="handleOpenEntity" />
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- Data Issues -->
              <v-expansion-panel v-if="dataIssues.length > 0" value="data">
                <v-expansion-panel-title>
                  <div class="d-flex align-center">
                    <v-icon icon="mdi-database-alert" class="mr-2" />
                    <span class="font-weight-medium">Data</span>
                    <v-chip size="small" class="ml-2">
                      {{ dataIssues.length }}
                    </v-chip>
                    <v-chip v-if="dataErrors.length > 0" size="small" color="error" class="ml-2">
                      {{ dataErrors.length }} errors
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <validation-message-list :messages="dataIssues" @open-entity="handleOpenEntity" />
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- Performance Issues -->
              <v-expansion-panel v-if="performanceIssues.length > 0" value="performance">
                <v-expansion-panel-title>
                  <div class="d-flex align-center">
                    <v-icon icon="mdi-speedometer" class="mr-2" />
                    <span class="font-weight-medium">Performance</span>
                    <v-chip size="small" class="ml-2">
                      {{ performanceIssues.length }}
                    </v-chip>
                    <v-chip v-if="performanceErrors.length > 0" size="small" color="error" class="ml-2">
                      {{ performanceErrors.length }} errors
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <validation-message-list :messages="performanceIssues" @open-entity="handleOpenEntity" />
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- Conformance Issues -->
              <v-expansion-panel v-if="conformanceIssues.length > 0" value="conformance">
                <v-expansion-panel-title>
                  <div class="d-flex align-center">
                    <v-icon icon="mdi-check-decagram-outline" class="mr-2" color="deep-purple" />
                    <span class="font-weight-medium">Conformance</span>
                    <v-chip size="small" class="ml-2">
                      {{ conformanceIssues.length }}
                    </v-chip>
                    <v-chip v-if="conformanceErrors.length > 0" size="small" color="error" class="ml-2">
                      {{ conformanceErrors.length }} errors
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <validation-message-list :messages="conformanceIssues" @open-entity="handleOpenEntity" />
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-window-item>

          <!-- By Entity / Branch -->
          <v-window-item value="by-entity">
            <div v-if="entityScopedIssues.length === 0" class="text-center py-8">
              <v-icon icon="mdi-check-circle" size="48" color="success" />
              <p class="text-body-1 mt-4">No validation issues found. Project looks good!</p>
            </div>

            <v-expansion-panels v-else variant="accordion">
              <v-expansion-panel v-for="group in entityScopedIssues" :key="group.key" :value="group.key">
                <v-expansion-panel-title>
                  <div class="d-flex align-center flex-wrap ga-2">
                    <v-icon :icon="group.entity ? 'mdi-cube' : 'mdi-cog-outline'" class="mr-2" />
                    <span class="font-weight-medium">{{ group.entity || 'General' }}</span>
                    <v-chip size="small">{{ group.messages.length }}</v-chip>
                    <v-chip v-if="group.branchGroups.length > 0" size="small" color="teal" variant="outlined">
                      {{ group.branchGroups.length }} branches
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <validation-message-list
                    v-if="group.entityMessages.length > 0"
                    :messages="group.entityMessages"
                    :empty-message="'No entity-level issues found'"
                    @open-entity="handleOpenEntity"
                  />

                  <v-expansion-panels v-if="group.branchGroups.length > 0" variant="accordion" class="mt-3">
                    <v-expansion-panel v-for="branchGroup in group.branchGroups" :key="branchGroup.key" :value="branchGroup.key">
                      <v-expansion-panel-title>
                        <div class="d-flex align-center flex-wrap ga-2">
                          <v-icon icon="mdi-source-branch" color="teal" class="mr-2" />
                          <span class="font-weight-medium">{{ formatBranchGroupLabel(branchGroup.branchName, branchGroup.branchSource) }}</span>
                          <v-chip size="small">{{ branchGroup.messages.length }}</v-chip>
                        </div>
                      </v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <validation-message-list :messages="branchGroup.messages" @open-entity="handleOpenEntity" />
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
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
import { useNotification } from '@/composables/useNotification'
import { groupByEntityScope, type ValidationResult } from '@/types'
import ValidationMessageList from './ValidationMessageList.vue'
import DataValidationConfig from './DataValidationConfig.vue'

interface Props {
  projectName: string
  validationResult: ValidationResult | null
  loading: boolean
  dataValidationLoading?: boolean
  conformanceValidationLoading?: boolean
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
  (e: 'validate-target-model'): void
  (e: 'open-entity', entityName: string): void
}

const props = withDefaults(defineProps<Props>(), {
  availableEntities: () => [],
})
const emit = defineEmits<Emits>()

const activeTab = ref('all')
const showDataConfig = ref(false)

const { success, error } = useNotification()

// Computed
const errorCount = computed(() => props.validationResult?.error_count ?? 0)
const warningCount = computed(() => props.validationResult?.warning_count ?? 0)
const errors = computed(() => props.validationResult?.errors ?? [])
const warnings = computed(() => props.validationResult?.warnings ?? [])
const allMessages = computed(() => [...errors.value, ...warnings.value])
const entityScopedIssues = computed(() => groupByEntityScope(allMessages.value))

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
const structuralIssues = computed(() => {
  return allMessages.value.filter((msg) => msg.category === 'structural' || !msg.category)
})

const dataIssues = computed(() => {
  return allMessages.value.filter((msg) => msg.category === 'data')
})

const performanceIssues = computed(() => {
  return allMessages.value.filter((msg) => msg.category === 'performance')
})

const structuralErrors = computed(() => {
  return structuralIssues.value.filter((msg) => msg.severity === 'error')
})

const dataErrors = computed(() => {
  return dataIssues.value.filter((msg) => msg.severity === 'error')
})

const performanceErrors = computed(() => {
  return performanceIssues.value.filter((msg) => msg.severity === 'error')
})

const conformanceIssues = computed(() => {
  return allMessages.value.filter((msg) => msg.category === 'conformance')
})

const conformanceErrors = computed(() => {
  return conformanceIssues.value.filter((msg) => msg.severity === 'error')
})

// Methods
function handleDataValidationRun(config: ValidationConfig) {
  showDataConfig.value = false
  emit('validate-data', config)
}

function handleOpenEntity(entityName: string) {
  emit('open-entity', entityName)
}

async function copyToClipboard() {
  if (!props.validationResult || allMessages.value.length === 0) {
    return
  }

  try {
    // Create tabular format with headers
    const headers = ['Severity', 'Entity', 'Branch', 'Branch Source', 'Field', 'Category', 'Priority', 'Code', 'Message', 'Suggestion']
    const separator = '\t'
    const headerRow = headers.join(separator)

    // Format each message as a row
    const rows = allMessages.value.map((msg) => {
      return [
        msg.severity || '',
        msg.entity || '',
        msg.branch_name || '',
        msg.branch_source || '',
        msg.field || '',
        msg.category || '',
        msg.priority || '',
        msg.code || '',
        msg.message || '',
        msg.suggestion || '',
      ].join(separator)
    })

    // Combine header and rows
    const tsvContent = [headerRow, ...rows].join('\n')

    // Copy to clipboard
    await navigator.clipboard.writeText(tsvContent)

    success(
      `Copied ${allMessages.value.length} validation ${allMessages.value.length === 1 ? 'issue' : 'issues'} to clipboard`
    )
  } catch (err) {
    console.error('Failed to copy to clipboard:', err)
    error('Failed to copy to clipboard')
  }
}

function formatBranchGroupLabel(branchName: string | null, branchSource: string | null): string {
  if (branchName && branchSource) {
    return `${branchName} (${branchSource})`
  }

  if (branchName) {
    return branchName
  }

  return branchSource || 'Unnamed branch'
}
</script>
