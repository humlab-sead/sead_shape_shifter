<template>
  <v-dialog :model-value="modelValue" max-width="900px" persistent scrollable @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-toolbar color="primary" density="compact">
        <v-toolbar-title>
          <v-icon :icon="isNew ? 'mdi-plus-circle' : 'mdi-pencil'" class="mr-2" />
          {{ isNew ? 'Add' : 'Edit' }} Reconciliation Specification
        </v-toolbar-title>
      </v-toolbar>

      <v-tabs v-model="activeTab" bg-color="primary">
        <v-tab value="form">Form</v-tab>
        <v-tab value="yaml" :disabled="isNew">
          <v-icon icon="mdi-code-braces" class="mr-1" size="small" />
          YAML
        </v-tab>
      </v-tabs>

      <v-card-text class="pt-6">
        <!-- Validation Errors Alert -->
        <v-alert
          v-if="!isNew && validationErrors.length > 0"
          type="error"
          variant="tonal"
          class="mb-4"
        >
          <v-alert-title class="d-flex align-center">
            <v-icon start>mdi-alert-circle</v-icon>
            Configuration Issues Detected
          </v-alert-title>
          <ul class="mt-2">
            <li v-for="(error, idx) in validationErrors" :key="idx">{{ error }}</li>
          </ul>
          <div class="text-caption mt-2">
            Please fix these issues before the specification can be used.
          </div>
        </v-alert>

        <!-- Validation Warnings Alert -->
        <v-alert
          v-if="!isNew && validationWarnings.length > 0"
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          <v-alert-title class="d-flex align-center">
            <v-icon start>mdi-alert</v-icon>
            Configuration Warnings
          </v-alert-title>
          <ul class="mt-2">
            <li v-for="(warning, idx) in validationWarnings" :key="idx">{{ warning }}</li>
          </ul>
        </v-alert>

        <v-window v-model="activeTab">
          <v-window-item value="form">
            <v-form ref="form" v-model="valid">
          <!-- Entity and Target Field Selection (only for new) -->
          <template v-if="isNew">
            <v-row>
              <v-col cols="6">
                <v-autocomplete
                  v-model="formData.entity_name"
                  :items="availableEntities"
                  label="Entity *"
                  variant="outlined"
                  density="comfortable"
                  :rules="[required]"
                  prepend-inner-icon="mdi-table"
                  @update:model-value="onEntityChange"
                >
                  <template #no-data>
                    <v-list-item>
                      <v-list-item-title class="text-grey">No entities available</v-list-item-title>
                    </v-list-item>
                  </template>
                </v-autocomplete>
              </v-col>

              <v-col cols="6">
                <v-autocomplete
                  v-model="formData.target_field"
                  :items="availableFields"
                  label="Target Field *"
                  variant="outlined"
                  density="comfortable"
                  :rules="[required, uniqueTargetField]"
                  :loading="loadingFields"
                  :disabled="!formData.entity_name"
                  prepend-inner-icon="mdi-target"
                >
                  <template #no-data>
                    <v-list-item>
                      <v-list-item-title class="text-grey">
                        {{ formData.entity_name ? 'No fields available' : 'Select an entity first' }}
                      </v-list-item-title>
                    </v-list-item>
                  </template>
                </v-autocomplete>
              </v-col>
            </v-row>
          </template>

          <!-- Read-only for existing -->
          <v-text-field
            v-else
            :model-value="`${specification?.entity_name} → ${specification?.target_field}`"
            label="Entity → Target Field"
            variant="outlined"
            density="comfortable"
            readonly
            prepend-inner-icon="mdi-lock"
          />

          <!-- Data Source Configuration -->
          <h4 class="text-subtitle-1 mb-4">
            <v-icon start size="small">mdi-database</v-icon>
            Data Source
          </h4>

          <v-row>
            <v-col cols="6">
              <v-select
                v-model="sourceType"
                :items="sourceTypes"
                label="Source Type"
                variant="outlined"
                density="comfortable"
              />
            </v-col>
            <v-col cols="6">
              <v-autocomplete
                v-if="sourceType === 'Other Entity'"
                v-model="otherEntityName"
                :items="availableEntities.filter(e => e !== formData.entity_name)"
                label="Source Entity"
                variant="outlined"
                density="comfortable"
              />
            </v-col>
          </v-row>

          <v-textarea
            v-if="sourceType === 'SQL Query'"
            v-model="sqlQuery"
            label="SQL Query"
            variant="outlined"
            rows="4"
            class="mb-4"
            hint="Write a custom SQL query to fetch reconciliation data"
          />

          <!-- Remote Configuration -->
          <h4 class="text-subtitle-1 mb-4">
            <v-icon start size="small">mdi-cloud</v-icon>
            Remote Entity Configuration
          </h4>

          <v-autocomplete
            v-model="formData.spec.remote.service_type"
            :items="availableRemoteTypes"
            label="Remote Type *"
            variant="outlined"
            density="comfortable"
            :rules="[required]"
            :loading="loadingRemoteTypes"
            clearable
            @update:model-value="onRemoteTypeChange"
          >
            <template #no-data>
              <v-list-item>
                <v-list-item-title class="text-grey">No remote types available</v-list-item-title>
                <v-list-item-subtitle>Check reconciliation service status</v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-autocomplete>

          <!-- Property Mappings -->
          <h4 class="text-subtitle-1 mb-4">
            <v-icon start size="small">mdi-link-variant</v-icon>
            Property Mappings
            <v-chip size="x-small" class="ml-2">{{ Object.keys(formData.spec.property_mappings).length }}</v-chip>
          </h4>

          <v-card variant="flat" class="mb-4">
            <v-card-text v-if="availableProperties.length > 0">
              <v-row v-for="prop in availableProperties" :key="prop" dense>
                <v-col cols="12">
                  <v-autocomplete
                    :model-value="formData.spec.property_mappings[prop]"
                    :items="availableFields"
                    :label="prop"
                    variant="outlined"
                    density="compact"
                    clearable
                    :hint="`Map property '${prop}' to a source column`"
                    persistent-hint
                    :error="!isNew && isMissingColumn(formData.spec.property_mappings[prop])"
                    :error-messages="!isNew && isMissingColumn(formData.spec.property_mappings[prop]) ? `Column '${formData.spec.property_mappings[prop]}' not found in entity` : undefined"
                    :loading="loadingFields"
                    :disabled="availableFields.length === 0"
                    @update:model-value="(value) => updatePropertyMapping(prop, value)"
                  >
                    <template #prepend-inner>
                      <v-icon size="small" :color="!isNew && isMissingColumn(formData.spec.property_mappings[prop]) ? 'error' : 'primary'">mdi-arrow-left</v-icon>
                    </template>
                    <template #no-data>
                      <v-list-item>
                        <v-list-item-title class="text-grey">
                          {{ formData.entity_name ? 'No columns available' : 'Select an entity first' }}
                        </v-list-item-title>
                      </v-list-item>
                    </template>
                  </v-autocomplete>
                </v-col>
              </v-row>
            </v-card-text>
            <v-card-text v-else class="text-center text-grey">
              <p>Select a remote type to see available properties</p>
            </v-card-text>
          </v-card>

          <h4 class="text-subtitle-1 mb-4">
            <v-icon start size="small">mdi-tune</v-icon>
            Match Thresholds
          </h4>

          <v-row>
            <v-col cols="6">
              <v-slider
                v-model="formData.spec.auto_accept_threshold"
                label="Auto-accept Threshold"
                :min="0"
                :max="1"
                :step="0.05"
                thumb-label="always"
                color="success"
              >
                <template #append>
                  <v-text-field
                    :model-value="(formData.spec.auto_accept_threshold * 100).toFixed(0) + '%'"
                    density="compact"
                    style="width: 70px"
                    readonly
                    hide-details
                  />
                </template>
              </v-slider>
            </v-col>
            <v-col cols="6">
              <v-slider
                v-model="formData.spec.review_threshold"
                label="Review Threshold"
                :min="0"
                :max="1"
                :step="0.05"
                thumb-label="always"
                color="warning"
              >
                <template #append>
                  <v-text-field
                    :model-value="(formData.spec.review_threshold * 100).toFixed(0) + '%'"
                    density="compact"
                    style="width: 70px"
                    readonly
                    hide-details
                  />
                </template>
              </v-slider>
            </v-col>
          </v-row>
            </v-form>
          </v-window-item>

          <v-window-item value="yaml">
            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              <div class="text-caption">
                <v-icon icon="mdi-information" size="small" class="mr-1" />
                Edit the reconciliation specification in YAML format. Changes will be synced with the form editor.
              </div>
            </v-alert>

            <yaml-editor
              v-model="yamlContent"
              height="500px"
              :validate-on-change="true"
              @validate="handleYamlValidation"
              @change="handleYamlChange"
            />

            <v-alert v-if="yamlError" type="error" density="compact" variant="tonal" class="mt-2">
              {{ yamlError }}
            </v-alert>
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn @click="cancel">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          :disabled="!valid || !isDirty"
          :loading="saving"
          @click="save"
        >
          {{ isNew ? 'Create' : 'Save' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useReconciliationStore } from '@/stores/reconciliation'
import { useProjectStore } from '@/stores/project'
import type {
  SpecificationListItem,
  EntityReconciliationSpec,
  ReconciliationSource,
} from '@/types/reconciliation'
import * as yaml from 'js-yaml'
import YamlEditor from '../common/YamlEditor.vue'

interface Props {
  modelValue: boolean
  projectName: string
  specification?: SpecificationListItem | null
  isNew: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const reconciliationStore = useReconciliationStore()
const projectStore = useProjectStore()

// State
const form = ref<any>(null)
const valid = ref(false)
const saving = ref(false)
const loadingFields = ref(false)
const loadingRemoteTypes = ref(false)
const availableEntities = ref<string[]>([])
const availableFields = ref<string[]>([])
const availableRemoteTypes = ref<string[]>([])
const availableProperties = ref<string[]>([])
const isDirty = ref(false)
const validationErrors = ref<string[]>([])
const validationWarnings = ref<string[]>([])
const activeTab = ref('form')
const yamlContent = ref('')
const yamlError = ref<string | null>(null)
const yamlValid = ref(true)

// Source type selection
const sourceTypes = ['Entity Preview', 'Other Entity', 'SQL Query']
const sourceType = ref('Entity Preview')
const otherEntityName = ref<string>('')
const sqlQuery = ref('')

// Form data
const formData = ref<{
  entity_name: string
  target_field: string
  spec: EntityReconciliationSpec
}>({
  entity_name: '',
  target_field: '',
  spec: {
    source: null,
    property_mappings: {},
    remote: {
      service_type: null,
    },
    auto_accept_threshold: 0.95,
    review_threshold: 0.70,
    mapping: [],
  },
})

// Validation rules
const required = (v: any) => !!v || 'Required'

const uniqueTargetField = (v: string) => {
  if (!props.isNew) return true
  const existing = reconciliationStore.specifications.find(
    (s) => s.entity_name === formData.value.entity_name && s.target_field === v
  )
  return !existing || 'This entity + target field combination already exists'
}

// Validation methods
async function validateSpecification() {
  validationErrors.value = []
  validationWarnings.value = []

  if (props.isNew) return

  // If source is a SQL query, we can't validate columns (they're defined in the query)
  if (formData.value.spec.source && typeof formData.value.spec.source === 'object') {
    // SQL query source - skip column validation
    if (!formData.value.spec.remote?.service_type) {
      validationWarnings.value.push('No remote service type configured')
    }
    return
  }

  // Determine which entity to validate against
  let entityForValidation = formData.value.entity_name
  if (formData.value.spec.source && typeof formData.value.spec.source === 'string') {
    entityForValidation = formData.value.spec.source
  }

  // Get actual available fields from API (includes keys, columns, extra_columns, FK joins, unnest)
  let entityColumns: string[] = []
  try {
    entityColumns = await reconciliationStore.getAvailableFields(props.projectName, entityForValidation)
  } catch (error) {
    validationErrors.value.push(
      `Entity '${entityForValidation}' not found or has no columns`
    )
    return
  }

  if (entityColumns.length === 0) {
    validationErrors.value.push(
      `Entity '${entityForValidation}' not found or has no columns`
    )
    return
  }

  // Check if target field exists
  if (!entityColumns.includes(formData.value.target_field)) {
    validationErrors.value.push(
      `Target field '${formData.value.target_field}' not found in entity '${entityForValidation}'`
    )
  }

  // Check if property mapping source columns exist
  const missingColumns: string[] = []
  Object.entries(formData.value.spec.property_mappings).forEach(([prop, sourceCol]) => {
    if (sourceCol && !entityColumns.includes(sourceCol)) {
      missingColumns.push(`${prop} → ${sourceCol}`)
    }
  })

  if (missingColumns.length > 0) {
    validationErrors.value.push(
      `Property mappings reference missing columns: ${missingColumns.join(', ')}`
    )
  }
}

function isMissingColumn(columnName: string | undefined): boolean {
  if (!columnName || props.isNew) return false
  
  // Check against availableFields (includes keys, columns, extra_columns, FK joins, unnest)
  // This is the same source used to populate the dropdown
  if (availableFields.value.length === 0) {
    // Fields not loaded yet, don't show error
    return false
  }

  return !availableFields.value.includes(columnName)
}

// Methods
function updatePropertyMapping(property: string, value: string | null) {
  // Ensure reactive update by creating a new object
  formData.value.spec.property_mappings = {
    ...formData.value.spec.property_mappings,
    [property]: value || ''
  }
}

async function onEntityChange(entityName: string) {
  if (!entityName) {
    availableFields.value = []
    return
  }

  loadingFields.value = true
  try {
    availableFields.value = await reconciliationStore.getAvailableFields(props.projectName, entityName)
  } catch (error) {
    console.error('Failed to load available fields:', error)
    availableFields.value = []
  } finally {
    loadingFields.value = false
  }
}

async function onRemoteTypeChange(remoteType: string | null) {
  if (!remoteType) {
    availableProperties.value = []
    return
  }

  // If we have existing property_mappings (editing mode), use those keys
  const existingProps = Object.keys(formData.value.spec.property_mappings)
  if (existingProps.length > 0) {
    availableProperties.value = existingProps
  } else {
    // TODO: Fetch available properties from reconciliation service manifest
    // For now, use type-specific defaults
    const propertyDefaults: Record<string, string[]> = {
      site: ['latitude', 'longitude', 'description', 'country', 'region'],
      taxon: ['rank', 'kingdom', 'family'],
      location: ['latitude', 'longitude', 'country'],
      abundance: ['value', 'unit'],
    }
    availableProperties.value = propertyDefaults[remoteType.toLowerCase()] || []
  }
  
  isDirty.value = true
}

function cancel() {
  emit('update:modelValue', false)
  resetForm()
  validationErrors.value = []
  validationWarnings.value = []
}

async function save() {
  if (!form.value?.validate()) return

  saving.value = true
  try {
    // Prepare source based on source type
    let source: string | ReconciliationSource | null = null
    if (sourceType.value === 'Other Entity') {
      source = otherEntityName.value
    } else if (sourceType.value === 'SQL Query') {
      source = {
        data_source: 'default',
        type: 'sql',
        query: sqlQuery.value,
      }
    }
    formData.value.spec.source = source

    if (props.isNew) {
      await reconciliationStore.createSpecification(props.projectName, {
        entity_name: formData.value.entity_name,
        target_field: formData.value.target_field,
        spec: formData.value.spec,
      })
    } else {
      await reconciliationStore.updateSpecification(
        props.projectName,
        formData.value.entity_name,
        formData.value.target_field,
        {
          source: formData.value.spec.source,
          property_mappings: formData.value.spec.property_mappings,
          remote: formData.value.spec.remote,
          auto_accept_threshold: formData.value.spec.auto_accept_threshold,
          review_threshold: formData.value.spec.review_threshold,
        }
      )
    }

    emit('saved')
    resetForm()
  } catch (error) {
    console.error('Failed to save specification:', error)
  } finally {
    saving.value = false
  }
}

function resetForm() {
  formData.value = {
    entity_name: '',
    target_field: '',
    spec: {
      source: null,
      property_mappings: {},
      remote: {
        service_type: null,
      },
      auto_accept_threshold: 0.95,
      review_threshold: 0.70,
      mapping: [],
    },
  }
  sourceType.value = 'Entity Preview'
  otherEntityName.value = ''
  sqlQuery.value = ''
  isDirty.value = false
  form.value?.resetValidation()
}

// Load available entities from project
async function loadAvailableEntities() {
  try {
    const project = projectStore.selectedProject
    if (project?.entities) {
      availableEntities.value = Object.keys(project.entities)
    }
  } catch (error) {
    console.error('Failed to load available entities:', error)
  }
}

// Load available remote types (TODO: from reconciliation service manifest)
async function loadRemoteTypes() {
  loadingRemoteTypes.value = true
  try {
    // Fetch from reconciliation service /reconcile endpoint
    const manifest = await reconciliationStore.getServiceManifest()
    
    // Extract entity types from manifest
    // OpenRefine manifest has defaultTypes array with {id, name} objects
    if (manifest.defaultTypes && Array.isArray(manifest.defaultTypes)) {
      availableRemoteTypes.value = manifest.defaultTypes.map((type: any) => type.id)
      console.log(`[SpecificationEditor] Loaded ${availableRemoteTypes.value.length} entity types from service:`, availableRemoteTypes.value)
    } else {
      console.warn('[SpecificationEditor] No defaultTypes found in manifest, using fallback')
      // Fallback to common types if manifest doesn't have them
      availableRemoteTypes.value = ['site', 'taxon', 'location', 'abundance']
    }
  } catch (error) {
    console.error('Failed to load remote types:', error)
    // Fallback to common types on error
    availableRemoteTypes.value = ['site', 'taxon', 'location', 'abundance']
  } finally {
    loadingRemoteTypes.value = false
  }
}

// Watch for specification changes (edit mode)
watch(
  () => props.specification,
  async (spec) => {
    if (spec && !props.isNew) {
      formData.value = {
        entity_name: spec.entity_name,
        target_field: spec.target_field,
        spec: {
          source: spec.source,
          property_mappings: { ...spec.property_mappings },
          remote: { ...spec.remote },
          auto_accept_threshold: spec.auto_accept_threshold,
          review_threshold: spec.review_threshold,
          mapping: [],
        },
      }

      // Set source type
      if (!spec.source) {
        sourceType.value = 'Entity Preview'
      } else if (typeof spec.source === 'string') {
        sourceType.value = 'Other Entity'
        otherEntityName.value = spec.source
      } else {
        sourceType.value = 'SQL Query'
        sqlQuery.value = spec.source.query
      }

      // Load available fields for the entity
      const entityForFields = (typeof spec.source === 'string') ? spec.source : spec.entity_name
      try {
        loadingFields.value = true
        availableFields.value = await reconciliationStore.getAvailableFields(props.projectName, entityForFields)
      } catch (error) {
        console.error('Failed to load available fields:', error)
        availableFields.value = []
      } finally {
        loadingFields.value = false
      }

      // Load properties for remote type
      if (spec.remote.service_type) {
        onRemoteTypeChange(spec.remote.service_type)
      }

      // Validate the loaded specification
      validateSpecification()
    }
  },
  { immediate: true }
)

// Watch for dialog open
watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      loadAvailableEntities()
      loadRemoteTypes()
      if (props.isNew) {
        resetForm()
      }
    }
  }
)

