<template>
  <v-container fluid class="pa-6">
    <!-- Header -->
    <v-row>
      <v-col>
        <div class="d-flex align-center justify-space-between mb-6">
          <div class="d-flex align-center">
            <v-btn icon="mdi-arrow-left" variant="text" @click="$router.push({ name: 'projects' })" />
            <div class="ml-2">
              <h1 class="text-h4">{{ projectName }}</h1>
              <div class="d-flex align-center mt-1">
                <v-chip
                  v-if="entityCount > 0"
                  size="small"
                  variant="outlined"
                  prepend-icon="mdi-cube-outline"
                  class="mr-2"
                >
                  {{ entityCount }} {{ entityCount === 1 ? 'entity' : 'entities' }}
                </v-chip>
                <v-chip
                  v-if="validationResult"
                  size="small"
                  :color="validationChipColor"
                  variant="tonal"
                  :prepend-icon="validationChipIcon"
                >
                  {{ validationChipText }}
                </v-chip>
              </div>
            </div>
          </div>

          <div class="d-flex gap-2">
            <v-btn variant="outlined" prepend-icon="mdi-play-circle-outline" color="success" @click="handleTestRun">
              Test Run
            </v-btn>
            <v-btn
              variant="outlined"
              prepend-icon="mdi-check-circle-outline"
              :loading="validationLoading"
              @click="handleValidate"
            >
              Validate
            </v-btn>
            <v-btn variant="outlined" prepend-icon="mdi-history" @click="showBackupsDialog = true"> Backups </v-btn>
            <v-btn color="primary" prepend-icon="mdi-content-save" :disabled="!hasUnsavedChanges" @click="handleSave">
              Save Changes
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Session Indicator -->
    <v-row>
      <v-col>
        <session-indicator :project-name="projectName" />
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="projectLoading">
      <v-col cols="12" class="text-center py-12">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-grey">Loading project...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-alert v-else-if="projectError" type="error" variant="tonal">
      <v-alert-title>Error Loading Project</v-alert-title>
      {{ projectError }}
      <template #append>
        <v-btn variant="text" @click="handleRefresh">Retry</v-btn>
      </template>
    </v-alert>

    <!-- Main Content -->
    <v-row v-else-if="selectedProject">
      <v-col cols="12">
        <v-tabs v-model="activeTab" bg-color="transparent">
          <v-tab value="entities">
            <v-icon icon="mdi-cube-outline" class="mr-2" />
            Entities
          </v-tab>
          <v-tab value="dependencies">
            <v-icon icon="mdi-graph-outline" class="mr-2" />
            Dependencies
          </v-tab>
          <v-tab value="reconciliation">
            <v-icon icon="mdi-link-variant" class="mr-2" />
            Reconciliation
          </v-tab>
          <v-tab value="data-sources">
            <v-icon icon="mdi-database-outline" class="mr-2" />
            Data Sources
          </v-tab>
          <v-tab value="validation">
            <v-icon icon="mdi-check-circle-outline" class="mr-2" />
            Validation
            <v-badge
              v-if="validationResult && (hasErrors || hasWarnings)"
              :content="errorCount + warningCount"
              :color="hasErrors ? 'error' : 'warning'"
              inline
              class="ml-2"
            />
          </v-tab>
          <v-tab value="metadata">
            <v-icon icon="mdi-information-outline" class="mr-2" />
            Metadata
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab" class="mt-4">
          <!-- Entities Tab -->
          <v-window-item value="entities">
            <entity-list-card :project-name="projectName" @entity-updated="handleEntityUpdated" />
          </v-window-item>

          <!-- Dependencies Tab -->
          <v-window-item value="dependencies">
            <dependency-graph :project-name="projectName" @edit-entity="handleEditEntity" />
          </v-window-item>

          <!-- Reconciliation Tab -->
          <v-window-item value="reconciliation">
            <reconciliation-view :project-name="projectName" />
          </v-window-item>

          <!-- Data Sources Tab -->
          <v-window-item value="data-sources">
            <configuration-data-sources :project-name="projectName" @updated="handleDataSourcesUpdated" />
          </v-window-item>

          <!-- Validation Tab -->
          <v-window-item value="validation">
            <validation-panel
              :project-name="projectName"
              :validation-result="mergedValidationResult"
              :loading="validationLoading"
              :data-validation-loading="dataValidationLoading"
              :available-entities="entityNames"
              @validate="handleValidate"
              @validate-data="handleDataValidate"
              @apply-fix="handleApplyFix"
              @apply-all-fixes="handleApplyAllFixes"
            />
          </v-window-item>

          <!-- Metadata Tab -->
          <v-window-item value="metadata">
            <metadata-editor :project-name="projectName" />
          </v-window-item>
        </v-window>
      </v-col>
    </v-row>

    <!-- Backups Dialog -->
    <v-dialog v-model="showBackupsDialog" max-width="600">
      <v-card>
        <v-card-title>
          <v-icon icon="mdi-history" class="mr-2" />
          Project Backups
        </v-card-title>
        <v-card-text>
          <v-list v-if="backups.length > 0">
            <v-list-item
              v-for="backup in backups"
              :key="backup.file_path"
              @click="handleRestoreBackup(backup.file_path)"
            >
              <template #prepend>
                <v-icon icon="mdi-file-clock-outline" />
              </template>
              <v-list-item-title>{{ backup.file_name }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatBackupDate(backup.created_at) }}
              </v-list-item-subtitle>
              <template #append>
                <v-btn
                  icon="mdi-restore"
                  variant="text"
                  size="small"
                  @click.stop="handleRestoreBackup(backup.file_path)"
                />
              </template>
            </v-list-item>
          </v-list>
          <v-alert v-else type="info" variant="tonal"> No backups available for this project. </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showBackupsDialog = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Preview Fixes Modal -->
    <preview-fixes-modal
      v-model:show="showPreviewModal"
      :preview="fixPreview"
      :loading="fixPreviewLoading"
      :error="fixPreviewError"
      @apply="handleApplyFixesConfirmed"
      @cancel="handleCancelPreview"
    />

    <!-- Success Snackbar with Animation -->
    <v-scale-transition>
      <v-snackbar v-if="showSuccessSnackbar" v-model="showSuccessSnackbar" color="success" timeout="3000">
        {{ successMessage }}
        <template #actions>
          <v-btn variant="text" @click="showSuccessSnackbar = false"> Close </v-btn>
        </template>
      </v-snackbar>
    </v-scale-transition>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { useProjects, useEntities, useValidation } from '@/composables'
