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
            <v-btn variant="outlined" prepend-icon="mdi-play-circle" color="success" @click="showExecuteDialog = true">
              Execute
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
          <v-tab value="yaml">
            <v-icon icon="mdi-code-braces" class="mr-2" />
            YAML
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab" class="mt-4">
          <!-- Entities Tab -->
          <v-window-item value="entities">
            <entity-list-card :project-name="projectName" :entity-to-edit="entityToEdit" @entity-updated="handleEntityUpdated" />
          </v-window-item>

          <!-- Dependencies Tab -->
          <v-window-item value="dependencies">
            <!-- Circular Dependencies Alert -->
            <circular-dependency-alert v-if="hasCircularDependencies" :cycles="cycles" class="mb-4" />

            <!-- Graph Controls -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text class="d-flex align-center gap-4">
                <v-btn-toggle v-model="layoutType" mandatory density="compact">
                  <v-btn value="hierarchical" prepend-icon="mdi-file-tree"> Hierarchical </v-btn>
                  <v-btn value="force" prepend-icon="mdi-vector-arrange-above"> Force-Directed </v-btn>
                </v-btn-toggle>

                <v-divider vertical />

                <v-switch v-model="showNodeLabels" label="Show Node Labels" density="compact" hide-details />
                <v-switch v-model="showEdgeLabels" label="Show Edge Labels" density="compact" hide-details />

                <v-switch
                  v-model="highlightCycles"
                  label="Highlight Cycles"
                  density="compact"
                  hide-details
                  :disabled="!hasCircularDependencies"
                />

                <v-switch
                  v-model="showSourceNodes"
                  label="Show Source Nodes"
                  density="compact"
                  hide-details
                />

                <v-spacer />

                <v-btn
                  variant="outlined"
                  prepend-icon="mdi-information-outline"
                  size="small"
                  @click="showLegend = !showLegend"
                >
                  Legend
                </v-btn>

                <v-chip prepend-icon="mdi-cube-outline"> {{ depStatistics.nodeCount }} nodes </v-chip>
                <v-chip prepend-icon="mdi-arrow-right"> {{ depStatistics.edgeCount }} edges </v-chip>
              </v-card-text>
            </v-card>

            <!-- Loading State -->
            <v-card v-if="dependenciesLoading" variant="outlined" class="text-center py-12">
              <v-progress-circular indeterminate color="primary" size="64" />
              <p class="mt-4 text-grey">Loading dependency graph...</p>
            </v-card>

            <!-- Error State -->
            <v-alert v-else-if="dependenciesError" type="error" variant="tonal">
              <v-alert-title>Error Loading Graph</v-alert-title>
              {{ dependenciesError }}
              <template #append>
                <v-btn variant="text" @click="handleRefreshDependencies">Retry</v-btn>
              </template>
            </v-alert>

            <!-- Graph Container -->
            <v-card v-else-if="dependencyGraph" variant="outlined">
              <v-card-text class="pa-0">
                <div ref="graphContainer" class="graph-container" />
              </v-card-text>
              <v-card-actions class="justify-end">
                <v-btn variant="text" prepend-icon="mdi-fit-to-screen" size="small" @click="handleFit"> Fit </v-btn>
                <v-btn variant="text" prepend-icon="mdi-magnify-plus" size="small" @click="handleZoomIn">
                  Zoom In
                </v-btn>
                <v-btn variant="text" prepend-icon="mdi-magnify-minus" size="small" @click="handleZoomOut">
                  Zoom Out
                </v-btn>
                <v-btn variant="text" prepend-icon="mdi-refresh" size="small" @click="handleResetView">
                  Reset View
                </v-btn>
                <v-divider vertical class="mx-2" />
                <v-btn variant="text" prepend-icon="mdi-download" size="small" @click="handleExportPNG">
                  Export PNG
                </v-btn>
              </v-card-actions>
            </v-card>

            <!-- Empty State -->
            <v-card v-else variant="outlined" class="text-center py-12">
              <v-icon icon="mdi-graph-outline" size="64" color="grey" />
              <h3 class="text-h6 mt-4 mb-2">No Graph Data</h3>
              <p class="text-grey mb-4">No dependency data available for this project</p>
            </v-card>

            <!-- Legend Dialog -->
            <v-dialog v-model="showLegend" max-width="500">
              <node-legend :show-source-nodes="showSourceNodes" @close="showLegend = false" />
            </v-dialog>

            <!-- Entity Details Drawer -->
            <v-navigation-drawer v-model="showDetailsDrawer" location="right" temporary width="400">
              <template v-if="selectedNode">
                <v-toolbar color="primary">
                  <v-toolbar-title>{{ selectedNode }}</v-toolbar-title>
                  <v-btn icon="mdi-close" @click="showDetailsDrawer = false" />
                </v-toolbar>

                <v-list>
                  <v-list-item>
                    <v-list-item-title>Entity Name</v-list-item-title>
                    <v-list-item-subtitle>{{ selectedNodeInfo?.id }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item>
                    <v-list-item-title>Depth</v-list-item-title>
                    <v-list-item-subtitle>{{ selectedNodeInfo?.depth ?? 'N/A' }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item>
                    <v-list-item-title>Topological Order</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ selectedNodeInfo?.topologicalOrder ?? 'N/A' }}
                    </v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item>
                    <v-list-item-title>Dependencies</v-list-item-title>
                    <v-list-item-subtitle>
                      <v-chip
                        v-for="dep in selectedNodeInfo?.dependencies ?? []"
                        :key="dep"
                        size="small"
                        class="mr-1 mt-1"
                      >
                        {{ dep }}
                      </v-chip>
                      <span v-if="(selectedNodeInfo?.dependencies ?? []).length === 0">None</span>
                    </v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item>
                    <v-list-item-title>Dependents</v-list-item-title>
                    <v-list-item-subtitle>
                      <v-chip
                        v-for="dependent in selectedNodeInfo?.dependents ?? []"
                        :key="dependent"
                        size="small"
                        class="mr-1 mt-1"
                      >
                        {{ dependent }}
                      </v-chip>
                      <span v-if="(selectedNodeInfo?.dependents ?? []).length === 0">None</span>
                    </v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item v-if="isInCycle(selectedNode)">
                    <v-alert type="warning" variant="tonal" density="compact">
                      This entity is part of a circular dependency
                    </v-alert>
                  </v-list-item>
                </v-list>

                <v-divider />

                <v-card-actions>
                  <v-btn variant="text" prepend-icon="mdi-pencil" block @click="handleEditEntity(selectedNode)">
                    Edit Entity
                  </v-btn>
                </v-card-actions>
              </template>
            </v-navigation-drawer>
          </v-window-item>

          <!-- Reconciliation Tab -->
          <v-window-item value="reconciliation">
            <reconciliation-view :project-name="projectName" />
          </v-window-item>

          <!-- Data Sources Tab -->
          <v-window-item value="data-sources">
            <project-data-sources :project-name="projectName" @updated="handleDataSourcesUpdated" />
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

          <!-- YAML Tab -->
          <v-window-item value="yaml">
            <v-card variant="outlined">
              <v-card-title class="d-flex align-center justify-space-between">
                <div>
                  <v-icon icon="mdi-code-braces" class="mr-2" />
                  Edit Project YAML
                </div>
                <div class="d-flex gap-2">
                  <v-btn
                    variant="outlined"
                    prepend-icon="mdi-refresh"
                    size="small"
                    :loading="yamlLoading"
                    @click="handleLoadYaml"
                  >
                    Reload
                  </v-btn>
                  <v-btn
                    color="primary"
                    prepend-icon="mdi-content-save"
                    size="small"
                    :loading="yamlSaving"
                    :disabled="!yamlHasChanges"
                    @click="handleSaveYaml"
                  >
                    Save YAML
                  </v-btn>
                </div>
              </v-card-title>
              <v-card-text>
                <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                  <div class="text-caption">
                    <strong>Direct YAML editing:</strong> Edit the complete project YAML file. Changes are saved to
                    the file immediately. A backup is created automatically before saving.
                  </div>
                </v-alert>

                <v-alert v-if="yamlError" type="error" variant="tonal" density="compact" class="mb-4" closable @click:close="yamlError = null">
                  {{ yamlError }}
                </v-alert>

                <yaml-editor
                  v-if="rawYamlContent !== null"
                  v-model="rawYamlContent"
                  height="600px"
                  :readonly="false"
                  :validate-on-change="true"
                  @change="handleYamlChange"
                />

                <div v-else class="text-center py-12">
                  <v-progress-circular indeterminate color="primary" />
                  <p class="mt-4 text-grey">Loading YAML content...</p>
                </div>
              </v-card-text>
            </v-card>
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

    <!-- Execute Dialog -->
    <execute-dialog
      v-model="showExecuteDialog"
      :project-name="projectName"
      @executed="handleExecuted"
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
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { api } from '@/api'
import { useProjects, useEntities, useValidation, useDependencies, useCytoscape } from '@/composables'
import { useDataValidation } from '@/composables/useDataValidation'
import { useSession } from '@/composables/useSession'
import { getNodeInfo } from '@/utils/graphAdapter'
import EntityListCard from '@/components/entities/EntityListCard.vue'
import ValidationPanel from '@/components/validation/ValidationPanel.vue'
import PreviewFixesModal from '@/components/validation/PreviewFixesModal.vue'
import ProjectDataSources from '@/components/ProjectDataSources.vue'
import SessionIndicator from '@/components/SessionIndicator.vue'
import CircularDependencyAlert from '@/components/dependencies/CircularDependencyAlert.vue'
import NodeLegend from '@/components/dependencies/NodeLegend.vue'
import ReconciliationView from '@/components/reconciliation/ReconciliationView.vue'
import MetadataEditor from '@/components/MetadataEditor.vue'
import YamlEditor from '@/components/common/YamlEditor.vue'
import ExecuteDialog from '@/components/execute/ExecuteDialog.vue'

