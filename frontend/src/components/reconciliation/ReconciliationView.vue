<template>
  <div class="reconciliation-view">
    <v-card>
      <v-card-title>
        <div class="d-flex align-center justify-space-between">
          <span>Entity Reconciliation</span>
          <div class="d-flex align-center gap-2">
            <!-- Service Status Indicator -->
            <v-chip
              v-if="serviceStatus"
              :color="serviceStatus.status === 'online' ? 'success' : 'error'"
              size="small"
              variant="flat"
              :prepend-icon="serviceStatus.status === 'online' ? 'mdi-check-circle' : 'mdi-alert-circle'"
            >
              Service {{ serviceStatus.status === 'online' ? 'Online' : 'Offline' }}
            </v-chip>
            <v-chip v-if="reconcilableEntities.length > 0" size="small" variant="tonal">
              {{ reconcilableEntities.length }} entities configured
            </v-chip>
          </div>
        </div>
      </v-card-title>

      <!-- Tabs -->
      <v-tabs v-model="activeTab" bg-color="transparent" color="primary" grow>
        <v-tab value="setup" :disabled="!hasConfig">
          <v-icon start>mdi-cog</v-icon>
          Setup
        </v-tab>
        <v-tab value="reconcile" :disabled="!selectedEntity">
          <v-icon start>mdi-auto-fix</v-icon>
          Reconcile
        </v-tab>
        <v-tab value="review" :disabled="!selectedEntity || !entityPreviewData.length">
          <v-icon start>mdi-pencil</v-icon>
          Review
        </v-tab>
      </v-tabs>

      <v-divider />

      <v-card-text>
        <v-window v-model="activeTab">
          <!-- Setup Tab -->
          <v-window-item value="setup">
            <div class="py-4">
              <h3 class="text-h6 mb-4">
                <v-icon start>mdi-cog</v-icon>
                Configuration
              </h3>

              <!-- Entity Selection -->
              <v-card variant="outlined" class="mb-4">
                <v-card-title class="text-subtitle-1">Entity Selection</v-card-title>
                <v-card-text>
                  <v-select
                    v-model="selectedEntity"
                    :items="reconcilableEntities"
                    label="Select Entity to Reconcile"
                    variant="outlined"
                    density="comfortable"
                    :loading="loading"
                    :disabled="!hasConfig || reconcilableEntities.length === 0"
                    prepend-inner-icon="mdi-table"
                  >
                    <template #no-data>
                      <v-list-item>
                        <v-list-item-title class="text-grey">
                          No entities configured for reconciliation
                        </v-list-item-title>
                        <v-list-item-subtitle> Add reconciliation specs to your project YAML </v-list-item-subtitle>
                      </v-list-item>
                    </template>
                  </v-select>
                </v-card-text>
              </v-card>

              <!-- Thresholds -->
              <v-card v-if="entitySpec" variant="outlined" class="mb-4">
                <v-card-title class="text-subtitle-1">Match Thresholds</v-card-title>
                <v-card-text>
                  <v-slider
                    v-model="autoAcceptThreshold"
                    :min="50"
                    :max="100"
                    :step="1"
                    thumb-label="always"
                    color="primary"
                    class="mb-4"
                  >
                    <template #prepend>
                      <v-icon icon="mdi-target" />
                    </template>
                    <template #append>
                      <v-chip size="small" variant="tonal">{{ autoAcceptThreshold }}%</v-chip>
                    </template>
                    <template #label> Auto-accept Threshold </template>
                  </v-slider>

                  <v-slider
                    v-model="reviewThreshold"
                    :min="0"
                    :max="100"
                    :step="1"
                    thumb-label="always"
                    color="warning"
                  >
                    <template #prepend>
                      <v-icon icon="mdi-eye" />
                    </template>
                    <template #append>
                      <v-chip size="small" variant="tonal">{{ reviewThreshold }}%</v-chip>
                    </template>
                    <template #label> Review Threshold </template>
                  </v-slider>
                </v-card-text>
              </v-card>

              <!-- Entity Spec Details -->
              <v-card v-if="entitySpec" variant="outlined">
                <v-card-title class="text-subtitle-1">Specification Details</v-card-title>
                <v-card-text>
                  <v-list density="compact">
                    <v-list-item v-if="entitySpec.source">
                      <template #prepend>
                        <v-icon>mdi-database</v-icon>
                      </template>
                      <v-list-item-title>Source</v-list-item-title>
                      <v-list-item-subtitle>
                        <span v-if="typeof entitySpec.source === 'string'">{{ entitySpec.source }}</span>
                        <span v-else>Custom query ({{ entitySpec.source.data_source }})</span>
                      </v-list-item-subtitle>
                    </v-list-item>

                    <v-list-item>
                      <template #prepend>
                        <v-icon>mdi-key</v-icon>
                      </template>
                      <v-list-item-title>Keys</v-list-item-title>
                      <v-list-item-subtitle>{{ entitySpec.keys.join(', ') }}</v-list-item-subtitle>
                    </v-list-item>

                    <v-list-item v-if="Object.keys(entitySpec.property_mappings).length > 0">
                      <template #prepend>
                        <v-icon>mdi-swap-horizontal</v-icon>
                      </template>
                      <v-list-item-title>Properties</v-list-item-title>
                      <v-list-item-subtitle>
                        {{
                          Object.entries(entitySpec.property_mappings)
                            .map(([k, v]) => `${k}→${v}`)
                            .join(', ')
                        }}
                      </v-list-item-subtitle>
                    </v-list-item>

                    <v-list-item v-if="entitySpec.remote.service_type">
                      <template #prepend>
                        <v-icon>mdi-cloud</v-icon>
                      </template>
                      <v-list-item-title>Service Type</v-list-item-title>
                      <v-list-item-subtitle>{{ entitySpec.remote.service_type }}</v-list-item-subtitle>
                    </v-list-item>

                    <v-list-item>
                      <template #prepend>
                        <v-icon>mdi-link-variant</v-icon>
                      </template>
                      <v-list-item-title>Mappings</v-list-item-title>
                      <v-list-item-subtitle>{{ entitySpec.mapping.length }} defined</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-card-text>
              </v-card>

              <!-- Continue Button -->
              <div v-if="selectedEntity && entitySpec" class="d-flex justify-end mt-4">
                <v-btn
                  variant="tonal"
                  color="primary"
                  append-icon="mdi-arrow-right"
                  @click="activeTab = 'reconcile'"
                >
                  Continue to Reconcile
                </v-btn>
              </div>

              <!-- Empty State -->
              <v-card v-if="!selectedEntity" variant="outlined" class="pa-8 text-center mt-4">
                <v-icon icon="mdi-information-outline" size="64" color="grey" />
                <h3 class="text-h6 mt-4 mb-2">No Entity Selected</h3>
                <p class="text-grey mb-4">Select an entity above to begin reconciliation</p>
              </v-card>
            </div>
          </v-window-item>

          <!-- Reconcile Tab -->
          <v-window-item value="reconcile">
            <div class="py-4">
              <h3 class="text-h6 mb-4">
                <v-icon start>mdi-auto-fix</v-icon>
                Auto-Reconciliation
              </h3>

              <!-- Actions Card -->
              <v-card variant="outlined" class="mb-4">
                <v-card-title class="text-subtitle-1">Actions</v-card-title>
                <v-card-text>
                  <div class="d-flex align-center gap-4">
                    <v-btn
                      variant="tonal"
                      color="primary"
                      prepend-icon="mdi-auto-fix"
                      size="large"
                      :loading="loading"
                      @click="handleAutoReconcile"
                    >
                      Run Auto-Reconcile
                    </v-btn>
                    <div class="text-caption text-grey">
                      Auto-accept: ≥{{ autoAcceptThreshold }}% | Review: ≥{{ reviewThreshold }}%
                    </div>
                  </div>
                </v-card-text>
              </v-card>

              <!-- Statistics Card -->
              <reconciliation-stats-card
                v-if="entityPreviewData.length"
                :preview-data="entityPreviewData"
                :entity-spec="entitySpec!"
                @refresh="handleAutoReconcile"
                class="mb-4"
              />

              <!-- Continue Button -->
              <div v-if="entityPreviewData.length" class="d-flex justify-end mt-4">
                <v-btn
                  variant="tonal"
                  color="primary"
                  append-icon="mdi-arrow-right"
                  @click="activeTab = 'review'"
                >
                  Continue to Review
                </v-btn>
              </div>

              <!-- Empty State -->
              <v-card v-if="!entityPreviewData.length" variant="outlined" class="pa-8 text-center mt-4">
                <v-icon icon="mdi-database-off-outline" size="64" color="grey" />
                <h3 class="text-h6 mt-4 mb-2">No Preview Data</h3>
                <p class="text-grey">Click "Run Auto-Reconcile" above to fetch and process entity data</p>
              </v-card>
            </div>
          </v-window-item>

          <!-- Review Tab -->
          <v-window-item value="review">
            <div class="py-4">
              <h3 class="text-h6 mb-4">
                <v-icon start>mdi-pencil</v-icon>
                Manual Review & Refinement
              </h3>

              <!-- Compact Statistics -->
              <v-card variant="outlined" class="mb-4">
                <v-card-text class="py-2">
                  <div class="d-flex align-center justify-space-around flex-wrap gap-2">
                    <v-chip color="success" variant="flat" prepend-icon="mdi-check-circle">
                      {{ getStatistics().autoMatched }} Auto-matched
                    </v-chip>
                    <v-chip color="warning" variant="flat" prepend-icon="mdi-alert-circle">
                      {{ getStatistics().needsReview }} Needs Review
                    </v-chip>
                    <v-chip color="error" variant="flat" prepend-icon="mdi-close-circle">
                      {{ getStatistics().noMatches }} No Matches
                    </v-chip>
                    <v-chip color="grey" variant="flat" prepend-icon="mdi-cancel">
                      {{ getStatistics().willNotMatch }} Won't Match
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>

              <!-- Reconciliation Grid -->
              <reconciliation-grid
                v-if="entitySpec && entityPreviewData.length"
                :entity-spec="entitySpec"
                :preview-data="entityPreviewData"
                :loading="loading"
                :project-name="projectName"
                :entity-name="selectedEntity!"
                @update:mapping="handleUpdateMapping"
                @save="handleSaveChanges"
              />
            </div>
          </v-window-item>
        </v-window>
      </v-card-text>
    </v-card>

    <!-- Result Snackbar -->
    <v-snackbar v-model="showResultSnackbar" :color="resultColor" timeout="5000">
      {{ resultMessage }}
      <template #actions>
        <v-btn variant="text" @click="showResultSnackbar = false">Close</v-btn>
      </template>
    </v-snackbar>

    <!-- Progress Dialog -->
    <reconciliation-progress-dialog
      :operation-id="currentOperationId"
      @close="handleProgressClose"
      @complete="handleProgressComplete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useReconciliationStore } from '@/stores/reconciliation'