import { useDataValidation } from '@/composables/useDataValidation'
import { useSession } from '@/composables/useSession'
import EntityListCard from '@/components/entities/EntityListCard.vue'
import ValidationPanel from '@/components/validation/ValidationPanel.vue'
import PreviewFixesModal from '@/components/validation/PreviewFixesModal.vue'
import ConfigurationDataSources from '@/components/ConfigurationDataSources.vue'
import SessionIndicator from '@/components/SessionIndicator.vue'
import DependencyGraph from '@/components/dependencies/DependencyGraph.vue'
import ReconciliationView from '@/components/reconciliation/ReconciliationView.vue'
import MetadataEditor from '@/components/MetadataEditor.vue'

const route = useRoute()
const projectName = computed(() => route.params.name as string)

// Composables
const {
  selectedProject,
  loading: projectLoading,
  error: projectError,
  hasUnsavedChanges,
  backups,
  select,
  update,
  clearError,
  fetchBackups,
  restore,
  markAsChanged,
} = useProjects({ autoFetch: false })

const { entityCount, entities } = useEntities({
  projectName: projectName.value,
  autoFetch: true,
})

const entityNames = computed(() => {
  return entities.value?.map((e) => e.name) ?? []
})

// Session management
const { startSession, saveWithVersionCheck, hasActiveSession } = useSession()

const {
  validationResult,
  loading: validationLoading,
  hasErrors,
  hasWarnings,
  errorCount,
  warningCount,
  validate,
} = useValidation({
  projectName: projectName.value,
  autoValidate: false,
})

const {
  loading: dataValidationLoading,
  result: dataValidationResult,
  validateData,
  previewFixes,
  applyFixes,
  autoFixableIssues,
} = useDataValidation()

// Local state
const activeTab = ref('entities')
const showBackupsDialog = ref(false)
const showSuccessSnackbar = ref(false)
const successMessage = ref('')
const showPreviewModal = ref(false)
const fixPreview = ref<any>(null)
const fixPreviewLoading = ref(false)
const fixPreviewError = ref<string | null>(null)

// Computed
const mergedValidationResult = computed(() => {
  if (!validationResult.value && !dataValidationResult.value) return null

  const structural = validationResult.value
  const data = dataValidationResult.value

  if (!structural && data) return data
  if (structural && !data) return structural
  if (!structural || !data) return null

  // Merge both results
  return {
    is_valid: structural.is_valid && data.is_valid,
    errors: [...structural.errors, ...data.errors],
    warnings: [...structural.warnings, ...data.warnings],
    info: [...(structural.info || []), ...(data.info || [])],
    error_count: structural.error_count + data.error_count,
    warning_count: structural.warning_count + data.warning_count,
  }
})

const validationChipColor = computed(() => {
  if (!mergedValidationResult.value) return 'default'
  if (hasErrors.value) return 'error'
  if (hasWarnings.value) return 'warning'
  return 'success'
})

const validationChipIcon = computed(() => {
  if (!validationResult.value) return 'mdi-help-circle'
  if (hasErrors.value) return 'mdi-alert-circle'
  if (hasWarnings.value) return 'mdi-alert'
  return 'mdi-check-circle'
})

