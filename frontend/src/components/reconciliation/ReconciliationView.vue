<template>
  <div class="reconciliation-view">
    <v-card>
      <v-card-title>
        <div class="d-flex align-center justify-space-between">
          <span>Entity Reconciliation</span>
          <v-chip v-if="reconcilableEntities.length > 0" size="small" variant="tonal">
            {{ reconcilableEntities.length }} entities configured
          </v-chip>
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
                  <v-list-item-subtitle> Add reconciliation specs to your configuration YAML </v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-select>
          </v-col>

          <v-col cols="12" md="6" class="d-flex align-center gap-2">
            <v-text-field
              v-if="entitySpec"
              :model-value="`Auto-accept: ${Math.round(entitySpec.auto_accept_threshold * 100)}%`"
              label="Threshold"
              variant="outlined"
              density="comfortable"
              readonly
              prepend-inner-icon="mdi-target"
            />
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
          v-if="selectedEntity && entitySpec && previewData.length > 0"
          :entity-spec="entitySpec"
          :preview-data="previewData"
          :loading="loading"
          @update:mapping="handleUpdateMapping"
          @save="handleSaveChanges"
        />

        <!-- Empty State - No Data -->
        <v-card
          v-else-if="selectedEntity && entitySpec && previewData.length === 0"
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
  configName: string
}

const props = defineProps<Props>()

// Store
const reconciliationStore = useReconciliationStore()
const { config, loading, error, reconcilableEntities, hasConfig, previewData } = storeToRefs(reconciliationStore)

// Local state
const selectedEntity = ref<string | null>(null)
const showResultSnackbar = ref(false)
const resultMessage = ref('')
const resultColor = ref('success')

// Computed
const entitySpec = computed(() => {
  if (!selectedEntity.value || !config.value) return null
  return config.value.entities[selectedEntity.value] || null
})

// Methods
async function handleAutoReconcile() {
  if (!selectedEntity.value) return

  try {
    const result = await reconciliationStore.autoReconcile(props.configName, selectedEntity.value)

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
  if (!selectedEntity.value) return

  try {
    await reconciliationStore.updateMapping(props.configName, selectedEntity.value, row, seadId, notes)
  } catch (e: any) {
    resultMessage.value = `Failed to update mapping: ${e.message}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  }
}

async function handleSaveChanges() {
  try {
    await reconciliationStore.saveConfig(props.configName)
    resultMessage.value = 'Changes saved successfully'
    resultColor.value = 'success'
    showResultSnackbar.value = true
  } catch (e: any) {
    resultMessage.value = `Failed to save changes: ${e.message}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  }
}

// Load config on mount
onMounted(async () => {
  try {
    await reconciliationStore.loadConfig(props.configName)

    // Auto-select first entity if available
    if (reconcilableEntities.value.length > 0) {
      selectedEntity.value = reconcilableEntities.value[0]
    }
  } catch (e) {
    console.error('Failed to load reconciliation config:', e)
  }
})

// Watch for config changes
watch(
  () => props.configName,
  async (newConfigName) => {
    if (newConfigName) {
      selectedEntity.value = null
      await reconciliationStore.loadConfig(newConfigName)
    }
  }
)
</script>

<style scoped>
.gap-2 {
  gap: 0.5rem;
}
</style>