import { storeToRefs } from 'pinia'
import ReconciliationGrid from './ReconciliationGrid.vue'
import ReconciliationStatsCard from './ReconciliationStatsCard.vue'
import ReconciliationProgressDialog from './ReconciliationProgressDialog.vue'
import type { ReconciliationPreviewRow } from '@/types'

interface Props {
  projectName: string
}

const props = defineProps<Props>()

// Store
const reconciliationStore = useReconciliationStore()
const { reconciliationConfig, loading, reconcilableEntities, hasConfig, previewData } = storeToRefs(reconciliationStore)

// Local state
const selectedEntity = ref<string | null>(null)
const autoAcceptThreshold = ref<number>(95) // User-adjustable threshold (percentage)
const reviewThreshold = ref<number>(70) // User-adjustable threshold (percentage)
const showResultSnackbar = ref(false)
const resultMessage = ref('')
const resultColor = ref('success')
const serviceStatus = ref<{ status: string; service_name?: string; error?: string } | null>(null)
const currentOperationId = ref<string | null>(null)
const activeTab = ref<string>('setup') // Tab state: setup, reconcile, review

// Computed
const entitySpec = computed(() => {
  if (!selectedEntity.value || !reconciliationConfig.value) return null
  return reconciliationConfig.value.entities[selectedEntity.value] || null
})

