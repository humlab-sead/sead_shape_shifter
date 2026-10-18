<template>
  <v-card variant="outlined">
    <v-card-title>Project Metadata</v-card-title>
    <v-divider />

    <!-- Loading State -->
    <v-card-text v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" />
      <p class="mt-4 text-grey">Updating metadata...</p>
    </v-card-text>

    <!-- Metadata Form -->
    <v-card-text v-else>
      <v-form ref="formRef" @submit.prevent="handleSave">
        <v-text-field
          v-model="formData.name"
          label="Project Name"
          hint="Project name is determined by the filename and cannot be edited here"
          persistent-hint
          variant="outlined"
          density="comfortable"
          readonly
          :rules="[rules.required]"
          class="mb-4"
        >
          <template #prepend-inner>
            <v-icon icon="mdi-lock-outline" size="small" />
          </template>
        </v-text-field>

        <v-textarea
          v-model="formData.description"
          label="Description"
          persistent-hint
          variant="outlined"
          density="comfortable"
          rows="3"
          class="mb-4"
        />

        <v-text-field
          v-model="formData.version"
          label="Version"
          persistent-hint
          variant="outlined"
          density="comfortable"
          :rules="[rules.version]"
          class="mb-4"
        />

        <div v-if="hasProviderBinding" class="mb-4">
          <v-text-field
            :model-value="providerDisplay"
            label="Data Provider"
            variant="outlined"
            density="comfortable"
            readonly
            class="mb-4"
          />
          <v-text-field
            :model-value="formData.provider_schema"
            label="Provider Schema"
            variant="outlined"
            density="comfortable"
            readonly
          />
        </div>
        <div v-else class="mb-4">
          <v-select
            v-model="formData.data_provider_code"
            :items="providerOptions"
            :loading="providersLoading"
            :rules="[rules.required]"
            label="Data Provider"
            item-title="title"
            item-value="value"
            variant="outlined"
            density="comfortable"
            clearable
            class="mb-4"
          />
          <v-select
            v-model="formData.provider_schema"
            :items="schemaOptions"
            :disabled="!formData.data_provider_code || providersLoading || schemaOptions.length === 0"
            :rules="[rules.required]"
            label="Provider Schema"
            item-title="title"
            item-value="value"
            variant="outlined"
            density="comfortable"
            clearable
          />
          <v-alert v-if="providerListError" type="error" variant="tonal" class="mt-3">
            {{ providerListError }}
          </v-alert>
        </div>

        <v-select
          v-model="formData.default_entity"
          :items="availableEntities"
          label="Default Entity"
          persistent-hint
          variant="outlined"
          density="comfortable"
          clearable
          class="mb-4"
        >
          <template #prepend-inner>
            <v-icon icon="mdi-cube-outline" />
          </template>
        </v-select>

        <v-combobox
          v-model="formData.target_model"
          :items="targetModelItems"
          item-title="label"
          item-value="value"
          :loading="yamlFilesLoading"
          label="Target Model"
          hint="Select a project-local or shared YAML target model, or type an @load: path. Shared models are read-only."
          persistent-hint
          variant="outlined"
          density="comfortable"
          clearable
          class="mb-4"
          placeholder="@load: target_model.yml"
        >
          <template #prepend-inner>
            <v-icon icon="mdi-check-decagram-outline" size="small" />
          </template>
          <template #no-data>
            <v-list-item>
              <v-list-item-title class="text-caption text-grey">
                {{ yamlFilesLoading ? 'Loading files...' : 'No YAML files found — type a path manually' }}
              </v-list-item-title>
            </v-list-item>
          </template>
        </v-combobox>

        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
          {{ error }}
        </v-alert>

        <v-alert v-if="successMessage" type="success" variant="tonal" class="mb-4">
          {{ successMessage }}
        </v-alert>

        <div class="d-flex gap-2">
          <v-btn
            color="primary"
            prepend-icon="mdi-content-save"
            :disabled="
              !hasChanges ||
              (!hasProviderBinding &&
                (!formData.data_provider_code ||
                  !formData.provider_schema ||
                  providersLoading ||
                  providerListError !== null))
            "
            :loading="saving"
            @click="handleSave"
          >
            Save Metadata
          </v-btn>
          <v-btn variant="outlined" :disabled="!hasChanges" @click="handleReset"> Reset </v-btn>
        </div>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { storeToRefs } from 'pinia'
import { projectsApi } from '@/api/projects'
import { dataProvidersApi, type DataProvider } from '@/api/data-providers'
import type { MetadataUpdateRequest, TargetModelFileOption } from '@/api/projects'

const props = defineProps<{
  projectName: string
}>()

const projectStore = useProjectStore()
const { selectedProject, loading } = storeToRefs(projectStore)

const formRef = ref()
const saving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// YAML files available to the target model picker
const targetModelFiles = ref<TargetModelFileOption[]>([])
const yamlFilesLoading = ref(false)
const providers = ref<DataProvider[]>([])
const providersLoading = ref(false)
const providerListError = ref<string | null>(null)

async function loadTargetModelFiles() {
  yamlFilesLoading.value = true
  try {
    targetModelFiles.value = await projectsApi.listTargetModels(props.projectName)
  } catch {
    targetModelFiles.value = []
  } finally {
    yamlFilesLoading.value = false
  }
}