const validationChipText = computed(() => {
  if (!validationResult.value) return 'Not validated'
  if (hasErrors.value) return `${errorCount.value} errors`
  if (hasWarnings.value) return `${warningCount.value} warnings`
  return 'Valid'
})

// Methods
function handleTestRun() {
  window.location.href = `/test-run/${projectName.value}`
}

async function handleValidate() {
  try {
    await validate(projectName.value)
    successMessage.value = 'Project validated successfully'
    showSuccessSnackbar.value = true
  } catch (err) {
    console.error('Validation failed:', err)
  }
}

// Debounced validation to prevent excessive API calls (500ms delay)
// Usage: Replace direct handleValidate() calls with debouncedValidate()
// in scenarios with rapid changes (e.g., auto-save, real-time editing)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const debouncedValidate = useDebounceFn(handleValidate, 500)

async function handleDataValidate(project?: any) {
  try {
    const entityNames = project?.entities
    await validateData(projectName.value, entityNames)
    successMessage.value = 'Data validation completed'
    showSuccessSnackbar.value = true
  } catch (err) {
    console.error('Data validation failed:', err)
  }
}

async function handleApplyFix(issue: any) {
  // Single fix - show preview modal
  await handlePreviewFixes([issue])
}

async function handleApplyAllFixes() {
  // All auto-fixable issues - show preview modal
  const issues = autoFixableIssues.value
  if (issues.length === 0) {
    successMessage.value = 'No auto-fixable issues found'
    showSuccessSnackbar.value = true
    return
  }
  await handlePreviewFixes(issues)
}

async function handlePreviewFixes(issues: any[]) {
  try {
    fixPreviewLoading.value = true
    fixPreviewError.value = null
    showPreviewModal.value = true

    const preview = await previewFixes(projectName.value, issues)
    fixPreview.value = preview
  } catch (err) {
    fixPreviewError.value = err instanceof Error ? err.message : 'Failed to preview fixes'
    console.error('Preview fixes error:', err)
  } finally {
    fixPreviewLoading.value = false
  }
}

async function handleApplyFixesConfirmed() {
  try {
    const issues = autoFixableIssues.value
    const result = await applyFixes(projectName.value, issues)

    showPreviewModal.value = false
    successMessage.value = `Successfully applied ${result.fixes_applied} fixes. Backup: ${result.backup_path}`
    showSuccessSnackbar.value = true

    // Reload project and re-validate
    await handleRefresh()
    await handleValidate()
  } catch (err) {
    fixPreviewError.value = err instanceof Error ? err.message : 'Failed to apply fixes'
    console.error('Apply fixes error:', err)
  }
}

function handleCancelPreview() {
  showPreviewModal.value = false
  fixPreview.value = null
  fixPreviewError.value = null
}

async function handleSave() {
  if (!selectedProject.value) return

  try {
    // Start session if not already active
    if (!hasActiveSession.value) {
      await startSession(projectName.value)
    }

    // Save with version check
    const saved = await saveWithVersionCheck()

    if (saved) {
      successMessage.value = 'Project saved successfully'
      showSuccessSnackbar.value = true
    } else {
      // Version conflict - show error
      successMessage.value = 'Save failed: Version conflict detected. Another user modified this project.'
      showSuccessSnackbar.value = true
    }
  } catch (err) {
    console.error('Failed to save project:', err)
    successMessage.value = err instanceof Error ? err.message : 'Failed to save project'
    showSuccessSnackbar.value = true
  }
}

async function handleRefresh() {
  clearError()
  if (projectName.value) {
    await select(projectName.value)
  }
}

function handleEntityUpdated() {
  markAsChanged()
}

function handleEditEntity(entityName: string) {
  // Switch to entities tab and trigger entity edit
  activeTab.value = 'entities'
  // The entity list will need to handle the actual editing
  // We could potentially pass the entity name via a ref or event bus
  console.log('Edit entity requested:', entityName)
}

async function handleDataSourcesUpdated() {
  // Reload project after data source changes
  await handleRefresh()
}

async function handleRestoreBackup(backupPath: string) {
  try {
    await restore(projectName.value, backupPath)
    successMessage.value = 'Backup restored successfully'
    showSuccessSnackbar.value = true
    showBackupsDialog.value = false
  } catch (err) {
    console.error('Failed to restore backup:', err)
  }
}

function formatBackupDate(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString()
}

// Lifecycle
onMounted(async () => {
  if (projectName.value) {
    await select(projectName.value)
    await fetchBackups(projectName.value)
    // Start editing session
    await startSession(projectName.value)
  }
})

// Watch for project name changes
watch(
  () => projectName.value,
  async (newName) => {
    if (newName) {
      await select(newName)
      await fetchBackups(newName)
    }
  }
)
</script>

<style scoped>
.gap-2 {
  gap: 0.5rem;
}
</style>
