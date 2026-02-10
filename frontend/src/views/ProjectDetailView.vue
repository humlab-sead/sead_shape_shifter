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
            <v-btn variant="outlined" prepend-icon="mdi-play-circle" color="success" @click="showExecuteDialog = true">
              Execute
              <v-tooltip activator="parent">Execute the full workflow and export data</v-tooltip>
            </v-btn>
            <v-btn variant="outlined" prepend-icon="mdi-history" color="success" @click="showBackupsDialog = true">
              Backups
              <v-tooltip activator="parent">View and restore previous versions of this project</v-tooltip>
            </v-btn>
            <v-btn variant="outlined" prepend-icon="mdi-refresh" @click="handleRefresh">
              Refresh
              <v-tooltip activator="parent">Reload project from disk (force refresh cache)</v-tooltip>
            </v-btn>
            <v-btn variant="outlined" color="success" prepend-icon="mdi-content-save" :disabled="!hasUnsavedChanges" @click="handleSave">
              Save Changes
              <v-tooltip activator="parent">Save changes to the project configuration</v-tooltip>
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Session Indicator -->
    <session-indicator v-if="projectName" :project-name="projectName" class="mb-4" />

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
            Reconcile
          </v-tab>
          <v-tab value="validation">
            <v-icon icon="mdi-check-circle-outline" class="mr-2" />
            Validate
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
          <v-tab value="data-sources">
            <v-icon icon="mdi-database-outline" class="mr-2" />
            Data Sources
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
                <!-- Task Filter Dropdown -->
                <task-filter-dropdown
                  v-model="currentTaskFilter"
                  :task-status="taskStatusStore.taskStatus"
                  @initialize="handleInitializeTaskList"
                />

                <v-divider vertical />

                <!-- Graph Layout Dropdown -->
                <graph-layout-dropdown
                  v-model:layout-type="layoutType"
                  :has-custom-layout="hasCustomLayout"
                  :saving="savingLayout"
                  @save-custom="handleSaveCustomLayout"
                  @clear-custom="handleClearCustomLayout"
                />

                <v-divider vertical />

                <!-- Graph Display Options -->
                <graph-display-options-dropdown
                  :options="displayOptions"
                  @update:options="updateDisplayOptions"
                />

                <v-spacer />
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
                
                <!-- Stats Overlay (top-left) -->
                <div class="graph-stats-overlay">
                  <v-card variant="flat" class="stats-card">
                    <v-card-text class="pa-2">
                      <!-- Task Completion -->
                      <div v-if="taskStatusStore.taskStatus" class="mb-2">
                        <v-row no-gutters align="center" class="mb-1">
                          <v-col cols="auto" class="mr-2">
                            <v-icon 
                              :icon="completionIcon" 
                              :color="completionColor"
                              size="small"
                            />
                          </v-col>
                          <v-col>
                            <div class="text-caption">
                              <span class="font-weight-medium">{{ taskStats.completed }}</span>
                              <span class="text-medium-emphasis"> of </span>
                              <span class="font-weight-medium">{{ taskStats.total }}</span>
                              <span class="text-medium-emphasis"> complete</span>
                            </div>
                          </v-col>
                          <v-col cols="auto" class="ml-2">
                            <v-chip
                              :color="completionColor"
                              size="x-small"
                              variant="flat"
                            >
                              {{ Math.round(taskStats.completion_percentage) }}%
                            </v-chip>
                          </v-col>
                        </v-row>
                        <v-progress-linear
                          :model-value="taskStats.completion_percentage"
                          :color="completionColor"
                          height="3"
                          rounded
                        />
                      </div>
                      
                      <!-- Node/Edge Counts -->
                      <div class="d-flex gap-1 mb-2">
                        <v-chip size="x-small" variant="flat" color="primary">
                          <v-icon icon="mdi-cube-outline" size="x-small" class="mr-1" />
                          {{ depStatistics.nodeCount }}
                        </v-chip>
                        <v-chip size="x-small" variant="flat" color="secondary">
                          <v-icon icon="mdi-arrow-right" size="x-small" class="mr-1" />
                          {{ depStatistics.edgeCount }}
                        </v-chip>
                      </div>
                      
                      <!-- Visual Indicators Legend -->
                      <div class="text-caption text-medium-emphasis">
                        <div class="d-flex align-center gap-1 mb-1">
                          <div style="width: 12px; height: 12px; border: 2px double #4CAF50; border-radius: 50%;" />
                          <span style="font-size: 10px;">Materialized</span>
                        </div>
                      </div>
                    </v-card-text>
                  </v-card>
                </div>
                
                <!-- Floating Action Buttons -->
                <div class="graph-fab-container">
                  <v-btn 
                    icon
                    size="small"
                    class="graph-fab"
                    @click="handleFit"
                  >
                    <v-icon>mdi-fit-to-screen</v-icon>
                    <v-tooltip activator="parent" location="left">Fit to Screen</v-tooltip>
                  </v-btn>
                  
                  <v-btn 
                    icon
                    size="small"
                    class="graph-fab"
                    @click="handleZoomIn"
                  >
                    <v-icon>mdi-magnify-plus</v-icon>
                    <v-tooltip activator="parent" location="left">Zoom In</v-tooltip>
                  </v-btn>
                  
                  <v-btn 
                    icon
                    size="small"
                    class="graph-fab"
                    @click="handleZoomOut"
                  >
                    <v-icon>mdi-magnify-minus</v-icon>
                    <v-tooltip activator="parent" location="left">Zoom Out</v-tooltip>
                  </v-btn>
                  
                  <v-btn 
                    icon
                    size="small"
                    class="graph-fab"
                    @click="handleResetView"
                  >
                    <v-icon>mdi-refresh</v-icon>
                    <v-tooltip activator="parent" location="left">Reset View</v-tooltip>
                  </v-btn>
                  
                  <v-divider class="my-1" />
                  
                  <v-btn 
                    icon
                    size="small"
                    class="graph-fab"
                    color="primary"
                    @click="handleCreateNewNode"
                  >
                    <v-icon>mdi-plus-circle-outline</v-icon>
                    <v-tooltip activator="parent" location="left">Create New Node</v-tooltip>
                  </v-btn>
                  
                  <v-divider class="my-1" />
                  
                  <v-btn 
                    icon
                    size="small"
                    class="graph-fab"
                    @click="handleExportPNG"
                  >
                    <v-icon>mdi-download</v-icon>
                    <v-tooltip activator="parent" location="left">Export PNG</v-tooltip>
                  </v-btn>
                </div>
              </v-card-text>
            </v-card>
            
            <!-- Context Menu -->
            <graph-node-context-menu
              v-model="showContextMenu"
              :x="contextMenuX"
              :y="contextMenuY"
              :entity-name="contextMenuEntity"
              :task-status="taskStatusStore.getEntityStatus(contextMenuEntity || '')"
              @edit="handleContextMenuEdit"
              @preview="handleContextMenuPreview"
              @duplicate="handleContextMenuDuplicate"
              @delete="handleContextMenuDelete"
              @mark-complete="handleMarkComplete"
              @mark-ignored="handleMarkIgnored"
              @reset-status="handleResetStatus"
            />

            <!-- Entity Details Drawer -->
            <v-navigation-drawer v-model="showDetailsDrawer" location="right" temporary width="500">
              <template v-if="selectedNode">
                <v-toolbar color="primary" density="compact">
                  <v-toolbar-title class="text-subtitle-1">
                    <v-icon size="small" class="mr-2">mdi-code-braces</v-icon>
                    {{ selectedNode }}
                  </v-toolbar-title>
                  <v-spacer />
                  <v-btn icon="mdi-open-in-new" variant="text" size="small" @click="handleEditEntity(selectedNode)">
                    <v-tooltip activator="parent" location="bottom">Open Full Editor</v-tooltip>
                  </v-btn>
                  <v-btn icon="mdi-close" variant="text" size="small" @click="handleCloseQuickEdit" />
                </v-toolbar>

                <div class="drawer-body">
                  <div class="drawer-alerts">
                    <v-alert v-if="isInCycle(selectedNode)" type="warning" variant="tonal" density="compact" class="ma-2">
                      <v-icon size="small" class="mr-1">mdi-alert</v-icon>
                      Part of circular dependency
                    </v-alert>
                    
                    <v-progress-linear v-if="drawerYamlLoading" indeterminate color="primary" />
                    
                    <v-alert v-if="drawerYamlError" type="error" variant="tonal" density="compact" class="ma-2" closable @click:close="drawerYamlError = null">
                      {{ drawerYamlError }}
                    </v-alert>
                  </div>
                  
                  <div class="drawer-editor">
                    <div v-if="isSelectedNodeDataSource" class="data-source-info pa-4">
                      <v-icon size="48" color="grey-lighten-1" class="mb-3">mdi-database</v-icon>
                      <div class="text-subtitle-2 mb-2">Data Source Node</div>
                      <div class="text-caption text-medium-emphasis">
                        Data sources cannot be edited from the graph view.
                        Configure data sources in the Data Sources tab.
                      </div>
                    </div>
                    <yaml-editor
                      v-else-if="drawerYamlContent !== null"
                      v-model="drawerYamlContent"
                      height="calc(100vh - 200px)"
                      @change="handleDrawerYamlChange"
                    />
                  </div>
                </div>

                <div v-if="!isSelectedNodeDataSource" class="drawer-footer">
                  <v-divider />
                  <v-card-actions class="pa-3">
                    <v-btn 
                      variant="text" 
                      @click="handleCloseQuickEdit"
                      :disabled="drawerYamlSaving"
                    >
                      Cancel
                    </v-btn>
                    <v-spacer />
                    <v-btn 
                      color="primary" 
                      variant="flat"
                      prepend-icon="mdi-content-save"
                      :loading="drawerYamlSaving"
                      :disabled="!drawerYamlHasChanges || drawerYamlLoading"
                      @click="handleSaveQuickEdit"
                    >
                      Save
                    </v-btn>
                  </v-card-actions>
                </div>
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
                <!-- <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                  <div class="text-caption">
                    <strong>Direct YAML editing:</strong> Edit the complete project YAML file. Changes are saved to
                    the file immediately. A backup is created automatically before saving.
                  </div>
                </v-alert> -->

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
      :entity="
        entityStore.entities.find((e) => e.name === entityStore.overlayEntityName) || {
          name: entityStore.overlayEntityName,
          entity_data: {},
        }
      "
      :initial-tab="entityStore.overlayInitialTab"
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
import { useProjectStore } from '@/stores'
import { useTaskStatusStore } from '@/stores/taskStatus'
import type { CustomGraphLayout } from '@/types'
import type { TaskFilter } from '@/components/dependencies/TaskFilterDropdown.vue'
import EntityListCard from '@/components/entities/EntityListCard.vue'
import EntityFormDialog from '@/components/entities/EntityFormDialog.vue'
import ValidationPanel from '@/components/validation/ValidationPanel.vue'
import PreviewFixesModal from '@/components/validation/PreviewFixesModal.vue'
import ProjectDataSources from '@/components/ProjectDataSources.vue'
import SessionIndicator from '@/components/SessionIndicator.vue'
import CircularDependencyAlert from '@/components/dependencies/CircularDependencyAlert.vue'
import GraphNodeContextMenu from '@/components/dependencies/GraphNodeContextMenu.vue'
import TaskFilterDropdown from '@/components/dependencies/TaskFilterDropdown.vue'
import GraphDisplayOptionsDropdown from '@/components/dependencies/GraphDisplayOptionsDropdown.vue'
import type { GraphDisplayOptions } from '@/components/dependencies/GraphDisplayOptionsDropdown.vue'
import GraphLayoutDropdown from '@/components/dependencies/GraphLayoutDropdown.vue'
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
const displayOptions = ref<GraphDisplayOptions>({
  nodeLabels: true,
  edgeLabels: true,
  sourceNodes: false,
})
const highlightCycles = ref(true)
const showDetailsDrawer = ref(false)
const selectedNode = ref<string | null>(null)

