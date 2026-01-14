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
              <v-tooltip activator="parent">Preview transformation results for selected entities</v-tooltip>
            </v-btn>
            <v-btn
              variant="outlined"
              prepend-icon="mdi-check-circle-outline"
              :loading="validationLoading"
              @click="handleValidate"
            >
              Validate
              <v-tooltip activator="parent">Run validation checks on the entire project</v-tooltip>
            </v-btn>
            <v-btn variant="outlined" prepend-icon="mdi-play-circle" color="success" @click="showExecuteDialog = true">
              Execute
              <v-tooltip activator="parent">Execute the full workflow and export data</v-tooltip>
            </v-btn>
            <v-btn variant="outlined" prepend-icon="mdi-history" @click="showBackupsDialog = true">
              Backups
              <v-tooltip activator="parent">View and restore previous versions of this project</v-tooltip>
            </v-btn>
            <v-btn color="primary" prepend-icon="mdi-content-save" :disabled="!hasUnsavedChanges" @click="handleSave">
              Save Changes
              <v-tooltip activator="parent">Save changes to the project configuration</v-tooltip>
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
            Graph
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
          <v-tab value="dispatch">
            <v-icon icon="mdi-send" class="mr-2" />
            Dispatch
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
                  <v-btn 
                    size="x-small"
                    value="hierarchical" 
                    :color="layoutType === 'hierarchical' ? 'primary' : undefined"
                    prepend-icon="mdi-file-tree"
                  > Hierarchical </v-btn>
                  <v-btn 
                    size="small"
                    value="force"
                    :color="layoutType === 'force' ? 'primary' : undefined"
                    prepend-icon="mdi-vector-arrange-above"
                  >
                  Force
                </v-btn>
                  <v-btn 
                    size="small"
                    value="custom"
                    :color="layoutType === 'custom' ? 'primary' : undefined"
                    :disabled="!hasCustomLayout"
                    prepend-icon="mdi-cursor-move"
                  >
                    Custom
                    <v-tooltip v-if="!hasCustomLayout" activator="parent">
                      No custom layout saved yet. Save current layout to enable.
                    </v-tooltip>
                  </v-btn>
                </v-btn-toggle>

                <v-divider vertical />

                <!-- Save layout button -->
                <v-btn
                  size="small"
                  variant="tonal"
                  prepend-icon="mdi-content-save"
                  :loading="savingLayout"
                  @click="handleSaveCustomLayout"
                >
                  Save as Custom
                  <v-tooltip activator="parent">
                    Save the current node positions as a custom layout
                  </v-tooltip>
                </v-btn>

                <!-- Clear layout button (only show if custom layout exists) -->
                <v-btn
                  v-if="hasCustomLayout"
                  size="small"
                  variant="text"
                  prepend-icon="mdi-delete"
                  color="error"
                  @click="handleClearCustomLayout"
                >
                  Clear Custom
                  <v-tooltip activator="parent">
                    Remove the saved custom layout
                  </v-tooltip>
                </v-btn>

                <v-divider vertical />

                <v-btn
                  size="small"
                  variant="tonal"
                  :color="showNodeLabels ? 'primary' : undefined"
                  @click="showNodeLabels = !showNodeLabels"
                  class="text-capitalize"
                >
                  Node Labels
                </v-btn>
                <v-btn
                  size="small"
                  variant="tonal"
                  :color="showEdgeLabels ? 'primary' : undefined"
                  @click="showEdgeLabels = !showEdgeLabels"
                  class="text-capitalize"
                >
                  Edge Labels
                </v-btn>

                <!-- <v-btn
                  size="small"
                  :variant="highlightCycles ? 'tonal' : 'tonal'"
                  :color="highlightCycles ? 'primary' : undefined"
                  @click="highlightCycles = !highlightCycles"
                  class="text-capitalize"
                >
                  Cycles
                </v-btn> -->

                <v-btn
                  size="small"
                  variant="tonal"
                  :color="showSourceNodes ? 'primary' : undefined"
                  @click="showSourceNodes = !showSourceNodes"
                  class="text-capitalize"
                >
                  Source Nodes
                </v-btn>
                <v-spacer />

                <v-btn
                  size="small"
                  variant="outlined"
                  prepend-icon="mdi-information-outline"
                  :color="showLegend ? 'primary' : undefined"
                  @click="showLegend = !showLegend"
                >
                  Legend
                </v-btn>

                <v-chip prepend-icon="mdi-cube-outline"> {{ depStatistics.nodeCount }} nodes </v-chip>
                <v-chip prepend-icon="mdi-arrow-right"> {{ depStatistics.edgeCount }} edges </v-chip>
              </v-card-text>
            </v-card>

            <!-- Loading State (only on initial load, not during refresh) -->
            <v-card v-if="dependenciesLoading && !dependencyGraph" variant="outlined" class="text-center py-12">
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
            <v-card v-else variant="outlined" class="graph-card">
              <v-card-text class="pa-0 graph-card-content">
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

            <!-- Legend Dialog -->
            <v-dialog v-model="showLegend" max-width="500">
              <node-legend :show-source-nodes="showSourceNodes" @close="showLegend = false" />
            </v-dialog>
            
            <!-- Context Menu -->
            <graph-node-context-menu
              v-model="showContextMenu"
              :x="contextMenuX"
              :y="contextMenuY"
              :entity-name="contextMenuEntity"
              @preview="handleContextMenuPreview"
              @duplicate="handleContextMenuDuplicate"
              @delete="handleContextMenuDelete"
            />

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

          <!-- Dispatch Tab -->
          <v-window-item value="dispatch">
            <v-card variant="outlined">
              <v-card-title class="d-flex align-center">
                <v-icon icon="mdi-send" class="mr-2" />
                Dispatch Data to Target System
              </v-card-title>
              <v-card-text>
                <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                  <div class="text-caption">
                    <strong>Dispatch:</strong> Send processed Shape Shifter data to the configured target database.
                    Configuration is loaded from the project's <code>options.ingesters</code> section.
                  </div>
                </v-alert>

                <ingester-form />
              </v-card-text>
            </v-card>
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

    <!-- Entity Editor Overlay (for graph double-click) -->
    <entity-form-dialog
      v-if="entityStore.overlayEntityName"
      v-model="entityStore.showEditorOverlay"
      :project-name="projectName"
      :entity="entityStore.entities.find((e) => e.name === entityStore.overlayEntityName) || null"
      mode="edit"
      @saved="handleOverlayEntitySaved"
      @update:modelValue="handleOverlayClose"
    />

    <!-- Success Snackbar with Animation -->
    <v-scale-transition>
      <template #default>
        <v-snackbar v-if="showSuccessSnackbar" v-model="showSuccessSnackbar" color="success" timeout="3000">
          {{ successMessage }}
          <template #actions>
            <v-btn variant="text" @click="showSuccessSnackbar = false"> Close </v-btn>
          </template>
        </v-snackbar>
      </template>
    </v-scale-transition>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { api } from '@/api'