async function loadProviders() {
  providersLoading.value = true
  providerListError.value = null
  try {
    providers.value = await dataProvidersApi.list()
    if (providers.value.length === 0) {
      providerListError.value = 'No registered data providers are available.'
    }
  } catch {
    providers.value = []
    providerListError.value = 'Could not load registered data providers. Try again later.'
  } finally {
    providersLoading.value = false
  }
}

const targetModelItems = computed(() => targetModelFiles.value)
const providerOptions = computed(() =>
  providers.value.map((provider) => ({ title: `${provider.name} (${provider.code})`, value: provider.code }))
)
const selectedProvider = computed(() =>
  providers.value.find((provider) => provider.code === formData.value.data_provider_code)
)
const schemaOptions = computed(() =>
  (selectedProvider.value?.schemas ?? []).map((schema) => ({
    title: schema.provider_schema,
    value: schema.provider_schema,
  }))
)
const providerDisplay = computed(() => {
  const code = formData.value.data_provider_code
  const provider = providers.value.find((entry) => entry.code === code)
  return code && provider ? `${provider.name} (${code})` : (code ?? '')
})

// Form data
const formData = ref<{
  name: string
  description: string | null
  version: string | null
  default_entity: string | null
  target_model: string | null
  data_provider_code: string | null
  provider_schema: string | null
}>({
  name: '',
  description: null,
  version: null,
  default_entity: null,
  target_model: null,
  data_provider_code: null,
  provider_schema: null,
})

// Initial values for change detection
const initialValues = ref<typeof formData.value | null>(null)
const hasProviderBinding = computed(() =>
  Boolean(initialValues.value?.data_provider_code && initialValues.value?.provider_schema)
)

// Validation rules
const rules = {
  required: (value: string) => !!value || 'This field is required',
  version: (value: string | null) => {
    if (!value) return true
    const versionPattern = /^\d+\.\d+\.\d+$/
    return versionPattern.test(value) || 'Version must be in x.y.z format (e.g., 1.0.0)'
  },
}

// Computed
const availableEntities = computed(() => {
  if (!selectedProject.value?.entities) return []
  return Object.keys(selectedProject.value.entities)
})

const hasChanges = computed(() => {
  if (!initialValues.value) return false
  return (
    formData.value.name !== initialValues.value.name ||
    formData.value.description !== initialValues.value.description ||
    formData.value.version !== initialValues.value.version ||
    formData.value.default_entity !== initialValues.value.default_entity ||
    formData.value.target_model !== initialValues.value.target_model ||
    formData.value.data_provider_code !== initialValues.value.data_provider_code ||
    formData.value.provider_schema !== initialValues.value.provider_schema
  )
})

// Methods
function loadMetadata() {
  if (selectedProject.value?.metadata) {
    const metadata = selectedProject.value.metadata
    // target_model on ProjectMetadata may be a string (@load: ...) or (@include: ...) null; if it's an
    // object (resolved inline dict) we can't display it sensibly — show null instead.
    const rawTargetModel: string | null = typeof metadata.target_model === 'string' ? metadata.target_model : null
    formData.value = {
      name: metadata.name || props.projectName,
      description: metadata.description || null,
      version: metadata.version || null,
      default_entity: metadata.default_entity || null,
      target_model: rawTargetModel,
      data_provider_code: metadata.data_provider_code || null,
      provider_schema: metadata.provider_schema || null,
    }
    initialValues.value = { ...formData.value }
  }
}

async function handleSave() {
  error.value = null
  successMessage.value = null

  if (
    !hasProviderBinding.value &&
    (!formData.value.data_provider_code ||
      !formData.value.provider_schema ||
      providersLoading.value ||
      providerListError.value !== null)
  ) {
    error.value = providerListError.value ?? 'Select a registered data provider and provider schema before saving.'
    return
  }

  // Validate form
  const { valid } = await formRef.value.validate()
  if (!valid) {
    return
  }

  saving.value = true
  try {
    const updateData: MetadataUpdateRequest = {
      // Name is locked to filename, never send it for update
      description: formData.value.description,
      version: formData.value.version,
      default_entity: formData.value.default_entity,
      // Always include target_model so the backend knows it was explicitly provided
      // (empty string / null both clear the field)
      target_model: formData.value.target_model || null,
      ...(hasProviderBinding.value
        ? {}
        : {
            data_provider_code: formData.value.data_provider_code,
            provider_schema: formData.value.provider_schema,
          }),
    }

    await projectStore.updateMetadata(props.projectName, updateData)

    // Update initial values after successful save
    initialValues.value = { ...formData.value }

    successMessage.value = 'Metadata updated successfully'

    // Clear success message after 3 seconds
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to update metadata'
  } finally {
    saving.value = false
  }
}

watch(
  () => formData.value.data_provider_code,
  (newCode, previousCode) => {
    if (newCode !== previousCode && !hasProviderBinding.value) {
      formData.value.provider_schema = null
    }
  }
)

function handleReset() {
  if (initialValues.value) {
    formData.value = { ...initialValues.value }
  }
  error.value = null
  successMessage.value = null
}

// Watch for project changes
watch(
  () => selectedProject.value,
  () => {
    loadMetadata()
  },
  { immediate: true }
)

onMounted(() => {
  loadMetadata()
  loadTargetModelFiles()
  loadProviders()
})
</script>