// Quick YAML editor state (drawer)
const drawerYamlContent = ref<string | null>(null)
const drawerOriginalYamlContent = ref<string | null>(null)
const drawerYamlLoading = ref(false)
const drawerYamlSaving = ref(false)
const drawerYamlError = ref<string | null>(null)
const drawerYamlHasChanges = ref(false)

// Context menu state
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuEntity = ref<string | null>(null)

// Task status state
const currentTaskFilter = ref<TaskFilter>('all')

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

const isSelectedNodeDataSource = computed(() => {
  if (!selectedNode.value || !dependencyGraph.value) return false
  const sourceNodes = dependencyGraph.value.source_nodes || []
  return sourceNodes.some((sn: any) => sn.name === selectedNode.value)
})

// Cytoscape integration
const entityStore = useEntityStore()
const projectStore = useProjectStore()
const taskStatusStore = useTaskStatusStore()

// Task completion stats
const taskStats = computed(() => {
  if (!taskStatusStore.taskStatus) {
    return {
      total: 0,
      completed: 0,
      ignored: 0,
      todo: 0,
      completion_percentage: 0
    }
  }
  return taskStatusStore.taskStatus.completion_stats
})

const completionColor = computed(() => {
  const percentage = taskStats.value.completion_percentage
  if (percentage === 100) return 'success'
  if (percentage >= 75) return 'info'
  if (percentage >= 50) return 'warning'
  return 'error'
})

