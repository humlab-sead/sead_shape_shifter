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
            :items="driverOptions"
            label="Type *"
            :rules="[rules.required]"
            variant="outlined"
            class="mb-2"
            @update:model-value="handleDriverChange"
          />

          <!-- Database Connection Fields -->
          <div v-if="isDatabaseDriver">
            <v-text-field
              v-model="form.host"
              label="Host *"
              :rules="[rules.required]"
              variant="outlined"
              class="mb-2"
            />

            <v-text-field
              v-model.number="form.port"
              label="Port *"
              type="number"
              :rules="[rules.required, rules.port]"
              variant="outlined"
              class="mb-2"
            />

            <v-text-field
              v-model="form.database"
              label="Database *"
              :rules="[rules.required]"
              variant="outlined"
              class="mb-2"
            />

            <v-text-field
              v-model="form.username"
              label="Username *"
              :rules="[rules.required]"
              variant="outlined"
              class="mb-2"
            />

            <v-text-field
              v-model="form.password"
              label="Password"
              type="password"
              hint="Leave empty to keep existing password when editing"
              persistent-hint
              variant="outlined"
              class="mb-2"
            />
          </div>

          <!-- File Connection Fields -->
          <div v-else>
            <v-text-field
              v-model="form.filename"
              label="File Path *"
              hint="Path to the CSV file"
              persistent-hint
              :rules="[rules.required]"
              variant="outlined"
              class="mb-2"
            />
          </div>

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

          <!-- Advanced Options (MS Access) -->
          <v-expansion-panels v-if="form.driver === 'access' || form.driver === 'ucanaccess'" variant="accordion" class="mb-4">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon icon="mdi-cog" class="mr-2" />
                Advanced Options
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-text-field
                  v-model="ucanAccessDir"
                  label="UCanAccess Directory"
                  hint="Path to UCanAccess installation"
                  persistent-hint
                  variant="outlined"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
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
import { ref, computed, watch } from 'vue'
import { useDataSourceStore } from '@/stores/data-source'
import {
  getDefaultDataSourceForm,
  isDatabaseSource,
  type DataSourceConfig,
  type DataSourceFormData,
} from '@/types/data-source'

const props = defineProps<{
  modelValue: boolean
  dataSource?: DataSourceConfig | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: []
}>()

const dataSourceStore = useDataSourceStore()

// State
const formRef = ref()
const formValid = ref(false)
const form = ref<DataSourceFormData>(getDefaultDataSourceForm())
const ucanAccessDir = ref('')
const saving = ref(false)
const errorMessage = ref<string | null>(null)

// Computed
const isEditing = computed(() => !!props.dataSource)
const isDatabaseDriver = computed(() => isDatabaseSource(form.value.driver))

const driverOptions = [
  { title: 'PostgreSQL', value: 'postgresql' },
  { title: 'MS Access', value: 'access' },
  { title: 'SQLite', value: 'sqlite' },
  { title: 'CSV File', value: 'csv' },
]

// Validation rules
const rules = {
  required: (v: string | number) => !!v || 'Required',
  port: (v: number) => (v >= 1 && v <= 65535) || 'Port must be between 1 and 65535',
  unique: (v: string) => {
    if (isEditing.value && v === props.dataSource?.name) return true
    const existing = dataSourceStore.dataSourceByName(v)
    return !existing || 'Data source with this name already exists'
  },
}

// Methods
function handleDriverChange(newDriver: string) {
  // Set default port for database drivers
  if (newDriver === 'postgresql' || newDriver === 'postgres') {
    form.value.port = 5432
  } else if (newDriver === 'sqlite') {
    form.value.port = 0
  }
}

async function handleSave() {
  if (!formRef.value) return

  const { valid } = await formRef.value.validate()
  if (!valid) return

  saving.value = true
  errorMessage.value = null

  try {
    const config: DataSourceConfig = {
      name: form.value.name,
      driver: form.value.driver,
      description: form.value.description || null,
    }

    if (isDatabaseDriver.value) {
      config.host = form.value.host
      config.port = form.value.port
      config.database = form.value.database
      config.username = form.value.username
      
      // Only include password if provided
      if (form.value.password) {
        config.password = form.value.password
      }

      // Add MS Access specific options
      if ((form.value.driver === 'access' || form.value.driver === 'ucanaccess') && ucanAccessDir.value) {
        config.options = {
          ucanaccess_dir: ucanAccessDir.value,
        }
      }
    } else {
      config.filename = form.value.filename
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
  form.value = getDefaultDataSourceForm()
  ucanAccessDir.value = ''
  errorMessage.value = null
  formRef.value?.resetValidation()
}

function loadDataSource(dataSource: DataSourceConfig) {
  form.value = {
    name: dataSource.name,
    driver: dataSource.driver,
    host: dataSource.host || '',
    port: dataSource.port || 5432,
    database: dataSource.database || dataSource.dbname || '',
    username: dataSource.username || '',
    password: '', // Don't load existing password
    filename: dataSource.filename || dataSource.file_path || '',
    description: dataSource.description || '',
    options: dataSource.options || {},
  }

  // Load MS Access options
  if (dataSource.options?.ucanaccess_dir) {
    ucanAccessDir.value = dataSource.options.ucanaccess_dir as string
  }
}

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