// Track changes for dirty state
watch(formData, () => {
  isDirty.value = true
}, { deep: true })

// Watch for tab changes to sync YAML
watch(activeTab, (newTab) => {
  if (newTab === 'yaml' && !props.isNew) {
    yamlContent.value = formDataToYaml()
  }
})

// Watch for source type or other entity changes to update available fields
watch([sourceType, otherEntityName], async ([newSourceType, newOtherEntity]) => {
  if (!formData.value.entity_name) return

  let entityForFields = formData.value.entity_name
  
  // Determine which entity's fields to load
  if (newSourceType === 'Other Entity' && newOtherEntity) {
    entityForFields = newOtherEntity
  }
  // For 'SQL Query' we can't pre-load fields (custom query)
  // For 'Entity Preview' use the main entity

  if (newSourceType !== 'SQL Query') {
    try {
      loadingFields.value = true
      availableFields.value = await reconciliationStore.getAvailableFields(props.projectName, entityForFields)
    } catch (error) {
      console.error('Failed to load available fields:', error)
      availableFields.value = []
    } finally {
      loadingFields.value = false
    }
  } else {
    // SQL Query - no predefined fields
    availableFields.value = []
  }
  
  // Re-validate after fields change
  if (!props.isNew) {
    await validateSpecification()
  }
})

