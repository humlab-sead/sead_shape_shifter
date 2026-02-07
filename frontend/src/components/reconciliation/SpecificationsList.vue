<template>
  <div class="specifications-list">
    <v-card variant="outlined">
      <v-card-title class="d-flex align-center justify-space-between">
        <span>Reconciliation Specifications</span>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openAddDialog">
          Add Specification
        </v-btn>
      </v-card-title>

      <v-card-text>
        <!-- Loading State -->
        <div v-if="loadingSpecs" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" />
          <p class="text-grey mt-4">Loading specifications...</p>
        </div>

        <!-- Error State -->
        <v-alert v-else-if="specsError" type="error" variant="tonal" class="mb-4">
          {{ specsError }}
        </v-alert>

        <!-- Empty State -->
        <v-alert v-else-if="specifications.length === 0" type="info" variant="tonal" class="mb-4">
          <div class="d-flex align-center">
            <v-icon start>mdi-information</v-icon>
            <div>
              <div class="font-weight-bold">No specifications configured</div>
              <div class="text-caption">Add your first reconciliation specification to get started</div>
            </div>
          </div>
        </v-alert>

        <!-- Data Table -->
        <v-data-table
          v-else
          :headers="headers"
          :items="specifications"
          :items-per-page="10"
          class="elevation-0"
          hover
        >
          <!-- Status Column -->
          <template #item.status="{ item }">
            <v-tooltip location="right">
              <template #activator="{ props: tooltipProps }">
                <v-icon
                  v-if="getValidationStatus(item).hasErrors"
                  v-bind="tooltipProps"
                  color="error"
                  size="small"
                >
                  mdi-alert-circle
                </v-icon>
                <v-icon
                  v-else-if="getValidationStatus(item).hasWarnings"
                  v-bind="tooltipProps"
                  color="warning"
                  size="small"
                >
                  mdi-alert
                </v-icon>
                <v-icon
                  v-else
                  v-bind="tooltipProps"
                  color="success"
                  size="small"
                >
                  mdi-check-circle
                </v-icon>
              </template>
              <div v-if="getValidationStatus(item).hasErrors" class="pa-2">
                <div class="font-weight-bold mb-2">Configuration Errors:</div>
                <ul class="ml-4">
                  <li v-for="(error, idx) in getValidationStatus(item).errors" :key="idx" class="text-caption">
                    {{ error }}
                  </li>
                </ul>
              </div>
              <div v-else-if="getValidationStatus(item).hasWarnings" class="pa-2">
                <div class="font-weight-bold mb-2">Configuration Warnings:</div>
                <ul class="ml-4">
                  <li v-for="(warning, idx) in getValidationStatus(item).warnings" :key="idx" class="text-caption">
                    {{ warning }}
                  </li>
                </ul>
              </div>
              <div v-else class="pa-2">
                <div class="font-weight-bold">Valid Configuration</div>
                <div class="text-caption">No issues detected</div>
              </div>
            </v-tooltip>
          </template>

          <!-- Entity Name Column -->
          <template #item.entity_name="{ item }">
            <div class="d-flex align-center">
              <v-icon start size="small">mdi-table</v-icon>
              <span class="font-weight-medium">{{ item.entity_name }}</span>
            </div>
          </template>

          <!-- Target Field Column -->
          <template #item.target_field="{ item }">
            <v-chip size="small" variant="tonal" color="primary">
              <v-icon start size="x-small">mdi-target</v-icon>
              {{ item.target_field }}
            </v-chip>
          </template>

          <!-- Remote Type Column -->
          <template #item.remote="{ item }">
            <v-chip
              v-if="item.remote.service_type"
              size="small"
              :color="isRemoteTypeValid(item) ? 'success' : 'warning'"
              variant="tonal"
            >
              {{ item.remote.service_type }}
            </v-chip>
            <v-chip v-else size="small" color="grey" variant="tonal">
              <v-icon start size="x-small">mdi-minus-circle</v-icon>
              Disabled
            </v-chip>
          </template>

          <!-- Mappings Column -->
          <template #item.mapping_count="{ item }">
            <v-chip
              size="small"
              :color="item.mapping_count > 0 ? 'info' : 'default'"
              variant="tonal"
            >
              <v-icon start size="x-small">mdi-link-variant</v-icon>
              {{ item.mapping_count }}
            </v-chip>
          </template>

          <!-- Thresholds Column -->
          <template #item.thresholds="{ item }">
            <div class="text-caption">
              <div>Auto: {{ (item.auto_accept_threshold * 100).toFixed(0) }}%</div>
              <div>Review: {{ (item.review_threshold * 100).toFixed(0) }}%</div>
            </div>
          </template>

          <!-- Actions Column -->
          <template #item.actions="{ item }">
            <div class="d-flex gap-1">
              <v-tooltip text="Reconcile this entity" location="top">
                <template #activator="{ props }">
                  <v-btn
                    icon="mdi-auto-fix"
                    size="small"
                    variant="text"
                    color="primary"
                    v-bind="props"
                    @click.stop="reconcileSpec(item)"
                  />
                </template>
              </v-tooltip>

              <v-tooltip text="Edit specification" location="top">
                <template #activator="{ props }">
                  <v-btn
                    icon="mdi-pencil"
                    size="small"
                    variant="text"
                    v-bind="props"
                    @click.stop="editSpecification(item)"
                  />
                </template>
              </v-tooltip>

              <v-tooltip text="Delete specification" location="top">
                <template #activator="{ props }">
                  <v-btn
                    icon="mdi-delete"
                    size="small"
                    variant="text"
                    color="error"
                    v-bind="props"
                    @click.stop="confirmDelete(item)"
                  />
                </template>
              </v-tooltip>
            </div>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Specification Editor Dialog -->
    <SpecificationEditor
      v-model="editorDialog"
      :project-name="projectName"
      :specification="selectedSpec"
      :is-new="isNewSpec"
      @saved="handleSpecSaved"
    />

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="500">
      <v-card>
        <v-card-title class="text-h6">
          <v-icon start color="warning">mdi-alert</v-icon>
          Delete Specification?
        </v-card-title>

        <v-card-text>
          <p>
            Are you sure you want to delete the specification for
            <strong>{{ specToDelete?.entity_name }}.{{ specToDelete?.target_field }}</strong>?
          </p>

          <v-alert v-if="specToDelete && specToDelete.mapping_count > 0" type="warning" variant="tonal" class="mt-4">
            <div class="font-weight-bold">Warning: This specification has {{ specToDelete.mapping_count }} existing mappings</div>
            <div class="text-caption mt-1">All mappings will be permanently deleted.</div>
          </v-alert>

          <p v-else class="text-caption text-grey mt-4">This action cannot be undone.</p>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn
            color="error"
            variant="elevated"
            :loading="deletingSpec"
            @click="performDelete"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useReconciliationStore } from '@/stores/reconciliation'