import { useProjects, useEntities, useValidation, useDependencies, useCytoscape } from '@/composables'
import { useDataValidation } from '@/composables/useDataValidation'
import { useSession } from '@/composables/useSession'
import { useEntityStore } from '@/stores/entity'
import { getNodeInfo } from '@/utils/graphAdapter'
import type { CustomGraphLayout } from '@/types'
import EntityListCard from '@/components/entities/EntityListCard.vue'
import EntityFormDialog from '@/components/entities/EntityFormDialog.vue'
import ValidationPanel from '@/components/validation/ValidationPanel.vue'
import PreviewFixesModal from '@/components/validation/PreviewFixesModal.vue'
import ProjectDataSources from '@/components/ProjectDataSources.vue'
import SessionIndicator from '@/components/SessionIndicator.vue'
import CircularDependencyAlert from '@/components/dependencies/CircularDependencyAlert.vue'
import NodeLegend from '@/components/dependencies/NodeLegend.vue'
import GraphNodeContextMenu from '@/components/dependencies/GraphNodeContextMenu.vue'
import ReconciliationView from '@/components/reconciliation/ReconciliationView.vue'
import MetadataEditor from '@/components/MetadataEditor.vue'
import YamlEditor from '@/components/common/YamlEditor.vue'
import ExecuteDialog from '@/components/execute/ExecuteDialog.vue'
import IngesterForm from '@/components/ingester/IngesterForm.vue'

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
const layoutType = ref<'hierarchical' | 'force' | 'custom'>('force')
const customLayout = ref<CustomGraphLayout | null>(null)
const hasCustomLayout = ref(false)
const savingLayout = ref(false)
const showNodeLabels = ref(true)
const showEdgeLabels = ref(true)
const highlightCycles = ref(true)
const showSourceNodes = ref(false)
const showLegend = ref(false)
const showDetailsDrawer = ref(false)
const selectedNode = ref<string | null>(null)