// Watch for property mappings changes to re-validate
watch(() => formData.value.spec.property_mappings, async () => {
  if (!props.isNew && availableFields.value.length > 0) {
    await validateSpecification()
  }
}, { deep: true })

// Watch for remote type changes to re-validate
watch(() => formData.value.spec.remote?.service_type, async () => {
  if (!props.isNew) {
    await validateSpecification()
  }
})


// YAML Editor Functions
function formDataToYaml(): string {
  const specData: Record<string, any> = {}

  // Build source
  if (sourceType.value === 'Other Entity') {
    specData.source = otherEntityName.value
  } else if (sourceType.value === 'SQL Query') {
    specData.source = { query: sqlQuery.value }
  }
  // Entity Preview = null (default)

  // Add property mappings (only non-empty ones)
  const mappings: Record<string, string> = {}
  for (const [key, value] of Object.entries(formData.value.spec.property_mappings)) {
    if (value) {
      mappings[key] = value
    }
  }
  if (Object.keys(mappings).length > 0) {
    specData.property_mappings = mappings
  }

  // Add remote configuration
  specData.remote = {
    service_type: formData.value.spec.remote.service_type,
  }

  // Add thresholds
  specData.auto_accept_threshold = formData.value.spec.auto_accept_threshold
  specData.review_threshold = formData.value.spec.review_threshold

  return yaml.dump(specData, { indent: 2, lineWidth: 120, noRefs: true })
}

