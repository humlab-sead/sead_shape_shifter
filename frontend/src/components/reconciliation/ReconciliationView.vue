<template>
  <div class="reconciliation-view">
    <v-card>
      <v-card-title>
        <div class="d-flex align-center justify-space-between">
          <span>Entity Reconciliation</span>
          <div class="d-flex align-center gap-2">
            <!-- Service Status with Entity Count -->
            <v-chip
              v-if="serviceStatus"
              :color="serviceStatus.status === 'online' ? 'success' : 'error'"
              size="small"
              variant="flat"
              :prepend-icon="serviceStatus.status === 'online' ? 'mdi-check-circle' : 'mdi-alert-circle'"
            >
              {{
                serviceStatus.status === 'online' ? `Online (${availableEntityTypes} reconciliation types)` : 'Offline'
              }}
            </v-chip>

            <!-- Configured Specifications Count -->
            <v-chip v-if="specifications.length > 0" size="small" variant="tonal" color="primary">
              {{ specifications.length }}
              {{ specifications.length === 1 ? 'specification' : 'specifications' }} configured
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
        <v-tab value="yaml">
          <v-icon start>mdi-code-braces</v-icon>
          YAML
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
                Configure reconciliation specifications for your entities. Click the reconcile button on any
                specification to start.
              </p>
              <specifications-list
                :project-name="projectName"
                :manifest-result="manifestResult"
                @reconcile="handleReconcileSpec"
              />
            </div>
          </v-window-item>

          <!-- YAML Editor Tab -->
          <v-window-item value="yaml">
            <div class="py-4">
              <div class="d-flex justify-space-between align-center mb-4">
                <h3 class="text-h6">
                  <v-icon start>mdi-code-braces</v-icon>
                  Edit Reconciliation YAML
                </h3>
                <div class="d-flex gap-2">
                  <v-btn
                    variant="text"
                    color="primary"
                    prepend-icon="mdi-undo"
                    :disabled="!yamlModified"
                    @click="reloadYaml"
                  >
                    Reload
                  </v-btn>
                  <v-btn
                    variant="tonal"
                    color="primary"
                    prepend-icon="mdi-content-save"
                    :disabled="!yamlModified"
                    :loading="savingYaml"
                    @click="saveYaml"
                  >
                    Save
                  </v-btn>
                </div>
              </div>

              <v-alert
                v-if="yamlError"
                type="error"
                variant="tonal"
                class="mb-4"
                closable
                @click:close="yamlError = null"
              >
                <v-alert-title>YAML Error</v-alert-title>
                {{ yamlError }}
              </v-alert>

              <yaml-editor
                v-model="yamlContent"
                mode="reconciliation"
                height="600px"
                @update:model-value="yamlModified = true"
              />
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
                  data-testid="find-candidates-button"
                  variant="tonal"
                  color="primary"
                  prepend-icon="mdi-auto-fix"
                  :loading="loading"
                  :disabled="!matchEligibility.canMatch"
                  @click="handleAutoReconcile"
                >
                  Find Candidates
                </v-btn>

                <v-btn
                  v-if="selectedEntity"
                  data-testid="manual-link-open"
                  variant="tonal"
                  color="secondary"
                  prepend-icon="mdi-link-variant"
                  @click="openManualLinkDialog()"
                >
                  Add Manual Link
                </v-btn>

                <v-btn
                  v-if="selectedEntity && selectedTarget && entitySpec"
                  data-testid="export-to-mapping-button"
                  variant="tonal"
                  color="primary"
                  prepend-icon="mdi-export"
                  :loading="loading"
                  :disabled="loading"
                  class="ml-2"
                  @click="handleExportToMapping"
                >
                  Export to Mapping
                </v-btn>
              </div>

              <v-alert
                v-if="selectedEntity && entitySpec && !matchEligibility.canMatch"
                data-testid="matching-blocked"
                type="warning"
                variant="tonal"
                class="mb-4"
              >
                Candidate search is blocked: {{ matchEligibility.message }}
              </v-alert>

              <v-alert type="info" variant="tonal" class="mb-4">
                Export checks accepted candidates against SEAD and records local-only approvals separately. Missing or
                invalid candidates are not exported; links exported while the service is unavailable remain unverified
                until you export again. Manual and unowned links are protected.
              </v-alert>

              <v-alert v-if="previewError" data-testid="preview-error" type="error" variant="tonal" class="mb-4">
                Preview could not be loaded: {{ previewError }}
              </v-alert>

              <v-alert v-if="mappingError" data-testid="mapping-error" type="error" variant="tonal" class="mb-4">
                Mapping sidecar could not be loaded: {{ mappingError }}. Effective IDs are unavailable until it loads.
              </v-alert>

              <v-alert v-if="autoReconcileError" data-testid="matching-error" type="error" variant="tonal" class="mb-4">
                Candidate search failed: {{ autoReconcileError }}
              </v-alert>

              <v-alert
                v-if="autoReconcileResult"
                data-testid="matching-result"
                type="success"
                variant="tonal"
                class="mb-4"
              >
                Candidate search considered {{ autoReconcileResult.total }} rows, updated
                {{ autoReconcileResult.proposed }} proposed decisions, and found no candidates for
                {{ autoReconcileResult.unmatched }} rows. {{ autoReconcileResult.errors.length }} rows need attention.
                <ul v-if="autoReconcileResult.errors.length" class="mt-2">
                  <li v-for="(rowError, index) in autoReconcileResult.errors" :key="`${rowError.row_index}-${index}`">
                    Row {{ rowError.row_index + 1
                    }}{{ rowError.local_key_value ? ` (${rowError.local_key_value})` : '' }}:
                    {{ rowError.message }}
                  </li>
                </ul>
              </v-alert>

              <!-- Reconciliation Grid -->
              <reconciliation-grid
                v-if="selectedEntity && selectedTarget && entitySpec && entityPreviewData.length"
                :entity-spec="entitySpec"
                :preview-data="entityPreviewData"
                :mapping-data="entityMappingData"
                :loading="loading || mappingIsLoading"
                :project-name="projectName"
                :entity-name="selectedEntity"
                :target-field="selectedTarget"
                :submit-decision="handleUpdateMapping"
                @manual-link="openManualLinkDialog"
              />

              <!-- Empty State - No Data -->
              <v-card
                v-else-if="!previewError && !entityPreviewData.length"
                variant="outlined"
                class="pa-8 text-center"
              >
                <v-icon icon="mdi-database-off-outline" size="64" color="grey" />
                <h3 class="text-h6 mt-4 mb-2">No Preview Rows</h3>
                <p class="text-grey">
                  Find candidates to create proposals, or add a manual link by entering its encoded business key and
                  target ID.
                </p>
              </v-card>
            </div>
          </v-window-item>
        </v-window>
      </v-card-text>
    </v-card>

    <v-dialog v-model="manualLinkDialog" max-width="600">
      <v-card>
        <v-card-title>Add Manual Link</v-card-title>
        <v-card-subtitle>
          This saves a trusted manual mapping link. It does not check the target ID against SEAD.
        </v-card-subtitle>
        <v-card-text>
          <v-text-field
            v-model="manualLocalKeyValue"
            data-testid="manual-link-key"
            label="Encoded business key"
            placeholder="Enter the encoded local key"
            variant="outlined"
          />
          <v-text-field
            v-model="manualTargetId"
            data-testid="manual-link-target-id"
            label="Target ID"
            inputmode="numeric"
            variant="outlined"
          />
          <v-textarea v-model="manualNotes" label="Notes (optional)" rows="2" variant="outlined" />
          <v-alert v-if="manualLinkError" data-testid="manual-link-error" type="error" variant="tonal">
            {{ manualLinkError }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="manualLinkDialog = false">Cancel</v-btn>
          <v-btn
            data-testid="manual-link-submit"
            variant="tonal"
            color="primary"
            :loading="savingManualLink"
            :disabled="savingManualLink"
            @click="saveManualLink"
          >
            Save Manual Link
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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
import YamlEditor from '@/components/common/YamlEditor.vue'
import type {
  AutoReconcileResult,
  DecisionUpdateRequest,
  MappingEntityResponse,
  ReconciliationManifestResult,
  ReconciliationPreviewRow,
} from '@/types/reconciliation'
import { getReconciliationCompatibility, parseReconciliationManifest } from '@/utils/reconciliationManifest'
import yaml from 'js-yaml'

interface Props {
  projectName: string
}

const props = defineProps<Props>()

// Store
const reconciliationStore = useReconciliationStore()
const {
  reconciliationConfig,
  loading,
  reconcilableEntities,
  previewData,
  previewErrors,
  mappingData,
  mappingErrors,
  mappingLoading,
  getEntityTargets,
  specifications,
} = storeToRefs(reconciliationStore)

// Local state
const activeTab = ref<string>('configuration') // Tab state: configuration, reconcile
const selectedEntity = ref<string | null>(null)
const selectedTarget = ref<string | null>(null) // Selected target field
const autoAcceptThreshold = ref<number>(95) // User-adjustable threshold (percentage)
const showResultSnackbar = ref(false)
const resultMessage = ref('')
const resultColor = ref('success')
const serviceStatus = ref<{ status: string; service_name?: string; error?: string } | null>(null)
const manifestResult = ref<ReconciliationManifestResult | null>(null)
const availableEntityTypes = ref<number>(0)
const autoReconcileResult = ref<AutoReconcileResult | null>(null)
const autoReconcileError = ref<string | null>(null)
const manualLinkDialog = ref(false)
const manualLocalKeyValue = ref('')
const manualTargetId = ref('')
const manualNotes = ref('')
const manualLinkError = ref<string | null>(null)
const savingManualLink = ref(false)

// YAML Editor state
const yamlContent = ref('')
const yamlModified = ref(false)
const yamlError = ref<string | null>(null)
const savingYaml = ref(false)

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

const matchEligibility = computed(() =>
  getReconciliationCompatibility(
    manifestResult.value,
    entitySpec.value?.remote?.service_type,
    entitySpec.value?.property_mappings ?? {}
  )
)

watch(matchEligibility, (eligibility) => {
  if (!eligibility.canMatch) {
    autoReconcileError.value = null
    autoReconcileResult.value = null
  }
})

const entityPreviewData = computed(() => {
  if (!selectedEntity.value || !selectedTarget.value) return []
  return previewData.value[props.projectName]?.[selectedEntity.value]?.[selectedTarget.value] || []
})

const previewError = computed(() => {
  if (!selectedEntity.value || !selectedTarget.value) return null
  return previewErrors.value[props.projectName]?.[selectedEntity.value]?.[selectedTarget.value] ?? null
})

const entityMappingData = computed<MappingEntityResponse | null>(() => {
  if (!selectedEntity.value) return null
  return mappingData.value[props.projectName]?.[selectedEntity.value] ?? null
})

const mappingError = computed(() => {
  if (!selectedEntity.value) return null
  return mappingErrors.value[props.projectName]?.[selectedEntity.value] ?? null
})

const mappingIsLoading = computed(() => {
  if (!selectedEntity.value) return false
  return mappingLoading.value[props.projectName]?.[selectedEntity.value] ?? false
})

// Methods
function handleReconcileSpec(entityName: string, targetField: string) {
  selectedEntity.value = entityName
  selectedTarget.value = targetField
  activeTab.value = 'reconcile'
}

function getApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response
    const detail = response?.data?.detail
    if (typeof detail === 'string') return detail
    if (typeof detail === 'object' && detail !== null && 'message' in detail && typeof detail.message === 'string') {
      return detail.message
    }
  }
  return fallback
}