// Context menu state
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuEntity = ref<string | null>(null)

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
const entityStore = useEntityStore()

const { cy, fit, zoomIn, zoomOut, reset, render: renderGraph, exportPNG, getCurrentPositions } = useCytoscape({
  container: graphContainer,
  graphData: dependencyGraph,
  layoutType,
  customPositions: customLayout,
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
  onNodeDoubleClick: (nodeId: string) => {
    // Open entity editor overlay on double-click
    console.debug('[ProjectDetailView] Opening overlay for entity:', nodeId)
    entityStore.openEditorOverlay(nodeId)
  },
  onNodeRightClick: (nodeId: string, x: number, y: number) => {
    // Open context menu on right-click
    console.debug('[ProjectDetailView] Context menu for entity:', nodeId, 'at', x, y)
    console.debug('[ProjectDetailView] Setting context menu state...')
    contextMenuEntity.value = nodeId
    contextMenuX.value = x
    contextMenuY.value = y
    showContextMenu.value = true
    console.debug('[ProjectDetailView] Context menu state:', {
      entity: contextMenuEntity.value,
      x: contextMenuX.value,
      y: contextMenuY.value,
      show: showContextMenu.value
    })
  },
  onBackgroundClick: () => {
    selectedNode.value = null
    showDetailsDrawer.value = false
  },
})

// Load custom layout when project loads
watch(
  () => projectName.value,
  async (name) => {
    if (!name) return

    try {
      const { layout, has_custom_layout } = await api.projects.getLayout(name)
      customLayout.value = layout
      hasCustomLayout.value = has_custom_layout

      // Auto-switch to custom layout if it exists and has positions
      if (has_custom_layout && Object.keys(layout).length > 0) {
        layoutType.value = 'custom'
      }
    } catch (error) {
      console.warn('Failed to load custom layout:', error)
      // Not a critical error, just continue without custom layout
    }
  },
  { immediate: true }
)

// Save current layout as custom
async function handleSaveCustomLayout() {
  if (!projectName.value || !getCurrentPositions) return

  savingLayout.value = true
  try {
    const positions = getCurrentPositions()
    await api.projects.saveLayout(projectName.value, positions)
    customLayout.value = positions
    hasCustomLayout.value = true
    layoutType.value = 'custom'

    successMessage.value = `Custom layout saved with ${Object.keys(positions).length} entity positions`
    showSuccessSnackbar.value = true
  } catch (error) {
    console.error('Failed to save custom layout:', error)
  } finally {
    savingLayout.value = false
  }
}

// Clear custom layout
async function handleClearCustomLayout() {
  if (!projectName.value) return

  try {
    await api.projects.clearLayout(projectName.value)
    customLayout.value = null
    hasCustomLayout.value = false

    // Switch back to default layout
    if (layoutType.value === 'custom') {
      layoutType.value = 'force'
    }

    successMessage.value = 'Custom layout cleared'
    showSuccessSnackbar.value = true
  } catch (error) {
    console.error('Failed to clear custom layout:', error)
  }
}

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

async function handleOverlayEntitySaved() {
  // Refresh entities and dependencies after saving from overlay
  markAsChanged()
  successMessage.value = 'Entity saved successfully'
  showSuccessSnackbar.value = true
  
  // Refresh the dependency graph if we're on the dependencies tab
  if (activeTab.value === 'dependencies' && projectName.value) {
    await fetchDependencies(projectName.value)
  }
}

function handleOverlayClose(isOpen: boolean) {
  if (!isOpen) {
    entityStore.closeEditorOverlay()
  }
}

