<template>
  <v-dialog :model-value="modelValue" max-width="900px" persistent @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="text-h6 bg-primary">
        <v-icon start>{{ isNew ? 'mdi-plus' : 'mdi-pencil' }}</v-icon>
        {{ isNew ? 'Add' : 'Edit' }} Reconciliation Specification
      </v-card-title>

      <v-card-text class="pt-6">
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

          <v-divider class="my-6" />

          <!-- Data Source Configuration -->
          <h4 class="text-subtitle-1 mb-4">
            <v-icon start size="small">mdi-database</v-icon>
            Data Source
          </h4>

          <v-select
            v-model="sourceType"
            :items="sourceTypes"
            label="Source Type"
            variant="outlined"
            density="comfortable"
            class="mb-4"
          />

          <v-autocomplete
            v-if="sourceType === 'Other Entity'"
            v-model="otherEntityName"
            :items="availableEntities.filter(e => e !== formData.entity_name)"
            label="Source Entity"
            variant="outlined"
            density="comfortable"
            class="mb-4"
          />

          <v-textarea
            v-if="sourceType === 'SQL Query'"
            v-model="sqlQuery"
            label="SQL Query"
            variant="outlined"
            rows="4"
            class="mb-4"
            hint="Write a custom SQL query to fetch reconciliation data"
          />

          <v-divider class="my-6" />

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

          <v-divider class="my-6" />

          <!-- Property Mappings -->
          <h4 class="text-subtitle-1 mb-4">
            <v-icon start size="small">mdi-link-variant</v-icon>
            Property Mappings
            <v-chip size="x-small" class="ml-2">{{ Object.keys(formData.spec.property_mappings).length }}</v-chip>
          </h4>

          <v-card variant="outlined" class="mb-4">
            <v-card-text v-if="availableProperties.length > 0">
              <v-row v-for="prop in availableProperties" :key="prop" dense>
                <v-col cols="12">
                  <v-text-field
                    v-model="formData.spec.property_mappings[prop]"
                    :label="`${prop} → Source Column`"
                    variant="outlined"
                    density="compact"
                    clearable
                    :hint="`Map service property '${prop}' to a source column`"
                  />
                </v-col>
              </v-row>
            </v-card-text>
            <v-card-text v-else class="text-center text-grey">
              <p>Select a remote type to see available properties</p>
            </v-card-text>
          </v-card>

          <v-divider class="my-6" />

          <!-- Match Thresholds -->
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

// Methods
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

  // TODO: Fetch available properties from reconciliation service
  // For now, use common properties
  availableProperties.value = ['latitude', 'longitude', 'description', 'country', 'region']
  isDirty.value = true
}

function cancel() {
  emit('update:modelValue', false)
  resetForm()
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
    // TODO: Fetch from reconciliation service /reconcile endpoint
    // For now, use common types
    availableRemoteTypes.value = ['site', 'taxon', 'location', 'abundance']
  } catch (error) {
    console.error('Failed to load remote types:', error)
  } finally {
    loadingRemoteTypes.value = false
  }
}

// Watch for specification changes (edit mode)
watch(
  () => props.specification,
  (spec) => {
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

      // Load properties for remote type
      if (spec.remote.service_type) {
        onRemoteTypeChange(spec.remote.service_type)
      }
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

onMounted(() => {
  loadAvailableEntities()
  loadRemoteTypes()
})
</script>

<style scoped>
:deep(.v-slider) {
  margin-top: 8px;
}
</style>
