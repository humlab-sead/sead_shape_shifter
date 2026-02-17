<template>
  <v-dialog
    :model-value="modelValue"
    max-width="700"
    persistent
    @update:model-value="$emit('update:modelValue', $event)"
  >
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
            item-title="title"
            item-value="value"
            item-subtitle="description"
            variant="outlined"
            class="mb-2"
            :loading="schemaLoading"
            @update:model-value="handleDriverChange"
          />

          <!-- Dynamic Fields based on Driver Schema -->
          <template v-if="currentSchema">
            <template v-for="field in currentSchema.fields" :key="field.name">
              <!-- String/File Path Field -->
              <v-text-field
                v-if="field.type === 'string'"
                v-model="form.options[field.name]"
                :label="formatFieldLabel(field)"
                :placeholder="field.placeholder"
                :rules="field.required ? [rules.required] : []"
                variant="outlined"
                class="mb-2"
              />

              <!-- Integer Field -->
              <v-text-field
                v-else-if="field.type === 'integer'"
                v-model="form.options[field.name]"
                :label="formatFieldLabel(field)"
                :placeholder="field.placeholder"
                :rules="field.required ? [rules.required] : []"
                variant="outlined"
                class="mb-2"
              />

              <!-- File Path Field (upload or select existing) -->
              <div v-else-if="field.type === 'file_path'" class="mb-2">
                <div class="d-flex align-center mb-2">
                  <div class="font-weight-medium">{{ formatFieldLabel(field) }}</div>
                  <v-spacer />
                  <v-btn-toggle v-model="filePickerMode" density="comfortable" rounded="0" divided>
                    <v-btn value="existing" size="small">Select</v-btn>
                    <v-btn value="upload" size="small">Upload</v-btn>
                  </v-btn-toggle>
                </div>

                <v-select
                  v-if="filePickerMode === 'existing'"
                  v-model="form.options[field.name]"
                    :items="projectFileItems"
                    label="Select existing file"
                    variant="outlined"
                    class="mb-2"
                    :loading="projectFilesLoading"
                    :disabled="projectFilesLoading"
                    item-title="title"
                    item-value="value"
                    :rules="field.required ? [rules.required] : []"
                    @focus="fetchProjectFiles"
                  >
                    <template #item="{ props, item }">
                      <v-list-item v-bind="props">
                        <v-list-item-title>{{ item.raw.title }}</v-list-item-title>
                        <v-list-item-subtitle class="text-caption">{{ item.raw.subtitle }}</v-list-item-subtitle>
                      </v-list-item>
                    </template>
                  </v-select>

                  <div v-else>
                    <v-file-input
                      v-model="uploadSelection"
                      label="Upload file"
                      :placeholder="field.placeholder || 'Choose file'"
                      :rules="field.required ? [rules.required] : []"
                      variant="outlined"
                      class="mb-2"
                      :accept="fileAccept"
                      :loading="fileUploadInProgress"
                      @update:model-value="(files) => handleFileUpload(files, field.name)"
                    />
                    <div v-if="form.options[field.name]" class="text-caption text-success">
                      Selected: {{ form.options[field.name] }}
                    </div>
                  </div>

                  <div class="d-flex align-center justify-space-between mt-1">
                    <v-btn size="small" variant="text" prepend-icon="mdi-refresh" @click="fetchProjectFiles">
                      Refresh list
                    </v-btn>
                    <div class="text-caption text-grey">Files saved in workspace projects folder</div>
                  </div>

                  <v-alert v-if="projectFilesError" type="error" variant="tonal" density="compact" class="mt-2">
                    {{ projectFilesError }}
                  </v-alert>
                </div>

              <!-- Password Field -->
              <!-- <v-text-field
                v-else-if="field.type === 'password'"
                v-model="form.options[field.name]"
                :label="formatFieldLabel(field)"
                :hint="isEditing ? 'Leave empty to keep existing password' : field.description"
                :placeholder="field.placeholder"
                type="password"
                persistent-hint
                variant="outlined"
                class="mb-2"
              /> -->

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
          <!-- <v-textarea
            v-model="form.description"
            label="Description"
            hint="Optional description of this data source"
            persistent-hint
            rows="2"
            variant="outlined"
            class="mb-2"
          /> -->
        </v-form>

        <!-- Error Message -->
        <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mt-3">
          {{ errorMessage }}
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="handleCancel">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" :disabled="!formValid" @click="handleSave">
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
import { dataSourceFilesApi } from '@/api/data-source-files'
import type { DataSourceConfig, DataSourceType } from '@/types/data-source'
import type { ProjectFileInfo } from '@/types'
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
  getCanonicalDriver,
  getExtensionsForDriver,
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
const filePickerMode = ref<'existing' | 'upload'>('existing')
const uploadSelection = ref<File[] | File | null>(null)
const projectFiles = ref<ProjectFileInfo[]>([])
const projectFilesLoading = ref(false)
const projectFilesError = ref<string | null>(null)
const fileUploadInProgress = ref(false)