async function handleAutoReconcile() {
  if (!selectedEntity.value || !selectedTarget.value) return

  autoReconcileError.value = null
  autoReconcileResult.value = null
  if (!matchEligibility.value.canMatch) {
    autoReconcileError.value = matchEligibility.value.message ?? 'Reconciliation compatibility could not be verified.'
    return
  }

  try {
    const thresholdDecimal = autoAcceptThreshold.value / 100
    autoReconcileResult.value = await reconciliationStore.autoReconcile(
      props.projectName,
      selectedEntity.value,
      selectedTarget.value,
      thresholdDecimal,
      entitySpec.value?.review_threshold
    )

    try {
      await reconciliationStore.loadPreviewData(props.projectName, selectedEntity.value, selectedTarget.value)
    } catch (previewLoadError) {
      console.error('[ReconciliationView] Candidate search succeeded but preview reload failed:', previewLoadError)
    }

    resultMessage.value = `Candidate search considered ${autoReconcileResult.value.total} rows; ${autoReconcileResult.value.proposed} proposals updated and ${autoReconcileResult.value.unmatched} rows had no candidates.`
    resultColor.value = 'success'
    showResultSnackbar.value = true

    if (entityPreviewData.value.length > 0) {
      activeTab.value = 'reconcile'
    }
  } catch (e: any) {
    autoReconcileError.value = getApiErrorMessage(e, 'The matching request could not be completed.')
    resultMessage.value = `Candidate search failed: ${autoReconcileError.value}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  }
}

async function handleExportToMapping() {
  if (!selectedEntity.value || !selectedTarget.value) return

  try {
    const entityName = selectedEntity.value
    const targetField = selectedTarget.value
    const result = await reconciliationStore.exportToMapping(props.projectName, entityName, targetField)
    const summary = `${result.exported} link(s) exported; ${result.removed} stale link(s) removed; `
      + `${result.exported_local_only_approvals} local-only approval(s) exported; `
      + `${result.removed_local_only_approvals} stale local-only approval(s) removed; `
      + `${result.skipped_manual} protected link(s) skipped.`

    try {
      await reconciliationStore.loadMappingData(props.projectName, entityName)
    } catch (refreshError) {
      resultMessage.value = `${summary} Export succeeded, but mapping status could not be refreshed: `
        + getApiErrorMessage(refreshError, 'The mapping sidecar could not be reloaded.')
      resultColor.value = 'error'
      showResultSnackbar.value = true
      return
    }

    const rejected = result.outcomes
      .filter((outcome) => outcome.outcome === 'not_found' || outcome.outcome === 'invalid_candidate')
      .map((outcome) => `${outcome.local_key_value}: ${outcome.reason ?? outcome.outcome}`)
    const unverified = result.outcomes
      .filter((outcome) => outcome.outcome === 'unverified')
      .map((outcome) => `${outcome.local_key_value}: ${outcome.reason ?? 'Verification is still needed.'}`)
    const details = [
      rejected.length ? `Not exported: ${rejected.join('; ')}` : '',
      unverified.length ? `Unverified: ${unverified.join('; ')}` : '',
    ].filter(Boolean)

    resultMessage.value = details.length ? `${summary} ${details.join(' ')}` : summary
    resultColor.value = details.length ? 'warning' : 'success'
  } catch (error) {
    resultMessage.value = `Reconciliation export failed: ${getApiErrorMessage(error, 'The export could not be completed.')}`
    resultColor.value = 'error'
  }
  showResultSnackbar.value = true
}

async function handleUpdateMapping(request: DecisionUpdateRequest): Promise<void> {
  if (!selectedEntity.value || !selectedTarget.value) {
    throw new Error('Select an entity and target before saving a decision.')
  }
  await reconciliationStore.updateMapping(props.projectName, selectedEntity.value, selectedTarget.value, request)
}

function openManualLinkDialog(row?: ReconciliationPreviewRow) {
  manualLocalKeyValue.value = row?.local_key_value ?? ''
  manualTargetId.value = ''
  manualNotes.value = ''
  manualLinkError.value = null
  manualLinkDialog.value = true
}

async function saveManualLink() {
  if (!selectedEntity.value) {
    manualLinkError.value = 'Select an entity before adding a manual link.'
    return
  }
  const key = manualLocalKeyValue.value.trim()
  if (!key) {
    manualLinkError.value = 'Enter the encoded business key.'
    return
  }
  const targetText = manualTargetId.value.trim()
  if (!/^[1-9]\d*$/.test(targetText)) {
    manualLinkError.value = 'Enter a positive whole-number target ID.'
    return
  }
  const targetId = Number(targetText)
  if (!Number.isSafeInteger(targetId)) {
    manualLinkError.value = 'The target ID is outside the supported integer range.'
    return
  }

  savingManualLink.value = true
  manualLinkError.value = null
  try {
    await reconciliationStore.putManualMapping(
      props.projectName,
      selectedEntity.value,
      key,
      targetId,
      manualNotes.value.trim() || undefined
    )
    manualLinkDialog.value = false
    resultMessage.value = `Manual link saved for key ${key}; target ID ${targetId} is effective after normalization.`
    resultColor.value = 'success'
    showResultSnackbar.value = true
  } catch (e: any) {
    manualLinkError.value = e.message || 'The manual link could not be saved.'
    resultMessage.value = `Manual link failed: ${manualLinkError.value}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  } finally {
    savingManualLink.value = false
  }
}