const entityPreviewData = computed(() => {
  if (!selectedEntity.value) return []
  return previewData.value[selectedEntity.value] || []
})

// Methods
async function handleAutoReconcile() {
  if (!selectedEntity.value) return

  try {
    // Convert percentage to decimal (e.g., 95 -> 0.95)
    const thresholdDecimal = autoAcceptThreshold.value / 100
    const reviewThresholdDecimal = reviewThreshold.value / 100
    
    // Start async reconciliation with progress tracking
    const response = await reconciliationStore.autoReconcileAsync(
      props.projectName,
      selectedEntity.value,
      thresholdDecimal,
      reviewThresholdDecimal
    )
    
    // Set operation ID to trigger progress dialog
    currentOperationId.value = response.operation_id
  } catch (e: any) {
    resultMessage.value = `Failed to start reconciliation: ${e.message}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  }
}

function handleProgressClose() {
  currentOperationId.value = null
  // Reload data to show updated results
  if (selectedEntity.value) {
    reconciliationStore.loadReconciliationConfig(props.projectName).then(() => {
      if (selectedEntity.value) {
        reconciliationStore.loadPreviewData(props.projectName, selectedEntity.value)
      }
    })
  }
}

function handleProgressComplete(_metadata: any) {
  // Operation completed successfully - switch to review tab
  activeTab.value = 'review'
  resultMessage.value = 'Auto-reconciliation completed successfully'
  resultColor.value = 'success'
  showResultSnackbar.value = true
}

async function handleUpdateMapping(row: ReconciliationPreviewRow, seadId: number | null, notes?: string) {
  if (!selectedEntity.value || !entitySpec.value) return

  try {
    // Extract source values from row based on entity keys
    const sourceValues = entitySpec.value.keys.map((key) => row[key])
    await reconciliationStore.updateMapping(props.projectName, selectedEntity.value, sourceValues, seadId, notes)
  } catch (e: any) {
    resultMessage.value = `Failed to update mapping: ${e.message}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  }
}