const completionIcon = computed(() => {
  const percentage = taskStats.value.completion_percentage
  if (percentage === 100) return 'mdi-check-circle'
  if (percentage >= 75) return 'mdi-progress-check'
  if (percentage >= 25) return 'mdi-progress-clock'
  return 'mdi-clock-outline'
})

const { cy, fit, zoomIn, zoomOut, reset, render: renderGraph, exportPNG, getCurrentPositions } = useCytoscape({
  container: graphContainer,
  graphData: dependencyGraph,
  layoutType,
  customPositions: customLayout,
  showNodeLabels: computed(() => displayOptions.value.nodeLabels),
  showEdgeLabels: computed(() => displayOptions.value.edgeLabels),
  highlightCycles,
  showSourceNodes: computed(() => displayOptions.value.sourceNodes),
  cycles,
  isDark,
  onNodeClick: async (nodeId: string) => {
    selectedNode.value = nodeId
    await loadEntityYamlForDrawer(nodeId)
    showDetailsDrawer.value = true
  },
  onNodeDoubleClick: (nodeId: string, isCtrlKey: boolean) => {
    // Open entity editor overlay on double-click
    // Ctrl/Cmd+double-click opens YAML tab directly (power user shortcut)
    const initialTab = isCtrlKey ? 'yaml' : 'form'
    console.debug('[ProjectDetailView] Opening overlay for entity:', nodeId, { initialTab })
    entityStore.openEditorOverlay(nodeId, initialTab)
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
// Graph display options handlers
function updateDisplayOptions(options: GraphDisplayOptions) {
  displayOptions.value = options
}

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
async function handleValidate() {
  try {
    await validate(projectName.value)
    // Refresh task status after validation since status depends on validation results
    await taskStatusStore.refresh()
    successMessage.value = 'Project validated successfully'
    showSuccessSnackbar.value = true
  } catch (err) {
    console.error('Validation failed:', err)
  }
}

async function handleDataValidate(config?: any) {
  try {
    const entityNames = config?.entities
    const validationMode = config?.validationMode || 'sample'
    await validateData(projectName.value, entityNames, validationMode)
    // Refresh task status after validation
    await taskStatusStore.refresh()
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
    try {
      await projectStore.refreshProject(projectName.value)
      successMessage.value = 'Project refreshed from disk'
      showSuccessSnackbar.value = true
    } catch (err: any) {
      // Error will be shown from projectStore.error
      console.error('Failed to refresh project:', err)
    }
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
function handleContextMenuEdit(entityName: string) {
  console.debug('[ProjectDetailView] Context menu edit for entity:', entityName)
  entityStore.openEditorOverlay(entityName, 'form')
}

async function handleContextMenuPreview(entityName: string) {
  console.debug('[ProjectDetailView] Preview entity:', entityName)
  // Open entity editor to preview data
  entityStore.openEditorOverlay(entityName, 'form')
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

// Task status handlers
async function handleMarkComplete(entityName: string) {
  try {
    const success = await taskStatusStore.markComplete(entityName)
    if (success) {
      successMessage.value = `Entity "${entityName}" marked as complete`
      showSuccessSnackbar.value = true
      // Refresh graph to show updated badges
      applyTaskStatusToNodes()
    }
  } catch (err) {
    console.error('Failed to mark entity as complete:', err)
    successMessage.value = err instanceof Error ? err.message : 'Failed to mark entity as complete'
    showSuccessSnackbar.value = true
  }
}

async function handleMarkIgnored(entityName: string) {
  try {
    const success = await taskStatusStore.markIgnored(entityName)
    if (success) {
      successMessage.value = `Entity "${entityName}" marked as ignored`
      showSuccessSnackbar.value = true
      // Refresh graph to show updated badges
      applyTaskStatusToNodes()
    }
  } catch (err) {
    console.error('Failed to mark entity as ignored:', err)
    successMessage.value = err instanceof Error ? err.message : 'Failed to mark entity as ignored'
    showSuccessSnackbar.value = true
  }
}

async function handleResetStatus(entityName: string) {
  try {
    const success = await taskStatusStore.resetStatus(entityName)
    if (success) {
      successMessage.value = `Status reset for entity "${entityName}"`
      showSuccessSnackbar.value = true
      // Refresh graph to show updated badges
      applyTaskStatusToNodes()
    }
  } catch (err) {
    console.error('Failed to reset entity status:', err)
    successMessage.value = err instanceof Error ? err.message : 'Failed to reset entity status'
    showSuccessSnackbar.value = true
  }
}

async function handleInitializeTaskList() {
  try {
    const result = await api.tasks.initialize(projectName.value, 'dependency-order')
    
    if (result.success) {
      successMessage.value = result.message || 'Task list initialized successfully'
      showSuccessSnackbar.value = true
      
      // Refresh task status to show updated task list
      await taskStatusStore.refresh()
      
      // Refresh graph to show updated badges
      applyTaskStatusToNodes()
    }
  } catch (err) {
    console.error('Failed to initialize task list:', err)
    successMessage.value = err instanceof Error ? err.message : 'Failed to initialize task list'
    showSuccessSnackbar.value = true
  }
}

// Apply task status styling to graph nodes
function applyTaskStatusToNodes() {
  if (!cy.value || !taskStatusStore.taskStatus) return

  cy.value.nodes().forEach(node => {
    const entityName = node.id()
    const status = taskStatusStore.getEntityStatus(entityName)
    
    if (!status) return

    // Remove existing task classes
    node.removeClass('task-done task-ignored task-blocked task-critical task-ready')

    // Apply status-based classes
    if (status.status === 'done') {
      node.addClass('task-done')
    } else if (status.status === 'ignored') {
      node.addClass('task-ignored')
    } else if (status.blocked_by && status.blocked_by.length > 0) {
      node.addClass('task-blocked')
    } else if (status.priority === 'critical') {
      node.addClass('task-critical')
    } else if (status.priority === 'ready') {
      node.addClass('task-ready')
    }
  })
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

function handleCreateNewNode() {
  // Switch to entities tab to create a new entity
  activeTab.value = 'entities'
  // Note: The entity creation dialog will be triggered by the EntityListCard component
  // We could emit an event or use a shared state if we want to auto-open the dialog
}

// Quick YAML editor handlers
async function loadEntityYamlForDrawer(entityName: string) {
  // Check if this is a data source node
  if (dependencyGraph.value) {
    const sourceNodes = dependencyGraph.value.source_nodes || []
    const isDataSource = sourceNodes.some((sn: any) => sn.name === entityName)
    if (isDataSource) {
      // Don't load YAML for data sources
      drawerYamlContent.value = null
      drawerOriginalYamlContent.value = null
      drawerYamlHasChanges.value = false
      return
    }
  }
  
  drawerYamlLoading.value = true
  drawerYamlError.value = null
  try {
    const entity = entityStore.entities.find(e => e.name === entityName)
    if (!entity) {
      throw new Error(`Entity '${entityName}' not found`)
    }
    
    // Convert entity data to YAML
    const yaml = await import('js-yaml')
    const yamlContent = yaml.dump(entity.entity_data, { indent: 2, lineWidth: -1 })
    drawerYamlContent.value = yamlContent
    drawerOriginalYamlContent.value = yamlContent
    drawerYamlHasChanges.value = false
  } catch (err) {
    drawerYamlError.value = err instanceof Error ? err.message : 'Failed to load entity YAML'
    console.error('Failed to load entity YAML:', err)
  } finally {
    drawerYamlLoading.value = false
  }
}

function handleDrawerYamlChange() {
  drawerYamlHasChanges.value = drawerYamlContent.value !== drawerOriginalYamlContent.value
}

async function handleSaveQuickEdit() {
  if (!selectedNode.value || !drawerYamlContent.value) return
  
  drawerYamlSaving.value = true
  drawerYamlError.value = null
  
  try {
    // Parse YAML to validate
    const yaml = await import('js-yaml')
    const entityData = yaml.load(drawerYamlContent.value)
    
    if (typeof entityData !== 'object' || entityData === null) {
      throw new Error('Invalid YAML: must be an object')
    }
    
    // Update entity
    await entityStore.updateEntity(projectName.value, selectedNode.value, {
      entity_data: entityData as any
    })
    
    // Update original content to match saved content
    drawerOriginalYamlContent.value = drawerYamlContent.value
    drawerYamlHasChanges.value = false
    
    // Mark project as changed
    markAsChanged()
    
    // Refresh dependencies and graph
    await fetchDependencies(projectName.value)
    await nextTick()
    renderGraph()
    
    successMessage.value = `Entity '${selectedNode.value}' saved successfully`
    showSuccessSnackbar.value = true
    
  } catch (err) {
    drawerYamlError.value = err instanceof Error ? err.message : 'Failed to save entity'
    console.error('Failed to save quick edit:', err)
  } finally {
    drawerYamlSaving.value = false
  }
}

function handleCloseQuickEdit() {
  if (drawerYamlHasChanges.value) {
    if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
      return
    }
  }
  
  showDetailsDrawer.value = false
  selectedNode.value = null
  drawerYamlContent.value = null
  drawerOriginalYamlContent.value = null
  drawerYamlHasChanges.value = false
  drawerYamlError.value = null
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
    
    // Initialize task status
    await taskStatusStore.initialize(projectName.value)
    
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
      // Reinitialize task status for new project
      await taskStatusStore.initialize(newName)
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
  
  // Update route query to enable context-sensitive help
  const currentTab = route.query.tab
  if (currentTab !== newTab) {
    router.replace({ query: { ...route.query, tab: newTab } })
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

// Watch for task status updates to apply styling
watch(
  () => taskStatusStore.taskStatus,
  () => {
    applyTaskStatusToNodes()
  },
  { deep: true }
)

// Watch for dependency graph updates to apply task status
watch(
  () => dependencyGraph.value,
  async () => {
    // Wait for graph to render, then apply task status
    await nextTick()
    applyTaskStatusToNodes()
    applyTaskFilter()
  }
)

// Watch for task filter changes to show/hide nodes
watch(
  () => currentTaskFilter.value,
  () => {
    applyTaskFilter()
  }
)

// Apply task filter to show/hide nodes based on status
function applyTaskFilter() {
  if (!cy.value || !taskStatusStore.taskStatus) return

  const filter = currentTaskFilter.value

  cy.value.nodes().forEach(node => {
    const entityName = node.id()
    const status = taskStatusStore.getEntityStatus(entityName)
    
    if (!status) {
      // If no status info, show by default
      node.style('display', 'element')
      return
    }

    let shouldShow = true

    switch (filter) {
      case 'todo':
        shouldShow = status.status === 'todo'
        break
      case 'done':
        shouldShow = status.status === 'done'
        break
      case 'ignored':
        shouldShow = status.status === 'ignored'
        break
      case 'all':
      default:
        shouldShow = true
        break
    }

    node.style('display', shouldShow ? 'element' : 'none')
  })

  // Also hide edges connected to hidden nodes
  cy.value.edges().forEach(edge => {
    const source = edge.source()
    const target = edge.target()
    const sourceHidden = source.style('display') === 'none'
    const targetHidden = target.style('display') === 'none'
    
    edge.style('display', sourceHidden || targetHidden ? 'none' : 'element')
  })
}
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
  height: calc(100vh - 360px);
  min-height: 500px;
}

.graph-card-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.graph-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: transparent;
}

.graph-stats-overlay {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 10;
  max-width: 280px;
}

.stats-card {
  background: rgba(var(--v-theme-surface), 0.95) !important;
  backdrop-filter: blur(12px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(var(--v-border-color), 0.12);
  border-radius: 8px;
}

.graph-fab-container {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 10;
}

.graph-fab {
  background: rgba(var(--v-theme-surface), 0.9) !important;
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.2s ease;
}

.graph-fab:hover {
  background: rgba(var(--v-theme-surface), 1) !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  transform: translateY(-2px);
}

/* Quick edit drawer styles */
.drawer-body {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 112px); /* viewport - toolbar - footer */
  overflow: hidden;
}

.drawer-alerts {
  flex-shrink: 0; /* Don't shrink alerts */
}

.drawer-editor {
  flex: 1;
  min-height: 0; /* Critical for flex */
  overflow: hidden;
}

.drawer-footer {
  position: sticky;
  bottom: 0;
  background: rgb(var(--v-theme-surface));
  z-index: 10;
}

.drawer-editor :deep(.monaco-editor-container) {
  height: 100% !important;
}

.data-source-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
}
</style>