async function checkServiceHealth() {
  try {
    serviceStatus.value = await reconciliationStore.checkServiceHealth()
  } catch (error: unknown) {
    console.error('Failed to check reconciliation service health:', error)
    serviceStatus.value = { status: 'offline', error: getApiErrorMessage(error, 'Health check failed.') }
  }

  try {
    manifestResult.value = parseReconciliationManifest(await reconciliationStore.getServiceManifest())
    availableEntityTypes.value =
      manifestResult.value.status === 'valid' ? manifestResult.value.manifest.supportedTypes.length : 0
    if (manifestResult.value.status === 'error') {
      console.error('Failed to validate reconciliation service manifest:', manifestResult.value.error)
    }
  } catch (error: unknown) {
    console.error('Failed to load reconciliation service manifest:', error)
    manifestResult.value = {
      status: 'error',
      error: getApiErrorMessage(error, 'The service manifest could not be loaded.'),
    }
    availableEntityTypes.value = 0
  }
}

async function loadYamlContent() {
  try {
    if (!reconciliationStore.reconciliationConfig) {
      await reconciliationStore.loadEntityResolutionCatalog(props.projectName)
    }
    yamlContent.value = yaml.dump(reconciliationStore.reconciliationConfig, { indent: 2, lineWidth: 120 })
    yamlModified.value = false
    yamlError.value = null
  } catch (e: any) {
    console.error('Failed to load YAML:', e)
    yamlError.value = `Failed to load YAML: ${e.message}`
  }
}