import { useProjectStore } from '@/stores/project'
import type { EntityMappingListItem } from '@/types/reconciliation'
import SpecificationEditor from './SpecificationEditor.vue'

interface Props {
  projectName: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  reconcile: [entityName: string, targetField: string]
}>()

const reconciliationStore = useReconciliationStore()
const { specifications, loadingSpecs, specsError } = storeToRefs(reconciliationStore)
const projectStore = useProjectStore()

// State
const editorDialog = ref(false)
const deleteDialog = ref(false)
const selectedSpec = ref<EntityMappingListItem | null>(null)
const specToDelete = ref<EntityMappingListItem | null>(null)
const isNewSpec = ref(false)
const deletingSpec = ref(false)
const entityFieldsCache = ref<Record<string, string[]>>({}) // Cache for entity fields from API
const validationCache = ref<Record<string, ValidationStatus>>({}) // Cache for validation results
const validationLoading = ref(false)

// Table headers
const headers = [
  { title: 'Status', key: 'status', sortable: false, width: '80' },
  { title: 'Entity', key: 'entity_name', sortable: true },
  { title: 'Target Field', key: 'target_field', sortable: true },
  { title: 'Remote Type', key: 'remote', sortable: false },
  { title: 'Mappings', key: 'mapping_count', sortable: true },
  { title: 'Thresholds', key: 'thresholds', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' as const },
]

// Methods
function isRemoteTypeValid(item: EntityMappingListItem): boolean {
  // TODO: Validate against available remote types from service
  return item.remote.service_type != null
}

function openAddDialog() {
  selectedSpec.value = null
  isNewSpec.value = true
  editorDialog.value = true
}

function editSpecification(item: EntityMappingListItem) {
  selectedSpec.value = item
  isNewSpec.value = false
  editorDialog.value = true
}

function reconcileSpec(item: EntityMappingListItem) {
  emit('reconcile', item.entity_name, item.target_field)
}

function confirmDelete(item: EntityMappingListItem) {
  specToDelete.value = item
  deleteDialog.value = true
}

async function performDelete() {
  if (!specToDelete.value) return

  deletingSpec.value = true
  try {
    await reconciliationStore.deleteSpecification(
      props.projectName,
      specToDelete.value.entity_name,
      specToDelete.value.target_field,
      true // force delete even with mappings
    )
    deleteDialog.value = false
    specToDelete.value = null
  } catch (error) {
    console.error('Failed to delete specification:', error)
  } finally {
    deletingSpec.value = false
  }
}

async function handleSpecSaved() {
  editorDialog.value = false
  selectedSpec.value = null
  // List is automatically reloaded by store actions
}

// Validation
interface ValidationStatus {
  hasErrors: boolean
  hasWarnings: boolean
  errors: string[]
  warnings: string[]
}

async function getEntityFields(entityName: string): Promise<string[]> {
  // Return cached if available
  if (entityFieldsCache.value[entityName]) {
    return entityFieldsCache.value[entityName]
  }

  try {
    // Fetch from API - this gets actual available fields including:
    // 1. Keys
    // 2. Columns (excluding value_vars if unnest)
    // 3. Extra columns
    // 4. FK join columns
    // 5. var_name & value_name from unnest
    const fields = await reconciliationStore.getAvailableFields(props.projectName, entityName)
    entityFieldsCache.value[entityName] = fields
    return fields
  } catch (error) {
    console.error(`Failed to fetch fields for entity '${entityName}':`, error)
    // Fallback to empty array - will be treated as error
    return []
  }
}

async function validateSpecification(spec: EntityMappingListItem): Promise<ValidationStatus> {
  const status: ValidationStatus = {
    hasErrors: false,
    hasWarnings: false,
    errors: [],
    warnings: []
  }

  // Determine which entity to validate against
  let entityForValidation = spec.entity_name

  // Check if using "Other Entity" as source
  if (spec.source && typeof spec.source === 'string') {
    entityForValidation = spec.source
  }

  // Get actual available fields from API (includes all column types)
  const entityColumns = await getEntityFields(entityForValidation)
  
  if (entityColumns.length === 0) {
    status.hasErrors = true
    status.errors.push(`Entity '${entityForValidation}' not found or has no columns`)
    return status
  }

  // Check if target field exists
  if (!entityColumns.includes(spec.target_field)) {
    status.hasErrors = true
    status.errors.push(`Target field '${spec.target_field}' not found in entity '${entityForValidation}'`)
  }

  // Check if property mapping source columns exist
  const missingColumns: string[] = []
  Object.entries(spec.property_mappings || {}).forEach(([prop, sourceCol]) => {
    if (sourceCol && !entityColumns.includes(sourceCol)) {
      missingColumns.push(`${prop} → ${sourceCol}`)
    }
  })

  if (missingColumns.length > 0) {
    status.hasErrors = true
    status.errors.push(`Missing columns in mappings: ${missingColumns.join(', ')}`)
  }

  // Check if remote type is configured
  if (!spec.remote?.service_type) {
    status.hasWarnings = true
    status.warnings.push('No remote service type configured')
  }

  return status
}

function getValidationStatus(spec: EntityMappingListItem): ValidationStatus {
  const cacheKey = `${spec.entity_name}.${spec.target_field}`
  
  // Return cached if available
  if (validationCache.value[cacheKey]) {
    return validationCache.value[cacheKey]
  }

  // Return pending status if not yet validated
  return {
    hasErrors: false,
    hasWarnings: false,
    errors: [],
    warnings: []
  }
}

async function validateAllSpecifications() {
  if (!specifications.value.length) return
  
  validationLoading.value = true
  
  try {
    // Validate all specifications in parallel
    await Promise.all(
      specifications.value.map(async (spec) => {
        const cacheKey = `${spec.entity_name}.${spec.target_field}`
        const status = await validateSpecification(spec)
        validationCache.value[cacheKey] = status
      })
    )
  } catch (error) {
    console.error('Failed to validate specifications:', error)
  } finally {
    validationLoading.value = false
  }
}

// Lifecycle
onMounted(async () => {
  if (props.projectName) {
    await reconciliationStore.loadSpecifications(props.projectName)
    // Validate all specifications after loading
    await validateAllSpecifications()
  }
})

// Watch for specification changes and revalidate
watch(specifications, async () => {
  await validateAllSpecifications()
}, { deep: true })

</script>

<style scoped>
.specifications-list {
  width: 100%;
}

.gap-1 {
  gap: 4px;
}

.gap-2 {
  gap: 8px;
}
</style>
