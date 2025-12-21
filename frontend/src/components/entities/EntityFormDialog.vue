<template>
  <v-dialog v-model="dialogModel" max-width="900" persistent scrollable>
    <v-card>
      <v-card-title class="d-flex align-center" style="overflow: visible;">
        <v-icon :icon="mode === 'create' ? 'mdi-plus-circle' : 'mdi-pencil'" class="mr-2" />
        <span class="text-truncate" :title="mode === 'create' ? 'Create Entity' : `Edit ${entity?.name}`">
          {{ mode === 'create' ? 'Create Entity' : `Edit ${entity?.name}` }}
        </span>
      </v-card-title>

      <v-tabs v-model="activeTab" bg-color="primary">
        <v-tab value="basic">Basic</v-tab>
        <v-tab value="relationships" :disabled="mode === 'create'">Foreign Keys</v-tab>
        <v-tab value="advanced" :disabled="mode === 'create'">Advanced</v-tab>
        <v-tab value="yaml" :disabled="mode === 'create'">
          <v-icon icon="mdi-code-braces" class="mr-1" size="small" />
          YAML
        </v-tab>
        <v-tab value="preview" :disabled="mode === 'create' || !formData.name">Preview</v-tab>
      </v-tabs>

      <v-card-text class="pt-4">
        <v-window v-model="activeTab">
          <v-window-item value="basic">
            <v-form ref="formRef" v-model="formValid">
          <!-- Entity Name -->
          <v-text-field
            v-model="formData.name"
            label="Entity Name"
            :rules="nameRules"
            variant="outlined"
            density="comfortable"
            :disabled="mode === 'edit'"
            required
            class="mb-4"
          >
            <template #message>
              <span class="text-caption">Unique identifier for this entity</span>
            </template>
          </v-text-field>

          <!-- Entity Type -->
          <v-select
            v-model="formData.type"
            :items="entityTypeOptions"
            label="Type"
            :rules="requiredRule"
            variant="outlined"
            density="comfortable"
            required
            class="mb-4"
          >
            <template #message>
              <span class="text-caption">How this entity gets its data</span>
            </template>
          </v-select>

          <!-- Surrogate ID -->
          <v-text-field
            v-model="formData.surrogate_id"
            label="Surrogate ID (Optional)"
            variant="outlined"
            density="comfortable"
            placeholder="e.g., sample_id"
            class="mb-4"
          >
            <template #message>
              <span class="text-caption">Generated integer ID field name</span>
            </template>
          </v-text-field>

          <!-- Keys -->
          <v-combobox
            v-model="formData.keys"
            label="Keys"
            :rules="requiredRule"
            variant="outlined"
            density="comfortable"
            multiple
            chips
            closable-chips
            required
            persistent-placeholder
            class="mb-4"
          >
            <template #message>
              <span class="text-caption">Natural key columns that uniquely identify records</span>
            </template>
          </v-combobox>

          <!-- Columns (for data/fixed types) -->
          <v-combobox
            v-if="formData.type === 'data' || formData.type === 'fixed'"
            v-model="formData.columns"
            label="Columns"
            variant="outlined"
            density="comfortable"
            multiple
            chips
            closable-chips
            class="mb-4"
          >
            <template #message>
              <span class="text-caption">Column names to extract or create</span>
            </template>
          </v-combobox>

          <!-- Smart Suggestions Panel -->
          <SuggestionsPanel
            v-if="showSuggestions && suggestions"
            :suggestions="suggestions"
            @accept-foreign-key="handleAcceptForeignKey"
            @reject-foreign-key="handleRejectForeignKey"
            @accept-dependency="handleAcceptDependency"
            @reject-dependency="handleRejectDependency"
            class="mb-4"
          />

          <!-- Source Entity -->
          <v-autocomplete
            v-model="formData.source"
            :items="availableSourceEntities"
            label="Source Entity (Optional)"
            variant="outlined"
            density="comfortable"
            clearable
            persistent-placeholder
            class="mb-4"
          >
            <template #message>
              <span class="text-caption">Parent entity to derive this entity from</span>
            </template>
          </v-autocomplete>

          <!-- Data Source (for sql type) -->
          <v-text-field
            v-if="formData.type === 'sql'"
            v-model="formData.data_source"
            label="Data Source"
            :rules="formData.type === 'sql' ? requiredRule : []"
            variant="outlined"
            density="comfortable"
            class="mb-4"
          >
            <template #message>
              <span class="text-caption">Name of the data source connection</span>
            </template>
          </v-text-field>

          <!-- SQL Query (for sql type) -->
          <SqlEditor
            v-if="formData.type === 'sql'"
            v-model="formData.query"
            height="250px"
            help-text="SQL query to execute against the selected data source"
            :error="formValid === false && !formData.query ? 'SQL query is required' : ''"
            class="mb-4"
          />

              <v-alert v-if="error" type="error" variant="tonal" class="mt-4">
                {{ error }}
              </v-alert>
            </v-form>
          </v-window-item>

          <v-window-item value="relationships">
            <foreign-key-editor
              v-model="formData.foreign_keys"
              :available-entities="availableSourceEntities"
              :config-name="configName"
              :entity-name="formData.name"
              :is-entity-saved="mode === 'edit'"
            />
          </v-window-item>

          <v-window-item value="advanced">
            <advanced-entity-config
              v-model="formData.advanced"
              :available-entities="availableSourceEntities"
            />
          </v-window-item>

          <v-window-item value="yaml">
            <v-alert
              type="info"
              variant="tonal"
              density="compact"
              class="mb-4"
            >
              <div class="text-caption">
                <v-icon icon="mdi-information" size="small" class="mr-1" />
                Edit the entity configuration in YAML format. Changes will be synced with the form editor.
              </div>
            </v-alert>
            
            <yaml-editor
              v-model="yamlContent"
              height="500px"
              :validate-on-change="true"
              @validate="handleYamlValidation"
              @change="handleYamlChange"
            />
            
            <v-alert
              v-if="yamlError"
              type="error"
              density="compact"
              variant="tonal"
              class="mt-2"
            >
              {{ yamlError }}
            </v-alert>
          </v-window-item>

          <v-window-item value="preview">
            <entity-preview-panel
              :config-name="configName"
              :entity-name="formData.name"
              :auto-load="false"
              :auto-refresh="mode === 'edit'"
              @loaded="handlePreviewLoaded"
              @error="handlePreviewError"
            />
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="handleCancel" :disabled="loading">
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="loading"
          :disabled="!formValid"
          @click="handleSubmit"
        >
          {{ mode === 'create' ? 'Create' : 'Save' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, watchEffect } from 'vue'
import { useEntities, useSuggestions } from '@/composables'
import type { EntityResponse } from '@/api/entities'
import type { ForeignKeySuggestion, DependencySuggestion } from '@/composables'
import * as yaml from 'js-yaml'
import ForeignKeyEditor from './ForeignKeyEditor.vue'
import AdvancedEntityConfig from './AdvancedEntityConfig.vue'
import SuggestionsPanel from './SuggestionsPanel.vue'
import EntityPreviewPanel from './EntityPreviewPanel.vue'
import YamlEditor from '../common/YamlEditor.vue'
import SqlEditor from '../common/SqlEditor.vue'

interface Props {
  modelValue: boolean
  configName: string
  entity?: EntityResponse | null
  mode: 'create' | 'edit'
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { entities, create, update } = useEntities({
  configName: props.configName,
  autoFetch: false,
})

const { getSuggestionsForEntity, loading: suggestionsLoading } = useSuggestions()

// Form state
const formRef = ref()
const formValid = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const suggestions = ref<any>(null)
const showSuggestions = ref(false)
const yamlContent = ref('')
const yamlError = ref<string | null>(null)
const yamlValid = ref(true)

interface FormData {
  name: string
  type: string
  surrogate_id: string
  keys: string[]
  columns: string[]
  source: string | null
  data_source: string
  query: string
  foreign_keys: any[]
  advanced: any
}

const formData = ref<FormData>({
  name: '',
  type: 'data',
  surrogate_id: '',
  keys: [],
  columns: [],
  source: null,
  data_source: '',
  query: '',
  foreign_keys: [],
  advanced: {
    filters: [],
    unnest: null,
    append: [],
  },
})

const activeTab = ref('basic')

// Preview handlers
function handlePreviewLoaded(rows: number) {
  console.log(`Preview loaded: ${rows} rows`)
}

function handlePreviewError(error: string) {
  console.error('Preview error:', error)
}

// Computed
const dialogModel = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const entityTypeOptions = [
  { title: 'Data', value: 'data', subtitle: 'Load from CSV or other data source' },
  { title: 'SQL', value: 'sql', subtitle: 'Execute SQL query' },
  { title: 'Fixed', value: 'fixed', subtitle: 'Fixed values defined in config' },
]

const availableSourceEntities = computed(() => {
  return entities.value
    .filter((e) => e.name !== formData.value.name)
    .map((e) => e.name)
})

// Validation rules
const requiredRule = [(v: unknown) => {
  if (Array.isArray(v)) return v.length > 0 || 'This field is required'
  return !!v || 'This field is required'
}]

const nameRules = [
  (v: string) => !!v || 'Entity name is required',
  (v: string) => v.length >= 2 || 'Name must be at least 2 characters',
  (v: string) => /^[a-z][a-z0-9_]*$/.test(v) || 'Name must be lowercase snake_case',
  (v: string) => {
    if (props.mode === 'edit') return true
    return !entities.value.some((e) => e.name === v) || 'Entity name already exists'
  },
]

// YAML Editor Functions
function formDataToYaml(): string {
  const entityData: Record<string, any> = {
    name: formData.value.name,
    type: formData.value.type,
  }

  if (formData.value.surrogate_id) {
    entityData.surrogate_id = formData.value.surrogate_id
  }

  if (formData.value.keys.length > 0) {
    entityData.keys = formData.value.keys
  }

  if (formData.value.columns.length > 0) {
    entityData.columns = formData.value.columns
  }

  if (formData.value.source) {
    entityData.source = formData.value.source
  }

  if (formData.value.type === 'sql') {
    if (formData.value.data_source) {
      entityData.data_source = formData.value.data_source
    }
    if (formData.value.query) {
      entityData.query = formData.value.query
    }
  }

  if (formData.value.foreign_keys.length > 0) {
    entityData.foreign_keys = formData.value.foreign_keys
  }

  if (formData.value.advanced.filters?.length > 0) {
    entityData.filters = formData.value.advanced.filters
  }

  if (formData.value.advanced.unnest) {
    entityData.unnest = formData.value.advanced.unnest
  }

  if (formData.value.advanced.append?.length > 0) {
    entityData.append = formData.value.advanced.append
  }

  return yaml.dump(entityData, { indent: 2, lineWidth: -1 })
}

function yamlToFormData(yamlString: string): boolean {
  try {
    const data = yaml.load(yamlString) as Record<string, any>
    
    formData.value = {
      name: data.name || formData.value.name,
      type: data.type || 'data',
      surrogate_id: data.surrogate_id || '',
      keys: Array.isArray(data.keys) ? data.keys : [],
      columns: Array.isArray(data.columns) ? data.columns : [],
      source: data.source || null,
      data_source: data.data_source || '',
      query: data.query || '',
      foreign_keys: Array.isArray(data.foreign_keys) ? data.foreign_keys : [],
      advanced: {
        filters: Array.isArray(data.filters) ? data.filters : [],
        unnest: data.unnest || null,
        append: Array.isArray(data.append) ? data.append : [],
      },
    }
    
    yamlError.value = null
    return true
  } catch (err) {
    yamlError.value = err instanceof Error ? err.message : 'Invalid YAML'
    return false
  }
}

function handleYamlValidation(isValid: boolean, error?: string) {
  yamlValid.value = isValid
  if (!isValid && error) {
    yamlError.value = error
  }
}

function handleYamlChange(value: string) {
  // Auto-sync YAML to form data when valid
  if (yamlValid.value) {
    yamlToFormData(value)
  }
}

// Methods
async function handleSubmit() {
  if (!formValid.value) return

  const { valid } = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  error.value = null

  try {
    const entityData: Record<string, unknown> = {
      type: formData.value.type,
      keys: formData.value.keys,
    }

    if (formData.value.surrogate_id) {
      entityData.surrogate_id = formData.value.surrogate_id
    }

    if (formData.value.columns.length > 0) {
      entityData.columns = formData.value.columns
    }

    if (formData.value.source) {
      entityData.source = formData.value.source
    }

    if (formData.value.type === 'sql') {
      entityData.data_source = formData.value.data_source
      entityData.query = formData.value.query
    }

    // Include foreign keys if any
    if (formData.value.foreign_keys.length > 0) {
      entityData.foreign_keys = formData.value.foreign_keys
    }

    // Include advanced configuration
    if (formData.value.advanced.filters?.length > 0) {
      entityData.filters = formData.value.advanced.filters
    }
    if (formData.value.advanced.unnest) {
      entityData.unnest = formData.value.advanced.unnest
    }
    if (formData.value.advanced.append?.length > 0) {
      entityData.append = formData.value.advanced.append
    }

    if (props.mode === 'create') {
      await create({
        name: formData.value.name,
        entity_data: entityData,
      })
    } else {
      await update(formData.value.name, {
        entity_data: entityData,
      })
    }

    emit('saved')
    handleClose()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save entity'
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  handleClose()
}

function handleClose() {
  error.value = null
  formRef.value?.reset()
  dialogModel.value = false
}

// Load entity data when editing
watch(
  () => props.entity,
  (newEntity) => {
    if (newEntity && props.mode === 'edit') {
      formData.value = {
        name: newEntity.name,
        type: (newEntity.entity_data.type as string) || 'data',
        surrogate_id: (newEntity.entity_data.surrogate_id as string) || '',
        keys: (newEntity.entity_data.keys as string[]) || [],
        columns: (newEntity.entity_data.columns as string[]) || [],
        source: (newEntity.entity_data.source as string) || null,
        data_source: (newEntity.entity_data.data_source as string) || '',
        query: (newEntity.entity_data.query as string) || '',
        foreign_keys: (newEntity.entity_data.foreign_keys as any[]) || [],
        advanced: {
          filters: (newEntity.entity_data.filters as any[]) || [],
          unnest: newEntity.entity_data.unnest || null,
          append: (newEntity.entity_data.append as any[]) || [],
        },
      }
    } else if (props.mode === 'create') {
      formData.value = {
        name: '',
        type: 'data',
        surrogate_id: '',
        keys: [],
        columns: [],
        source: null,
        data_source: '',
        query: '',
        foreign_keys: [],
        advanced: {
          filters: [],
          unnest: null,
          append: [],
        },
      }
    }
  },
  { immediate: true }
)

// Reset form when dialog opens
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      error.value = null
      formRef.value?.resetValidation()
      suggestions.value = null
      showSuggestions.value = false
      yamlError.value = null
      
      // Initialize YAML content from form data
      if (props.mode === 'edit') {
        yamlContent.value = formDataToYaml()
      }
    }
  }
)