// Computed
const isEditing = computed(() => !!props.dataSource)
const currentSchema = computed(() => (form.value.driver ? getSchema(form.value.driver) : null))
const hasFileField = computed(() => currentSchema.value?.fields.some((field) => field.type === 'file_path') ?? false)
const projectFileItems = computed(() =>
  projectFiles.value.map((file) => ({
    title: file.name,
    value: file.path,
    subtitle: formatProjectFileSubtitle(file),
  }))
)
const fileAccept = computed(() => {
  const extensions = getExtensionsForDriver(form.value.driver)
  return extensions ? extensions.map((ext) => `.${ext}`).join(',') : undefined
})

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

function formatProjectFileSubtitle(file: ProjectFileInfo): string {
  const kb = Math.max(1, Math.round(file.size_bytes / 1024))
  return `${kb} KB${file.modified_at ? ` • ${file.modified_at}` : ''}`
}

async function fetchProjectFiles() {
  if (!hasFileField.value) {
    projectFiles.value = []
    return
  }

  projectFilesLoading.value = true
  projectFilesError.value = null

  try {
    const fileField = currentSchema.value?.fields.find((field) => field.type === 'file_path')
    const extensions = fileField?.extensions?.length ? fileField.extensions : getExtensionsForDriver(form.value.driver)
    projectFiles.value = await dataSourceFilesApi.listFiles(extensions)
  } catch (e) {
    projectFilesError.value = e instanceof Error ? e.message : 'Failed to load data source files'
  } finally {
    projectFilesLoading.value = false
  }
}

async function handleFileUpload(files: File[] | File | null, fieldName: string) {
  if (!files) {
    return
  }

  const file = Array.isArray(files) ? files[0] : files
  if (!file) return

  fileUploadInProgress.value = true
  projectFilesError.value = null

  try {
    const info = await dataSourceFilesApi.uploadFile(file)
    form.value.options[fieldName] = info.path
    uploadSelection.value = null
    filePickerMode.value = 'existing'
    await fetchProjectFiles()
  } catch (e) {
    projectFilesError.value = e instanceof Error ? e.message : 'Failed to upload file'
  } finally {
    fileUploadInProgress.value = false
  }
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
  filePickerMode.value = 'existing'
  void fetchProjectFiles()
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
      driver: form.value.driver as DataSourceType,
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
        ;(config as any)[field.name] = value
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
  projectFilesError.value = null
  uploadSelection.value = null
  filePickerMode.value = 'existing'
  formRef.value?.resetValidation()
}

function loadDataSource(dataSource: DataSourceConfig) {
  form.value.name = dataSource.name
  form.value.driver = getCanonicalDriver(dataSource.driver)
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

  // Load options object and handle aliases
  if (dataSource.options) {
    const schema = getSchema(dataSource.driver)
    
    for (const [key, value] of Object.entries(dataSource.options)) {
      // Find the canonical field name by checking if this key is an alias
      let canonicalName = key
      
      if (schema) {
        const field = schema.fields.find(
          (f) => f.name === key || (f.aliases && f.aliases.includes(key))
        )
        if (field) {
          canonicalName = field.name
        }
      }
      
      // Set the value using the canonical field name
      options[canonicalName] = value
    }
  }

  form.value.options = options

  void fetchProjectFiles()
}

// Lifecycle
onMounted(async () => {
  await loadSchemas()
})

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      if (props.dataSource) {
        loadDataSource(props.dataSource)
      } else {
        resetForm()
      }

      projectFilesError.value = null
      if (hasFileField.value) {
        void fetchProjectFiles()
      }
    }
  }
)

watch(
  () => hasFileField.value,
  (newValue) => {
    if (newValue) {
      void fetchProjectFiles()
    }
  }
)
</script>
