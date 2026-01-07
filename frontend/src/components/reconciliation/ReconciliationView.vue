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
        <v-tab value="configuration">
          <v-icon start>mdi-file-document-edit</v-icon>
          Configuration
        </v-tab>
        <v-tab value="reconcile" :disabled="!selectedEntity">
          <v-icon start>mdi-auto-fix</v-icon>
          Reconcile & Review
        </v-tab>
      </v-tabs>

      <v-divider />

      <v-card-text>
        <v-window v-model="activeTab">
          <!-- Configuration Tab -->
          <v-window-item value="configuration">
            <div class="py-4">
              <h3 class="text-h6 mb-4">
                <v-icon start>mdi-file-document-edit</v-icon>
                Reconciliation Specifications
              </h3>
              <p class="text-grey mb-4">
                Configure reconciliation specifications for your entities. Click the reconcile button on any specification to start.
              </p>
              <specifications-list :project-name="projectName" @reconcile="handleReconcileSpec" />
            </div>
          </v-window-item>

          <!-- Reconcile Tab -->
          <v-window-item value="reconcile">
            <div class="py-4">
              <div class="d-flex justify-space-between align-center mb-4">
                <h3 class="text-h6">
                  <v-icon start>mdi-auto-fix</v-icon>
                  Reconcile & Review
                </h3>
                
                <!-- Auto-Reconcile Button -->
                <v-btn
                  v-if="selectedEntity && entitySpec"
                  variant="tonal"
                  color="primary"
                  prepend-icon="mdi-auto-fix"
                  :loading="loading"
                  @click="handleAutoReconcile"
                >
                  Run Auto-Reconcile
                </v-btn>
              </div>

              <!-- Reconciliation Grid -->
              <reconciliation-grid
                v-if="selectedEntity && selectedTarget && entitySpec && entityPreviewData.length"
                :entity-spec="entitySpec"
                :preview-data="entityPreviewData"
                :loading="loading"
                :project-name="projectName"
                :entity-name="selectedEntity"
                :target-field="selectedTarget"
                @update:mapping="handleUpdateMapping"
                @save="handleSaveChanges"
              />

              <!-- Empty State - No Data -->
              <v-card v-else variant="outlined" class="pa-8 text-center">
                <v-icon icon="mdi-database-off-outline" size="64" color="grey" />
                <h3 class="text-h6 mt-4 mb-2">No Data Available</h3>
                <p class="text-grey">Run auto-reconcile to fetch and process entity data, then review and adjust mappings as needed</p>
                <v-btn class="mt-4" variant="tonal" @click="activeTab = 'setup'"> Go to Setup </v-btn>
              </v-card>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useReconciliationStore } from '@/stores/reconciliation'
import { storeToRefs } from 'pinia'
import ReconciliationGrid from './ReconciliationGrid.vue'
import SpecificationsList from './SpecificationsList.vue'
import type { ReconciliationPreviewRow } from '@/types'

interface Props {
  projectName: string
}

const props = defineProps<Props>()

// Store
const reconciliationStore = useReconciliationStore()
const { reconciliationConfig, loading, reconcilableEntities, previewData, getEntityTargets } = storeToRefs(reconciliationStore)

// Local state
const activeTab = ref<string>('configuration') // Tab state: configuration, reconcile
const selectedEntity = ref<string | null>(null)
const selectedTarget = ref<string | null>(null) // Selected target field
const autoAcceptThreshold = ref<number>(95) // User-adjustable threshold (percentage)
const showResultSnackbar = ref(false)
const resultMessage = ref('')
const resultColor = ref('success')
const serviceStatus = ref<{ status: string; service_name?: string; error?: string } | null>(null)

// Computed
const entityTargets = computed(() => {
  if (!selectedEntity.value) return []
  return getEntityTargets.value(selectedEntity.value)
})

const entitySpec = computed(() => {
  if (!selectedEntity.value || !selectedTarget.value || !reconciliationConfig.value) return null
  const entityConfigs = reconciliationConfig.value.entities[selectedEntity.value]
  if (!entityConfigs) return null
  return entityConfigs[selectedTarget.value] || null
})

const entityPreviewData = computed(() => {
  if (!selectedEntity.value) return []
  return previewData.value[selectedEntity.value] || []
})

// Methods
function handleReconcileSpec(entityName: string, targetField: string) {
  selectedEntity.value = entityName
  selectedTarget.value = targetField
  activeTab.value = 'reconcile'
}

async function handleAutoReconcile() {
  if (!selectedEntity.value || !selectedTarget.value) return

  try {
    // Convert percentage to decimal (e.g., 95 -> 0.95)
    const thresholdDecimal = autoAcceptThreshold.value / 100
    const result = await reconciliationStore.autoReconcile(
      props.projectName,
      selectedEntity.value,
      selectedTarget.value,
      thresholdDecimal
    )

    // Reload preview data to show updated results
    await reconciliationStore.loadPreviewData(props.projectName, selectedEntity.value, selectedTarget.value)

    resultMessage.value = `Auto-reconciliation complete: ${result.auto_accepted} auto-matched, ${result.needs_review} need review, ${result.unmatched} unmatched`
    resultColor.value = 'success'
    showResultSnackbar.value = true
    
    // Switch to reconcile tab to show results
    if (entityPreviewData.value.length > 0) {
      activeTab.value = 'reconcile'
    }
  } catch (e: any) {
    resultMessage.value = `Auto-reconciliation failed: ${e.message}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  }
}

async function handleUpdateMapping(row: ReconciliationPreviewRow, seadId: number | null, notes?: string) {
  if (!selectedEntity.value || !selectedTarget.value || !entitySpec.value) return

  try {
    // Extract the source value for the target field
    const sourceValue = row[selectedTarget.value]
    await reconciliationStore.updateMapping(
      props.projectName,
      selectedEntity.value,
      selectedTarget.value,
      sourceValue,
      seadId,
      notes
    )
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

// Watch for entity changes and auto-select first target
watch(
  selectedEntity,
  (newEntity) => {
    if (newEntity && entityTargets.value.length > 0) {
      // Auto-select the first target
      selectedTarget.value = entityTargets.value[0] || null
    } else {
      selectedTarget.value = null
    }
  },
  { immediate: true }
)

// Watch for target changes and load preview data
watch(
  [selectedEntity, selectedTarget],
  async ([newEntity, newTarget]) => {
    if (newEntity && newTarget && entitySpec.value) {
      // Sync slider with entity spec threshold when target changes (convert decimal to percentage)
      if (entitySpec.value.auto_accept_threshold) {
        autoAcceptThreshold.value = Math.round(entitySpec.value.auto_accept_threshold * 100)
      }
      
      // Load preview data for the selected entity and target
      try {
        await reconciliationStore.loadPreviewData(props.projectName, newEntity, newTarget)
      } catch (e: any) {
        console.error('[ReconciliationView] Failed to load preview data:', e)
        resultMessage.value = `Failed to load preview data: ${e.message}`
        resultColor.value = 'error'
        showResultSnackbar.value = true
      }
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.gap-2 {
  gap: 0.5rem;
}
</style>