const route = useRoute()
const router = useRouter()
const theme = useTheme()
const projectName = computed(() => route.params.name as string)

// Composables
const {
  selectedProject,
  loading: projectLoading,
  error: projectError,
  hasUnsavedChanges,
  backups,
  select,
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

// Dependencies management
const {
  dependencyGraph,
  loading: dependenciesLoading,
  error: dependenciesError,
  hasCircularDependencies,
  cycles,
  statistics: depStatistics,
  fetch: fetchDependencies,
  isInCycle,
  clearError: clearDependenciesError,
} = useDependencies({
  projectName: projectName.value,
  autoFetch: true,
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
const showExecuteDialog = ref(false)
const showSuccessSnackbar = ref(false)
const successMessage = ref('')
const showPreviewModal = ref(false)
const fixPreview = ref<any>(null)
const fixPreviewLoading = ref(false)
const fixPreviewError = ref<string | null>(null)
const entityToEdit = ref<string | null>(null)

// Graph state
const graphContainer = ref<HTMLElement | null>(null)
const layoutType = ref<'hierarchical' | 'force'>('hierarchical')
const showNodeLabels = ref(true)
const showEdgeLabels = ref(true)
const highlightCycles = ref(true)
const showSourceNodes = ref(false)
const showLegend = ref(false)
const showDetailsDrawer = ref(false)
const selectedNode = ref<string | null>(null)

// YAML editing state
const rawYamlContent = ref<string | null>(null)
const originalYamlContent = ref<string | null>(null)
const yamlLoading = ref(false)
const yamlSaving = ref(false)
const yamlError = ref<string | null>(null)
const yamlHasChanges = ref(false)

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

const isDark = computed(() => theme.global.current.value.dark)

const selectedNodeInfo = computed(() => {
  if (!selectedNode.value) return null
  return getNodeInfo(selectedNode.value, dependencyGraph.value)
})

// Cytoscape integration
const { fit, zoomIn, zoomOut, reset, exportPNG } = useCytoscape({
  container: graphContainer,
  graphData: dependencyGraph,
  layoutType,
  showNodeLabels,
  showEdgeLabels,
  highlightCycles,
  showSourceNodes,
  cycles,
  isDark,
  onNodeClick: (nodeId: string) => {
    selectedNode.value = nodeId
    showDetailsDrawer.value = true
  },
  onBackgroundClick: () => {
    selectedNode.value = null
    showDetailsDrawer.value = false
  },
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

function handleExecuted(result: any) {
  successMessage.value = `Workflow executed successfully: ${result.message}`
  showSuccessSnackbar.value = true
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
  // Switch to entities tab and trigger entity editor
  activeTab.value = 'entities'
  showDetailsDrawer.value = false
  entityToEdit.value = entityName
}

async function handleRefreshDependencies() {
  clearDependenciesError()
  if (projectName.value) {
    await fetchDependencies(projectName.value)
  }
}

function handleFit() {
  fit()
}

function handleZoomIn() {
  zoomIn()
}

function handleZoomOut() {
  zoomOut()
}

function handleResetView() {
  reset()
}

function handleExportPNG() {
  const png = exportPNG()
  if (png) {
    const link = document.createElement('a')
    link.download = `dependency-graph-${projectName.value}.png`
    link.href = png
    link.click()
  }
}

async function handleLoadYaml() {
  if (!projectName.value) return

  yamlLoading.value = true
  yamlError.value = null
  try {
    const response = await api.projects.getRawYaml(projectName.value)
    rawYamlContent.value = response.yaml_content
    originalYamlContent.value = response.yaml_content
    yamlHasChanges.value = false
  } catch (err) {
    yamlError.value = err instanceof Error ? err.message : 'Failed to load YAML content'
    console.error('Failed to load raw YAML:', err)
  } finally {
    yamlLoading.value = false
  }
}

function handleYamlChange(content: string) {
  yamlHasChanges.value = content !== originalYamlContent.value
}

async function handleSaveYaml() {
  if (!projectName.value || !rawYamlContent.value) return

  yamlSaving.value = true
  yamlError.value = null
  try {
    await api.projects.updateRawYaml(projectName.value, rawYamlContent.value)
    originalYamlContent.value = rawYamlContent.value
    yamlHasChanges.value = false
    
    // Refresh project to update selected project
    await handleRefresh()
    
    successMessage.value = 'YAML saved successfully'
    showSuccessSnackbar.value = true
    
    // Optionally re-validate
    await handleValidate()
  } catch (err) {
    yamlError.value = err instanceof Error ? err.message : 'Failed to save YAML'
    console.error('Failed to save raw YAML:', err)
  } finally {
    yamlSaving.value = false
  }
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

// Watch for tab changes to load YAML when YAML tab is activated
watch(activeTab, async (newTab) => {
  if (newTab === 'yaml' && rawYamlContent.value === null) {
    await handleLoadYaml()
  }
})

// Watch for entity query parameter (from dependency graph deep links)
watch(
  () => route.query.entity,
  (entityName) => {
    if (entityName && typeof entityName === 'string') {
      activeTab.value = 'entities'
      entityToEdit.value = entityName
      // Clear query param after triggering
      router.replace({ query: { ...route.query, entity: undefined } })
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.gap-2 {
  gap: 0.5rem;
}

.gap-4 {
  gap: 1rem;
}

.graph-container {
  width: 100%;
  height: 600px;
  min-height: 600px;
  position: relative;
  background: transparent;
}
</style>