function yamlToFormData(yamlString: string): boolean {
  try {
    const parsed = yaml.load(yamlString) as any

    if (!parsed || typeof parsed !== 'object') {
      yamlError.value = 'Invalid YAML: Expected an object'
      return false
    }

    // Update source type and value
    if (!parsed.source) {
      sourceType.value = 'Entity Preview'
    } else if (typeof parsed.source === 'string') {
      sourceType.value = 'Other Entity'
      otherEntityName.value = parsed.source
    } else if (parsed.source && typeof parsed.source === 'object' && parsed.source.query) {
      sourceType.value = 'SQL Query'
      sqlQuery.value = parsed.source.query
    }

    // Update property mappings
    if (parsed.property_mappings && typeof parsed.property_mappings === 'object') {
      formData.value.spec.property_mappings = { ...parsed.property_mappings }
    }

    // Update remote configuration
    if (parsed.remote && typeof parsed.remote === 'object') {
      formData.value.spec.remote = { ...parsed.remote }
      if (parsed.remote.service_type) {
        onRemoteTypeChange(parsed.remote.service_type)
      }
    }

    // Update thresholds
    if (typeof parsed.auto_accept_threshold === 'number') {
      formData.value.spec.auto_accept_threshold = parsed.auto_accept_threshold
    }
    if (typeof parsed.review_threshold === 'number') {
      formData.value.spec.review_threshold = parsed.review_threshold
    }

    yamlError.value = null
    return true
  } catch (e: any) {
    yamlError.value = `YAML parse error: ${e.message}`
    return false
  }
}

function handleYamlValidation(isValid: boolean) {
  yamlValid.value = isValid
}

function handleYamlChange(newYaml: string) {
  if (yamlValid.value) {
    yamlToFormData(newYaml)
  }
}

onMounted(() => {
  loadAvailableEntities()
  loadRemoteTypes()
})
</script>

<style scoped>
:deep(.v-slider) {
  margin-top: 8px;
}

/* Make hint text more subdued */
:deep(.v-messages__message) {
  opacity: 0.5;
  color: rgb(var(--v-theme-on-surface));
}

/* Make placeholder text in empty fields dimmer */
:deep(.v-field--variant-outlined input::placeholder),
:deep(.v-field--variant-outlined .v-select__selection-text),
:deep(.v-autocomplete input::placeholder) {
  opacity: 0.4;
  color: rgb(var(--v-theme-on-surface));
}
</style>
