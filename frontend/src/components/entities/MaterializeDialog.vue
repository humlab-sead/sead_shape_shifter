<template>
  <v-dialog v-model="dialog" max-width="600">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-database-arrow-down</v-icon>
        Materialize Entity
      </v-card-title>

      <v-card-text>
        <v-alert
          v-if="!canMaterialize && validationResult"
          type="error"
          variant="tonal"
          class="mb-4"
        >
          <div class="text-subtitle-2 mb-2">Cannot Materialize</div>
          <ul class="ml-4">
            <li v-for="(error, idx) in validationResult.errors" :key="idx">
              {{ error }}
            </li>
          </ul>
        </v-alert>

        <v-alert v-else type="info" variant="tonal" class="mb-4">
          This will freeze the current entity data to fixed values, allowing it to be used in
          reconciliation. The original configuration will be saved for later restoration.
        </v-alert>

        <div v-if="canMaterialize">
          <v-select
            v-model="storageFormat"
            :items="storageFormats"
            label="Storage Format"
            variant="outlined"
            density="comfortable"
            class="mb-4"
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <template #prepend>
                  <v-icon>{{ item.raw.icon }}</v-icon>
                </template>
                <v-list-item-title>{{ item.raw.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ item.raw.subtitle }}</v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-select>
        </div>

      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="close">Cancel</v-btn>
        <v-btn
          color="primary"
          :disabled="!canMaterialize || loading"
          :loading="loading"
          @click="materialize"
        >
          Materialize
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useNotification } from '@/composables/useNotification'
import { materializationApi } from '@/api/materialization'
import type { CanMaterializeResponse } from '@/api/materialization'

const { success, error } = useNotification()

interface Props {
  modelValue: boolean
  projectName: string
  entityName: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'materialized': []
}>()

const dialog = ref(props.modelValue)
const loading = ref(false)
const validationResult = ref<CanMaterializeResponse | null>(null)
const canMaterialize = ref(false)
const storageFormat = ref<'parquet' | 'csv' | 'inline'>('parquet')

const storageFormats = [
  {
    value: 'parquet',
    title: 'Parquet (Recommended)',
    subtitle: 'Binary format, efficient for large datasets',
    icon: 'mdi-table-arrow-down',
  },
  {
    value: 'csv',
    title: 'CSV',
    subtitle: 'Human-readable, easy to edit externally',
    icon: 'mdi-file-delimited',
  },
  {
    value: 'inline',
    title: 'Inline YAML',
    subtitle: 'Stored directly in project file (best for small datasets)',
    icon: 'mdi-code-braces',
  },
]

watch(
  () => props.modelValue,
  (val) => {
    dialog.value = val
    if (val) {
      checkCanMaterialize()
    }
  }
)

watch(dialog, (val) => {
  emit('update:modelValue', val)
})

async function checkCanMaterialize() {
  loading.value = true
  try {
    const response = await materializationApi.canMaterialize(props.projectName, props.entityName)
    validationResult.value = response
    canMaterialize.value = response.can_materialize
  } catch (error: any) {
    console.error('Failed to check materialization:', error)
    const errorMessage = error.response?.data?.detail || error.message
    validationResult.value = {
      can_materialize: false,
      errors: [errorMessage],
    }
    canMaterialize.value = false
    error(`Failed to check materialization: ${errorMessage}`)
  } finally {
    loading.value = false
  }
}

async function materialize() {
  loading.value = true
  try {
    const result = await materializationApi.materialize(props.projectName, props.entityName, {
      storage_format: storageFormat.value,
    })
    
    const rowCount = result.rows_materialized?.toLocaleString() || 'unknown'
    const storageInfo = result.storage_file ? ` to ${result.storage_file}` : ' inline'
    success(`Successfully materialized ${rowCount} rows${storageInfo}`)
    
    emit('materialized')
    close()
  } catch (err: any) {
    console.error('Materialization failed:', err)
    const errorMessage = err.response?.data?.detail || err.message
    error(`Materialization failed: ${errorMessage}`)
  } finally {
    loading.value = false
  }
}

function close() {
  dialog.value = false
}
</script>