// Sync form to YAML when switching to YAML tab
watch(activeTab, (newTab, oldTab) => {
  if (newTab === 'yaml' && oldTab !== 'yaml') {
    // Switching TO yaml tab - convert form data to YAML
    yamlContent.value = formDataToYaml()
    yamlError.value = null
  } else if (oldTab === 'yaml' && newTab !== 'yaml') {
    // Switching FROM yaml tab - validate and sync to form
    if (yamlValid.value) {
      yamlToFormData(yamlContent.value)
    }
  }
})

// Fetch suggestions when columns change (debounced)
let suggestionTimeout: NodeJS.Timeout | null = null
watchEffect(() => {
  if (props.mode === 'create' && formData.value.name && formData.value.columns.length > 0) {
    // Clear existing timeout
    if (suggestionTimeout) {
      clearTimeout(suggestionTimeout)
    }
    
    // Debounce suggestions fetch
    suggestionTimeout = setTimeout(async () => {
      try {
        const allEntities = entities.value.map(e => ({
          name: e.name,
          columns: e.entity_data.columns as string[] || []
        }))
        
        // Add current entity being created
        allEntities.push({
          name: formData.value.name,
          columns: formData.value.columns
        })
        
        const result = await getSuggestionsForEntity(
          {
            name: formData.value.name,
            columns: formData.value.columns
          },
          allEntities
        )
        
        suggestions.value = result
        showSuggestions.value = true
      } catch (err) {
        console.error('Failed to fetch suggestions:', err)
      }
    }, 1000) // 1 second debounce
  }
})

// Handle suggestion acceptance
function handleAcceptForeignKey(fk: ForeignKeySuggestion) {
  // Add foreign key to form data
  const newFk = {
    entity: fk.remote_entity,
    local_keys: fk.local_keys,
    remote_keys: fk.remote_keys,
    how: 'left' // Default join type
  }
  
  // Check if FK already exists
  const exists = formData.value.foreign_keys.some(
    existing => existing.entity === newFk.entity && 
                JSON.stringify(existing.local_keys) === JSON.stringify(newFk.local_keys)
  )
  
  if (!exists) {
    formData.value.foreign_keys.push(newFk)
  }
}

function handleRejectForeignKey(fk: ForeignKeySuggestion) {
  // Just log for now - user rejected this suggestion
  console.log('Rejected FK suggestion:', fk)
}

function handleAcceptDependency(dep: DependencySuggestion) {
  // Dependencies would be handled by the backend during processing
  // For now, just log
  console.log('Accepted dependency suggestion:', dep)
}

function handleRejectDependency(dep: DependencySuggestion) {
  console.log('Rejected dependency suggestion:', dep)
}
</script>
