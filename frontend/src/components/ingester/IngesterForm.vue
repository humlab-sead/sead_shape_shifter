<template>
  <v-card>
    <v-card-title>
      {{ selectedIngester?.name || 'Ingester Configuration' }}
    </v-card-title>

    <v-card-text>
      <v-form ref="formRef" v-model="formValid">
        <!-- Source File -->
        <v-text-field
          v-model="form.source"
          label="Source File Path *"
          hint="Path to the Excel file to ingest"
          persistent-hint
          :rules="[rules.required]"
          prepend-icon="mdi-file-excel"
        />

        <!-- Submission Name -->
        <v-text-field
          v-model="form.submission_name"
          label="Submission Name *"
          hint="Unique name for this submission"
          persistent-hint
          :rules="[rules.required]"
          prepend-icon="mdi-tag"
        />

        <!-- Data Types -->
        <v-text-field
          v-model="form.data_types"
          label="Data Types *"
          hint="Type of data (e.g., 'dendro', 'ceramics', 'adna')"
          persistent-hint
          :rules="[rules.required]"
          prepend-icon="mdi-shape"
        />

        <!-- Target Database Info -->
        <v-alert
          v-if="targetDataSourceName"
          type="info"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          <div class="text-caption">
            <strong>Target Database:</strong> {{ targetDataSourceName }}
            <span v-if="targetDataSourceInfo">
              <span v-if="targetDataSourceInfo.host">
                • {{ targetDataSourceInfo.host }}{{ targetDataSourceInfo.port ? ':' + targetDataSourceInfo.port : '' }}
              </span>
              <span v-if="targetDataSourceInfo.database || targetDataSourceInfo.dbname">
                • {{ targetDataSourceInfo.database || targetDataSourceInfo.dbname }}
              </span>
            </span>
          </div>
          <div v-if="!targetDataSourceInfo" class="text-caption error--text mt-1">
            ⚠️ Data source "{{ targetDataSourceName }}" not found in project configuration
          </div>
        </v-alert>

        <v-alert
          v-else
          type="warning"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          No target database configured for this ingester in the project file.
          Please configure the "ingesters.{{ selectedIngester?.key }}.data_source" option.
        </v-alert>

        <!-- Advanced Options -->
        <v-expansion-panels class="mt-4">
          <v-expansion-panel title="Advanced Options">
            <v-expansion-panel-text>
              <v-textarea
                v-model="ignoreColumnsText"
                label="Ignore Columns"
                hint="One pattern per line (e.g., 'date_updated', '*_uuid')"
                persistent-hint
                rows="3"
              />

              <v-switch
                v-model="form.do_register"
                label="Register in Database"
                color="primary"
                hide-details
              />

              <v-switch
                v-model="form.explode"
                label="Explode to Public Tables"
                color="primary"
                hide-details
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- Validation Result -->
        <v-alert
          v-if="validationResult"
          :type="validationResult.is_valid ? 'success' : 'error'"
          variant="tonal"
          class="mt-4"
        >
          <div class="text-subtitle-2">
            {{ validationResult.is_valid ? 'Validation Passed' : 'Validation Failed' }}
          </div>
          <div v-if="validationResult.errors.length > 0" class="mt-2">
            <div class="text-caption">Errors:</div>
            <ul>
              <li v-for="(error, i) in validationResult.errors" :key="i">{{ error }}</li>
            </ul>
          </div>
          <div v-if="validationResult.warnings.length > 0" class="mt-2">
            <div class="text-caption">Warnings:</div>
            <ul>
              <li v-for="(warning, i) in validationResult.warnings" :key="i">{{ warning }}</li>
            </ul>
          </div>
        </v-alert>

        <!-- Ingestion Result -->
        <v-alert
          v-if="ingestionResult"
          :type="ingestionResult.success ? 'success' : 'error'"
          variant="tonal"
          class="mt-4"
        >
          <div class="text-subtitle-2">{{ ingestionResult.message }}</div>
          <div v-if="ingestionResult.success" class="mt-2">
            <div>Records Processed: {{ ingestionResult.records_processed }}</div>
            <div v-if="ingestionResult.submission_id">
              Submission ID: {{ ingestionResult.submission_id }}
            </div>
            <div v-if="ingestionResult.output_path">
              Output: {{ ingestionResult.output_path }}
            </div>
          </div>
        </v-alert>

        <!-- Error Message -->
        <v-alert v-if="error" type="error" variant="tonal" class="mt-4" closable @click:close="clearError">
          {{ error }}
        </v-alert>
      </v-form>
    </v-card-text>

    <v-card-actions>
      <v-btn
        color="primary"
        variant="outlined"
        :loading="isValidating"
        :disabled="!formValid || !selectedIngester"
        @click="handleValidate"
      >
        <v-icon start>mdi-check-circle</v-icon>
        Validate
      </v-btn>

      <v-btn
        color="success"
        :loading="isIngesting"
        :disabled="!formValid || !selectedIngester"
        @click="handleIngest"
      >
        <v-icon start>mdi-database-import</v-icon>
        Ingest
      </v-btn>

      <v-spacer />

      <v-btn variant="text" @click="resetForm">
        Reset
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useIngesterStore } from '@/stores/ingester'
import { useDataSourceStore } from '@/stores/data-source'
import { useProjectStore } from '@/stores/project'
import type { IngestRequest, ValidateRequest } from '@/types/ingester'

