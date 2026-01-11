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

        <!-- Output Folder -->
        <v-text-field
          v-model="form.output_folder"
          label="Output Folder"
          hint="Folder for generated files (default: 'output')"
          persistent-hint
          prepend-icon="mdi-folder"
        />

        <!-- Database Configuration -->
        <v-expansion-panels class="mt-4">
          <v-expansion-panel title="Database Configuration">
            <v-expansion-panel-text>
              <v-text-field
                v-model="form.config?.database.host"
                label="Host"
                prepend-icon="mdi-server"
              />
              <v-text-field
                v-model.number="form.config?.database.port"
                label="Port"
                type="number"
                prepend-icon="mdi-ethernet"
              />
              <v-text-field
                v-model="form.config?.database.dbname"
                label="Database Name"
                prepend-icon="mdi-database"
              />
              <v-text-field
                v-model="form.config?.database.user"
                label="User"
                prepend-icon="mdi-account"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>

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
import { ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useIngesterStore } from '@/stores/ingester'
import type { IngestRequest, ValidateRequest } from '@/types/ingester'

const ingesterStore = useIngesterStore()
const {
  selectedIngester,
  validationResult,
  ingestionResult,
  error,
  isValidating,
  isIngesting
} = storeToRefs(ingesterStore)
const { validate, ingest, clearError, clearValidation, clearIngestion } = ingesterStore

const formRef = ref()
const formValid = ref(false)

const form = ref<IngestRequest>({
  source: '',
  submission_name: '',
  data_types: '',
  output_folder: 'output',
  do_register: false,
  explode: false,
  config: {
    database: {
      host: 'localhost',
      port: 5432,
      dbname: '',
      user: ''
    },
    ignore_columns: []
  }
})

const ignoreColumnsText = ref('date_updated\n*_uuid')

// Sync ignore_columns with textarea
watch(ignoreColumnsText, (newValue) => {
  form.value.config!.ignore_columns = newValue
    .split('\n')
    .map(s => s.trim())
    .filter(s => s.length > 0)
})

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
  clearValidation()
  clearIngestion()
  clearError()
}
</script>
