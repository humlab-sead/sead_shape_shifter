<template>
  <v-dialog v-model="dialogModel" max-width="700" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-play-circle" class="mr-2" />
        <span>Execute Workflow</span>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" v-model="formValid" @submit.prevent="handleSubmit">
          <!-- Dispatcher Selection -->
          <v-select
            v-model="selectedDispatcher"
            :items="dispatchers"
            item-title="description"
            item-value="key"
            label="Output Format"
            variant="outlined"
            density="comfortable"
            :rules="[(v) => !!v || 'Please select an output format']"
            hint="Choose how to save the normalized data"
            persistent-hint
            class="mb-4"
          >
            <template v-slot:item="{ props: itemProps, item }">
              <v-list-item v-bind="itemProps">
                <template v-slot:prepend>
                  <v-icon :icon="getDispatcherIcon(item.raw.target_type)" />
                </template>
                <template v-slot:subtitle>
                  {{ item.raw.key }} ({{ item.raw.target_type }})
                </template>
              </v-list-item>
            </template>
          </v-select>

          <!-- File Target (for file dispatchers) -->
          <v-text-field
            v-if="selectedTargetType === 'file'"
            v-model="fileTarget"
            label="Output File Path"
            :rules="[(v) => !!v || 'File path is required']"
            variant="outlined"
            density="comfortable"
            :hint="`Default: ./output/${projectName}.${selectedDispatcher}`"
            persistent-hint
            class="mb-4"
          >
            <template v-slot:prepend-inner>
              <v-icon icon="mdi-file" />
            </template>
          </v-text-field>

          <!-- Folder Target (for folder dispatchers) -->
          <v-text-field
            v-if="selectedTargetType === 'folder'"
            v-model="folderTarget"
            label="Output Folder Path"
            :rules="[(v) => !!v || 'Folder path is required']"
            variant="outlined"
            density="comfortable"
            :hint="`Default: ./output/${projectName}`"
            persistent-hint
            class="mb-4"
          >
            <template v-slot:prepend-inner>
              <v-icon icon="mdi-folder" />
            </template>
          </v-text-field>

          <!-- Data Source Selection (for database dispatchers) -->
          <v-select
            v-if="selectedTargetType === 'database'"
            v-model="selectedDataSource"
            :items="dataSourceNames"
            label="Target Database"
            variant="outlined"
            density="comfortable"
            :rules="[(v) => !!v || 'Please select a target database']"
            hint="Choose the database to write normalized data to"
            persistent-hint
            class="mb-4"
          >
            <template v-slot:prepend-inner>
              <v-icon icon="mdi-database" />
            </template>
          </v-select>

          <!-- Options -->
          <v-divider class="my-4" />
          
          <v-switch
            v-model="runValidation"
            label="Run validation before execution"
            color="primary"
            density="comfortable"
            hint="Validate project configuration before running workflow"
            persistent-hint
            class="mb-2"
          />

          <v-switch
            v-model="translate"
            label="Apply translations"
            color="primary"
            density="comfortable"
            hint="Translate column names using configured mappings"
            persistent-hint
            class="mb-2"
          />

          <v-switch
            v-model="dropForeignKeys"
            label="Drop foreign key columns"
            color="primary"
            density="comfortable"
            hint="Remove foreign key columns from output"
            persistent-hint
            class="mb-2"
          />

          <!-- Error Display -->
          <v-alert v-if="error" type="error" variant="tonal" class="mt-4">
            {{ error }}
          </v-alert>

          <!-- Success Display -->
          <v-alert v-if="showSuccess && lastResult" type="success" variant="tonal" class="mt-4">
            <div class="font-weight-bold">{{ lastResult.message }}</div>
            <div class="text-caption mt-1">
              Processed {{ lastResult.entity_count }} entities to {{ lastResult.target }}
            </div>
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="handleCancel" :disabled="loading"> Cancel </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="loading"
          :disabled="!formValid || !canExecute"
          @click="handleSubmit"
        >
          <v-icon icon="mdi-play" class="mr-2" />
          Execute
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useExecuteStore } from '@/stores/execute'
import { useDataSourceStore } from '@/stores/data-source'