const ingesterStore = useIngesterStore()
const dataSourceStore = useDataSourceStore()
const projectStore = useProjectStore()

const {
  selectedIngester,
  validationResult,
  ingestionResult,
  error,
  isValidating,
  isIngesting
} = storeToRefs(ingesterStore)
const { validate, ingest, clearError, clearValidation, clearIngestion } = ingesterStore
const { selectedProject } = storeToRefs(projectStore)

const formRef = ref()
const formValid = ref(false)

const form = ref<IngestRequest>({
  source: '',
  submission_name: '',
  data_types: '',
  do_register: false,
  explode: false,
  config: {
    data_source_name: '',
    ignore_columns: []
  }
})

const ignoreColumnsText = ref('date_updated\n*_uuid\n(*')

// Computed properties
const ingesterConfig = computed(() => {
  if (!selectedProject.value || !selectedIngester.value) return null
  const ingesters = selectedProject.value.options?.ingesters || {}
  return ingesters[selectedIngester.value.key] || null
})

const targetDataSourceName = computed(() => {
  return ingesterConfig.value?.data_source || null
})

const targetDataSourceInfo = computed(() => {
  if (!targetDataSourceName.value) return null
  return dataSourceStore.dataSourceByName(targetDataSourceName.value)
})

// Sync ignore_columns with textarea
watch(ignoreColumnsText, (newValue) => {
  form.value.config!.ignore_columns = newValue
    .split('\n')
    .map(s => s.trim())
    .filter(s => s.length > 0)
})

// Load defaults from project ingester config when it changes
watch(ingesterConfig, (config) => {
  if (!config) return
  
  // Load data source
  if (config.data_source && form.value.config) {
    form.value.config.data_source_name = config.data_source
  }
  
  // Load ignore columns
  if (config.options?.ignore_columns) {
    ignoreColumnsText.value = config.options.ignore_columns.join('\n')
  }
  
  // Load register/explode flags
  if (config.options?.do_register !== undefined) {
    form.value.do_register = config.options.do_register
  }
  if (config.options?.explode !== undefined) {
    form.value.explode = config.options.explode
  }
}, { immediate: true })

const rules = {
  required: (v: string) => !!v || 'Required field'
}

async function handleValidate() {
  if (!formValid.value) return

  clearValidation()
  clearError()

  const request: ValidateRequest = {
    source: form.value.source,
    config: form.value.config
  }

  await validate(request)
}

async function handleIngest() {
  if (!formValid.value) return

  clearIngestion()
  clearError()

  await ingest(form.value)
}

function resetForm() {
  formRef.value?.reset()
  // Reload from project config
  if (ingesterConfig.value) {
    watch(ingesterConfig, () => {}, { immediate: true })
  }
  clearValidation()
  clearIngestion()
  clearError()
}

// Load data sources on mount
onMounted(async () => {
  if (dataSourceStore.dataSources.length === 0) {
    try {
      await dataSourceStore.fetchDataSources()
    } catch (err) {
      console.error('Failed to load data sources:', err)
    }
  }
})
</script>