// Context menu handlers
async function handleContextMenuPreview(entityName: string) {
  console.debug('[ProjectDetailView] Preview entity:', entityName)
  // Navigate to test run with this entity selected
  window.location.href = `/test-run/${projectName.value}?entity=${entityName}`
}

async function handleContextMenuDuplicate(entityName: string) {
  console.log('=========================================')
  console.log('[ProjectDetailView] handleContextMenuDuplicate CALLED')
  console.log('Entity name:', entityName)
  console.log('=========================================')
  console.log('[1] Starting duplicate process')
  
  console.log('[2] Looking for source entity:', entityName)
  const sourceEntity = entityStore.entities.find((e) => e.name === entityName)
  console.log('[3] Source entity found:', sourceEntity ? 'YES' : 'NO')
  if (!sourceEntity) {
    console.error('Source entity not found:', entityName)
    return
  }
  
  console.log('[4] Generating new entity name')
  // Create a new entity name
  let newName = `${entityName}_copy`
  let counter = 1
  while (entityStore.entities.find((e) => e.name === newName)) {
    newName = `${entityName}_copy${counter++}`
  }
  console.log('[5] New entity name:', newName)
  
  try {
    console.log('[6] About to create entity...')
    // Create duplicate entity with copied data
    await entityStore.createEntity(projectName.value, {
      name: newName,
      entity_data: {
        ...sourceEntity.entity_data,
        // Clear any reconciliation specs that might reference the old name
        reconciliation: undefined,
      },
    })
    console.log('[7] Entity created successfully')
    
    console.log('[8] About to fetch dependencies...')
    // Refresh dependencies to update the graph (silently, without showing loading state)
    await fetchDependencies(projectName.value)
    console.log('[9] Dependencies fetched, graph data:', dependencyGraph.value)
    
    console.log('[10] Setting success message first...')
    successMessage.value = `Entity "${newName}" created from "${entityName}"`
    showSuccessSnackbar.value = true
    markAsChanged()
    
    console.log('[11] Waiting for Vue updates to settle...')
    await nextTick()
    
    console.log('[12] About to render graph...')
    renderGraph()
    console.log('[13] Graph rendered')
    console.log('[14] Duplicate complete!')
    
    // Diagnostic: Check if container/graph still exists after a short delay
    setTimeout(() => {
      console.log('[DIAGNOSTIC] Post-duplicate state:', {
        hasContainer: !!graphContainer.value,
        containerInDOM: graphContainer.value ? document.contains(graphContainer.value) : false,
        dependencyGraphExists: !!dependencyGraph.value,
        nodesCount: dependencyGraph.value?.nodes?.length ?? 0,
      })
      
      // Additional Cytoscape diagnostics
      if (graphContainer.value) {
        const rect = graphContainer.value.getBoundingClientRect()
        console.log('[DIAGNOSTIC] Container dimensions:', {
          width: rect.width,
          height: rect.height,
          visible: rect.width > 0 && rect.height > 0,
        })
        
        // Check for canvas element
        const canvas = graphContainer.value.querySelector('canvas')
        if (canvas) {
          const canvasRect = canvas.getBoundingClientRect()
          console.log('[DIAGNOSTIC] Canvas found:', {
            width: canvasRect.width,
            height: canvasRect.height,
            visible: canvasRect.width > 0 && canvasRect.height > 0,
          })
        } else {
          console.warn('[DIAGNOSTIC] No canvas element found in container!')
        }
      }
    }, 500)
  } catch (err) {
    console.error('[ERROR] Failed to duplicate entity:', err)
    successMessage.value = err instanceof Error ? err.message : 'Failed to duplicate entity'
    showSuccessSnackbar.value = true
  }
}