async function reloadYaml() {
  await loadYamlContent()
}

async function saveYaml() {
  savingYaml.value = true
  yamlError.value = null

  try {
    // Parse YAML to validate
    // const parsedConfig = yaml.load(yamlContent.value)

    // Save the config
    await reconciliationStore.saveEntityResolutionCatalogRaw(props.projectName, yamlContent.value)

    // Reload specifications to reflect changes
    await reconciliationStore.loadSpecifications(props.projectName)

    yamlModified.value = false
    resultMessage.value = 'Reconciliation configuration saved successfully'
    resultColor.value = 'success'
    showResultSnackbar.value = true
  } catch (e: any) {
    console.error('Failed to save YAML:', e)
    yamlError.value = `Failed to save: ${e.message}`
    resultMessage.value = `Failed to save YAML: ${e.message}`
    resultColor.value = 'error'
    showResultSnackbar.value = true
  } finally {
    savingYaml.value = false
  }
}

// Load project on mount
onMounted(async () => {
  try {
    console.log('[ReconciliationView] Mounted with project:', props.projectName)

    // Check service health and load manifest
    await checkServiceHealth()

    // Load config and specifications
    await reconciliationStore.loadEntityResolutionCatalog(props.projectName)
    await reconciliationStore.loadSpecifications(props.projectName)

    // Load YAML content
    await loadYamlContent()

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
      await reconciliationStore.loadEntityResolutionCatalog(newProjectName)
      await loadYamlContent()
    }
  }
)

// Watch for tab changes to reload YAML when switching to YAML tab
watch(activeTab, async (newTab) => {
  if (newTab === 'yaml') {
    // Load YAML content if not already loaded or not modified
    if (!yamlContent.value || !yamlModified.value) {
      await loadYamlContent()
    }
  }
})

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

watch(
  [() => props.projectName, selectedEntity],
  async ([projectName, entityName]) => {
    if (!projectName || !entityName) return
    try {
      await reconciliationStore.loadMappingData(projectName, entityName)
    } catch (e) {
      console.error('[ReconciliationView] Failed to load mapping sidecar:', e)
    }
  },
  { immediate: true }
)

// Watch for target changes and load preview data
watch(
  [selectedEntity, selectedTarget],
  async ([newEntity, newTarget]) => {
    autoReconcileResult.value = null
    autoReconcileError.value = null
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