interface Props {
  modelValue: boolean
  projectName?: string
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'executed', result: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const executeStore = useExecuteStore()
const dataSourceStore = useDataSourceStore()

const { dispatchers, loading, error, lastResult } = storeToRefs(executeStore)
const { dataSources } = storeToRefs(dataSourceStore)

// Form state
const formRef = ref()
const formValid = ref(false)
const selectedDispatcher = ref<string>('')
const fileTarget = ref('')
const folderTarget = ref('')
const selectedDataSource = ref<string>('')
const runValidation = ref(true)
const translate = ref(false)
const dropForeignKeys = ref(false)
const showSuccess = ref(false)

// Computed
const dialogModel = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const projectName = computed(() => props.projectName || '')

const selectedTargetType = computed(() => {
  if (!selectedDispatcher.value) return null
  const dispatcher = dispatchers.value.find(d => d.key === selectedDispatcher.value)
  return dispatcher?.target_type || null
})

const dataSourceNames = computed(() => {
  return dataSources.value.map(ds => ds.name)
})

const targetValue = computed(() => {
  if (selectedTargetType.value === 'file') {
    return fileTarget.value || `./output/${projectName.value}.${selectedDispatcher.value}`
  } else if (selectedTargetType.value === 'folder') {
    return folderTarget.value || `./output/${projectName.value}`
  } else if (selectedTargetType.value === 'database') {
    return selectedDataSource.value
  }
  return ''
})

const canExecute = computed(() => {
  if (!selectedDispatcher.value) return false
  if (selectedTargetType.value === 'database' && !selectedDataSource.value) return false
  return true
})

// Methods
function getDispatcherIcon(targetType: string): string {
  switch (targetType) {
    case 'file':
      return 'mdi-file-document'
    case 'folder':
      return 'mdi-folder'
    case 'database':
      return 'mdi-database'
    default:
      return 'mdi-help-circle'
  }
}

async function handleSubmit() {
  if (!formValid.value || !canExecute.value || !projectName.value) return

  // Validate form
  const { valid } = await formRef.value.validate()
  if (!valid) return

  showSuccess.value = false

  try {
    const result = await executeStore.executeWorkflow(projectName.value, {
      dispatcher_key: selectedDispatcher.value,
      target: targetValue.value,
      run_validation: runValidation.value,
      translate: translate.value,
      drop_foreign_keys: dropForeignKeys.value,
      default_entity: null,
    })

    if (result.success) {
      showSuccess.value = true
      emit('executed', result)
      
      // Close dialog after 2 seconds on success
      setTimeout(() => {
        handleCancel()
      }, 2000)
    }
  } catch (err) {
    // Error is already set in store
    console.error('Execute workflow failed:', err)
  }
}

function handleCancel() {
  resetForm()
  emit('update:modelValue', false)
}

function resetForm() {
  selectedDispatcher.value = ''
  fileTarget.value = ''
  folderTarget.value = ''
  selectedDataSource.value = ''
  runValidation.value = true
  translate.value = false
  dropForeignKeys.value = false
  showSuccess.value = false
  executeStore.clearError()
  formRef.value?.resetValidation()
}

// Watch dialog open to fetch data
watch(() => props.modelValue, async (isOpen) => {
  if (isOpen) {
    // Fetch dispatchers
    if (dispatchers.value.length === 0) {
      await executeStore.fetchDispatchers()
    }
    
    // Fetch data sources
    if (dataSources.value.length === 0) {
      await dataSourceStore.fetchDataSources()
    }
    
    // Set default file/folder targets
    if (projectName.value) {
      fileTarget.value = `./output/${projectName.value}.xlsx`
      folderTarget.value = `./output/${projectName.value}`
    }
  } else {
    resetForm()
  }
})

// Auto-select first dispatcher if only one available
watch(dispatchers, (newDispatchers) => {
  if (newDispatchers.length === 1 && !selectedDispatcher.value) {
    selectedDispatcher.value = newDispatchers[0]?.key || ''
  }
})
</script>