async function handleContextMenuDelete(entityName: string) {
  console.log('=========================================')
  console.log('[ProjectDetailView] handleContextMenuDelete CALLED')
  console.log('Entity name:', entityName)
  console.log('=========================================')
  const confirmed = confirm(`Are you sure you want to delete entity "${entityName}"?`)
  if (!confirmed) return
  
  try {
    console.debug('[ProjectDetailView] Deleting entity:', entityName)
    await entityStore.deleteEntity(projectName.value, entityName)
    
    console.log('[ProjectDetailView] Entity deleted, refreshing dependencies...')
    // Refresh dependencies to update the graph (silently, without showing loading state)
    await fetchDependencies(projectName.value)
    console.log('[ProjectDetailView] Dependencies refreshed, graph data:', dependencyGraph.value)
    
    console.log('[ProjectDetailView] Setting success message first...')
    successMessage.value = `Entity "${entityName}" deleted`
    showSuccessSnackbar.value = true
    markAsChanged()
    
    console.log('[ProjectDetailView] Waiting for Vue updates to settle...')
    await nextTick()
    
    // Force graph re-render after Vue's DOM updates settle
    console.log('[ProjectDetailView] Forcing graph re-render...')
    renderGraph()
    console.log('[ProjectDetailView] Graph rendered')
    console.log('[ProjectDetailView] Delete complete!')
    
    // Diagnostic: Check if container/graph still exists after a short delay
    setTimeout(() => {
      console.log('[DIAGNOSTIC] Post-delete state:', {
        hasContainer: !!graphContainer.value,
        containerInDOM: graphContainer.value ? document.contains(graphContainer.value) : false,
        dependencyGraphExists: !!dependencyGraph.value,
        nodesCount: dependencyGraph.value?.nodes?.length ?? 0,
      })
      
      // Additional Cytoscape diagnostics
      if (graphContainer.value) {
        const rect = graphContainer.value.getBoundingClientRect()
        console.log('[DIAGNOSTIC] Container dimensions:', {
          width: rect.width,
          height: rect.height,
          visible: rect.width > 0 && rect.height > 0,
        })
        
        // Check for canvas element
        const canvas = graphContainer.value.querySelector('canvas')
        if (canvas) {
          const canvasRect = canvas.getBoundingClientRect()
          console.log('[DIAGNOSTIC] Canvas found:', {
            width: canvasRect.width,
            height: canvasRect.height,
            visible: canvasRect.width > 0 && canvasRect.height > 0,
          })
        } else {
          console.warn('[DIAGNOSTIC] No canvas element found in container!')
        }
      }
    }, 500)
  } catch (err) {
    console.error('Failed to delete entity:', err)
    successMessage.value = err instanceof Error ? err.message : 'Failed to delete entity'
    showSuccessSnackbar.value = true
  }
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
  // Ensure we have a project name from route params
  if (!projectName.value) {
    console.warn('ProjectDetailView: No project name in route params')
    await router.push({ name: 'projects' })
    return
  }

  try {
    console.debug(`ProjectDetailView: Initializing for project "${projectName.value}"`)
    
    // Always load the project on mount to ensure fresh data
    console.debug(`ProjectDetailView: Loading project "${projectName.value}"`)
    await select(projectName.value)
    
    await fetchBackups(projectName.value)
    // Start editing session
    await startSession(projectName.value)
    
    console.debug(`ProjectDetailView: Successfully initialized for project "${projectName.value}"`)
  } catch (err) {
    console.error('ProjectDetailView: Failed to initialize project view:', err)
    // Only navigate back if we're still on this route (avoid navigation loops)
    if (router.currentRoute.value.name === 'project-detail') {
      await router.push({ name: 'projects' })
    }
  }
})

// Watch for project name changes
watch(
  () => projectName.value,
  async (newName, oldName) => {
    
    if (!newName) return
    
    // Avoid re-loading on initial mount (onMounted handles that)
    if (!oldName) return
    
    console.debug(`ProjectDetailView: Project changed from "${oldName}" to "${newName}"`)
    
    try {
      // Always load the project to ensure fresh data
      console.debug(`ProjectDetailView: Loading new project "${newName}"`)
      await select(newName)
      await fetchBackups(newName)
    } catch (err) {
      console.error(`ProjectDetailView: Failed to load project "${newName}":`, err)
      // Only navigate back if we're still on this route
      if (router.currentRoute.value.name === 'project-detail') {
        await router.push({ name: 'projects' })
      }
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

.graph-card {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 420px);
  min-height: 500px;
}

.graph-card-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.graph-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: transparent;
}
</style>