async function handleSaveChanges() {
  try {
    await reconciliationStore.saveReconciliationConfig(props.projectName)
    resultMessage.value = 'Changes saved successfully'
    resultColor.value = 'success'
    showResultSnackbar.value = true
  } catch (e: any) {
    resultMessage.value = `Failed to save changes: ${e.message}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  }
}

function getStatistics() {
  const autoMatched = entityPreviewData.value.filter(
    (row) => row.sead_id != null && (row.confidence ?? 0) >= autoAcceptThreshold.value && !row.will_not_match
  ).length
  const needsReview = entityPreviewData.value.filter(
    (row) =>
      row.candidates &&
      row.candidates.length > 0 &&
      (row.confidence ?? 0) < autoAcceptThreshold.value &&
      (row.confidence ?? 0) >= reviewThreshold.value &&
      !row.will_not_match
  ).length
  const noMatches = entityPreviewData.value.filter(
    (row) => (!row.candidates || row.candidates.length === 0) && !row.sead_id && !row.will_not_match
  ).length
  const willNotMatch = entityPreviewData.value.filter((row) => row.will_not_match).length

  return {
    autoMatched,
    needsReview,
    noMatches,
    willNotMatch,
  }
}

async function checkServiceHealth() {
  try {
    const response = await reconciliationStore.checkServiceHealth()
    serviceStatus.value = response
  } catch (e: any) {
    console.error('Failed to check service health:', e)
    serviceStatus.value = { status: 'offline', error: e.message }
  }
}

// Load project on mount
onMounted(async () => {
  try {
    console.log('[ReconciliationView] Mounted with project:', props.projectName)

    // Check service health
    await checkServiceHealth()

    // Load config
    await reconciliationStore.loadReconciliationConfig(props.projectName)

    // Auto-select first entity if available
    if (reconcilableEntities.value.length > 0) {
      selectedEntity.value = reconcilableEntities.value[0] ?? null
    } else {
      console.warn('[ReconciliationView] No reconcilable entities found')
    }
  } catch (e: any) {
    console.error('[ReconciliationView] Failed to load reconciliation config:', e)
    resultMessage.value = `Failed to load reconciliation config: ${e.message || e.response?.data?.detail || 'Unknown error'}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  }
})

// Watch for project changes
watch(
  () => props.projectName,
  async (newProjectName) => {
    if (newProjectName) {
      selectedEntity.value = null
      await reconciliationStore.loadReconciliationConfig(newProjectName)
    }
  }
)

// Watch for entity changes and sync threshold (only when entity changes, not on config reload)
watch(
  selectedEntity,
  async (newEntity) => {
    if (!newEntity) return
    
    // Wait for entitySpec to be available
    if (entitySpec.value) {
      if (entitySpec.value.auto_accept_threshold) {
        // Sync slider with entity spec threshold when entity changes (convert decimal to percentage)
        autoAcceptThreshold.value = Math.round(entitySpec.value.auto_accept_threshold * 100)
      }
      if (entitySpec.value.review_threshold != null) {
        reviewThreshold.value = Math.round(entitySpec.value.review_threshold * 100)
      }
      
      // Load preview data when entity is selected
      try {
        await reconciliationStore.loadPreviewData(props.projectName, newEntity)
      } catch (e: any) {
        console.error('[ReconciliationView] Failed to load preview data:', e)
        // Don't show error to user, just log it - they can run auto-reconcile to get data
      }
    }
  },
  { immediate: true }
)

// Keep in-memory config in sync with slider values so saving config persists thresholds.
watch(autoAcceptThreshold, (value) => {
  if (!entitySpec.value) return
  entitySpec.value.auto_accept_threshold = value / 100
})

watch(reviewThreshold, (value) => {
  if (!entitySpec.value) return
  entitySpec.value.review_threshold = value / 100
})
</script>

<style scoped>
.gap-2 {
  gap: 0.5rem;
}
</style>
