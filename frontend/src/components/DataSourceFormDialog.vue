<template>
  <v-dialog :model-value="modelValue" max-width="700" persistent @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="text-h5">
        {{ isEditing ? 'Edit Data Source' : 'New Data Source' }}
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" v-model="formValid">
          <!-- Name -->
          <v-text-field
            v-model="form.name"
            label="Name *"
            hint="Unique identifier for this data source"
            persistent-hint
            :rules="[rules.required, rules.unique]"
            :disabled="isEditing"
            variant="outlined"
            class="mb-2"
          />

          <!-- Driver Type -->
          <v-select
            v-model="form.driver"
            :items="availableDrivers"
            label="Type *"
            :rules="[rules.required]"
            variant="outlined"
            class="mb-2"
            :loading="schemaLoading"
            @update:model-value="handleDriverChange"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <v-list-item-title>{{ item.title }}</v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  {{ item.raw.description }}
                </v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-select>

          <!-- Dynamic Fields based on Driver Schema -->
          <template v-if="currentSchema">
            <template v-for="field in currentSchema.fields" :key="field.name">
              <!-- String/File Path Field -->
              <v-text-field
                v-if="field.type === 'string' || field.type === 'file_path'"
                v-model="form.options[field.name]"
                :label="formatFieldLabel(field)"
                :hint="shouldShowHint(field) ? field.description : undefined"
                :placeholder="field.placeholder"
                :rules="field.required ? [rules.required] : []"
                :persistent-hint="shouldShowHint(field)"
                variant="outlined"
                class="mb-2"
              />

              <!-- Integer Field -->
              <v-text-field
                v-else-if="field.type === 'integer'"
                v-model.number="form.options[field.name]"
                :label="formatFieldLabel(field)"
                :hint="shouldShowHint(field) ? field.description : undefined"
                :placeholder="field.placeholder"
                :rules="field.required ? [rules.required, rules.integer] : [rules.integer]"
                type="number"
                :min="field.min_value"
                :max="field.max_value"
                :persistent-hint="shouldShowHint(field)"
                variant="outlined"
                class="mb-2"
              />

              <!-- Password Field -->
              <v-text-field
                v-else-if="field.type === 'password'"
                v-model="form.options[field.name]"
                :label="formatFieldLabel(field)"
                :hint="isEditing ? 'Leave empty to keep existing password' : field.description"
                :placeholder="field.placeholder"
                type="password"
                persistent-hint
                variant="outlined"
                class="mb-2"
              />

              <!-- Boolean Field -->
              <v-checkbox
                v-else-if="field.type === 'boolean'"
                v-model="form.options[field.name]"
                :label="formatFieldLabel(field)"
                :hint="shouldShowHint(field) ? field.description : undefined"
                :persistent-hint="shouldShowHint(field)"
                class="mb-2"
              />
            </template>
          </template>

          <!-- Description -->
          <v-textarea
            v-model="form.description"
            label="Description"
            hint="Optional description of this data source"
            persistent-hint
            rows="2"
            variant="outlined"
            class="mb-2"
          />
        </v-form>

        <!-- Error Message -->
        <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mt-3">
          {{ errorMessage }}
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="handleCancel">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="saving"
          :disabled="!formValid"
          @click="handleSave"
        >
          {{ isEditing ? 'Update' : 'Create' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useDataSourceStore } from '@/stores/data-source'
import { useDriverSchema } from '@/composables/useDriverSchema'
import type { DataSourceConfig } from '@/types/data-source'
import type { FieldMetadata } from '@/types/driver-schema'

const props = defineProps<{
  modelValue: boolean
  dataSource?: DataSourceConfig | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: []
}>()

const dataSourceStore = useDataSourceStore()
const {
  availableDrivers,
  getSchema,
  getDefaultFormValues,
  loading: schemaLoading,
  loadSchemas,
} = useDriverSchema()

// State
const formRef = ref()
const formValid = ref(false)
const form = ref<{
  name: string
  driver: string
  description: string
  options: Record<string, any>
}>({
  name: '',
  driver: '',
  description: '',
  options: {},
})
const saving = ref(false)
const errorMessage = ref<string | null>(null)

// Computed
const isEditing = computed(() => !!props.dataSource)
const currentSchema = computed(() => form.value.driver ? getSchema(form.value.driver) : null)

// Validation rules
const rules = {
  required: (v: string | number) => {
    if (v === null || v === undefined || v === '') return 'Required'
    return true
  },
  integer: (v: any) => {
    if (v === null || v === undefined || v === '') return true
    return Number.isInteger(Number(v)) || 'Must be an integer'
  },
  unique: (v: string) => {
    if (isEditing.value && v === props.dataSource?.name) return true
    const existing = dataSourceStore.dataSourceByName(v)
    return !existing || 'Data source with this name already exists'
  },
}

// Methods
function formatFieldLabel(field: FieldMetadata): string {
  // Use description as user-friendly label, fall back to field name
  const label = field.description || field.name
  return field.required ? `${label} *` : label
}

function shouldShowHint(field: FieldMetadata): boolean {
  // Don't show hint - description is already used as the label
  return false
}

function handleDriverChange(newDriver: string) {
  // Reset options and apply defaults for new driver
  const defaults = getDefaultFormValues(newDriver)
  form.value.options = { ...defaults }
}

async function handleSave() {
  if (!formRef.value) return

  const { valid } = await formRef.value.validate()
  if (!valid) return

  saving.value = true
  errorMessage.value = null

  try {
    const schema = currentSchema.value
    if (!schema) {
      throw new Error('No schema found for selected driver')
    }

    // Build config from form
    const config: DataSourceConfig = {
      name: form.value.name,
      driver: form.value.driver,
      description: form.value.description || undefined,
    }

    // Map options to top-level fields and options object
    const topLevelFields = ['host', 'port', 'database', 'username', 'password', 'filename']
    const options: Record<string, any> = {}

    for (const field of schema.fields) {
      const value = form.value.options[field.name]
      
      // Skip empty passwords when editing (keep existing)
      if (field.type === 'password' && isEditing.value && !value) {
        continue
      }

      // Skip null/undefined values
      if (value === null || value === undefined || value === '') {
        continue
      }

      // Assign to top-level or options
      if (topLevelFields.includes(field.name)) {
        (config as any)[field.name] = value
      } else {
        options[field.name] = value
      }
    }

    // Add options if not empty
    if (Object.keys(options).length > 0) {
      config.options = options
    }

    if (isEditing.value && props.dataSource) {
      await dataSourceStore.updateDataSource(props.dataSource.name, config)
    } else {
      await dataSourceStore.createDataSource(config)
    }

    emit('save')
    handleCancel()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : 'Failed to save data source'
  } finally {
    saving.value = false
  }
}

function handleCancel() {
  emit('update:modelValue', false)
  resetForm()
}

function resetForm() {
  form.value = {
    name: '',
    driver: '',
    description: '',
    options: {},
  }
  errorMessage.value = null
  formRef.value?.resetValidation()
}

function loadDataSource(dataSource: DataSourceConfig) {
  form.value.name = dataSource.name
  form.value.driver = dataSource.driver
  form.value.description = dataSource.description || ''
  
  // Load all fields into options
  const options: Record<string, any> = {}
  
  // Load top-level fields
  if (dataSource.host) options.host = dataSource.host
  if (dataSource.port) options.port = dataSource.port
  if (dataSource.database) options.database = dataSource.database
  if (dataSource.dbname) options.database = dataSource.dbname // Handle alias
  if (dataSource.username) options.username = dataSource.username
  if (dataSource.filename) options.filename = dataSource.filename
  if (dataSource.file_path) options.filename = dataSource.file_path // Handle alias
  
  // Load options object
  if (dataSource.options) {
    Object.assign(options, dataSource.options)
  }
  
  form.value.options = options
}

// Lifecycle
onMounted(async () => {
  await loadSchemas()
})

// Watch for dialog open/close
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      if (props.dataSource) {
        loadDataSource(props.dataSource)
      } else {
        resetForm()
      }
    }
  }
)
</script>
