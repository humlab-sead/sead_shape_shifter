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

      <v-card-text>
        <!-- Entity Selection -->
        <v-row>
          <v-col cols="12" md="6">
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
                  <v-list-item-title class="text-grey"> No entities configured for reconciliation </v-list-item-title>
                  <v-list-item-subtitle> Add reconciliation specs to your project YAML </v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-select>
          </v-col>

          <v-col cols="12" md="6" class="d-flex align-center gap-2">
            <div v-if="entitySpec" class="flex-grow-1 d-flex flex-column">
              <v-slider
                v-model="autoAcceptThreshold"
                :min="50"
                :max="100"
                :step="1"
                thumb-label="always"
                color="primary"
                prepend-icon="mdi-target"
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
                prepend-icon="mdi-eye"
              >
                <template #prepend>
                  <v-icon icon="mdi-eye" />
                </template>
                <template #append>
                  <v-chip size="small" variant="tonal">{{ reviewThreshold }}%</v-chip>
                </template>
                <template #label> Review Threshold </template>
              </v-slider>
            </div>
          </v-col>
        </v-row>

        <!-- Entity Spec Details -->
        <v-alert v-if="entitySpec" type="info" variant="tonal" class="mb-4">
          <v-alert-title>Reconciliation Specification</v-alert-title>
          <div class="mt-2">
            <div v-if="entitySpec.source">
              <strong>Source:</strong>
              <span v-if="typeof entitySpec.source === 'string'">{{ entitySpec.source }}</span>
              <span v-else>Custom query ({{ entitySpec.source.data_source }})</span>
            </div>
            <div><strong>Keys:</strong> {{ entitySpec.keys.join(', ') }}</div>
            <div v-if="Object.keys(entitySpec.property_mappings).length > 0">
              <strong>Properties:</strong>
              {{
                Object.entries(entitySpec.property_mappings)
                  .map(([k, v]) => `${k}→${v}`)
                  .join(', ')
              }}
            </div>
            <div v-if="entitySpec.remote.service_type">
              <strong>Service Type:</strong> {{ entitySpec.remote.service_type }}
            </div>
            <div><strong>Mappings:</strong> {{ entitySpec.mapping.length }} defined</div>
          </div>
        </v-alert>

        <!-- Auto-Reconcile Button -->
        <div v-if="selectedEntity && entitySpec" class="d-flex justify-end mb-4">
          <v-btn
            variant="tonal"
            color="primary"
            prepend-icon="mdi-auto-fix"
            :loading="loading"
            @click="handleAutoReconcile"
          >
            Auto-Reconcile
          </v-btn>
        </div>

        <!-- Reconciliation Grid -->
        <reconciliation-grid
          v-if="selectedEntity && entitySpec && entityPreviewData.length"
          :entity-spec="entitySpec"
          :preview-data="entityPreviewData"
          :loading="loading"
          :project-name="projectName"
          :entity-name="selectedEntity"
          @update:mapping="handleUpdateMapping"
          @save="handleSaveChanges"
        />

        <!-- Empty State - No Data -->
        <v-card
          v-else-if="selectedEntity && entitySpec && !entityPreviewData.length"
          variant="outlined"
          class="pa-8 text-center"
        >
          <v-icon icon="mdi-database-off-outline" size="64" color="grey" />
          <h3 class="text-h6 mt-4 mb-2">No Preview Data</h3>
          <p class="text-grey">Run auto-reconcile to fetch and process entity data</p>
        </v-card>

        <!-- Empty State - No Selection -->
        <v-card v-else-if="!selectedEntity" variant="outlined" class="pa-8 text-center">
          <v-icon icon="mdi-information-outline" size="64" color="grey" />
          <h3 class="text-h6 mt-4 mb-2">No Entity Selected</h3>
          <p class="text-grey mb-4">Select an entity above to begin reconciliation</p>
        </v-card>
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
    const result = await reconciliationStore.autoReconcile(props.projectName, selectedEntity.value, thresholdDecimal, reviewThresholdDecimal)

    resultMessage.value = `Auto-reconciliation complete: ${result.auto_accepted} auto-matched, ${result.needs_review} need review, ${result.unmatched} unmatched`
    resultColor.value = 'success'
    showResultSnackbar.value = true
  } catch (e: any) {
    resultMessage.value = `Auto-reconciliation failed: ${e.message}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  }
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
  (newEntity) => {
    if (newEntity && entitySpec.value && entitySpec.value.auto_accept_threshold) {
      // Sync slider with entity spec threshold when entity changes (convert decimal to percentage)
      autoAcceptThreshold.value = Math.round(entitySpec.value.auto_accept_threshold * 100)
    }
    if (newEntity && entitySpec.value && entitySpec.value.review_threshold != null) {
      reviewThreshold.value = Math.round(entitySpec.value.review_threshold * 100)
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
