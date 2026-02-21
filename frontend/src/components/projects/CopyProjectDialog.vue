<template>
  <v-dialog v-model="dialogModel" max-width="600" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-content-copy" class="mr-2" />
        <span>Copy Project</span>
      </v-card-title>

      <v-card-text>
        <v-alert v-if="sourceName" type="info" variant="tonal" class="mb-4">
          Copying project: <strong>{{ sourceName }}</strong>
        </v-alert>

        <v-form ref="formRef" v-model="formValid" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="targetName"
            label="New Project Name"
            :rules="nameRules"
            variant="outlined"
            density="comfortable"
            autofocus
            required
            hint="Enter a unique name for the copy (with or without .yml extension)"
            persistent-hint
            class="mb-4"
          />

          <v-alert type="info" variant="tonal" density="compact" class="mt-2">
            <div class="text-body-2">
              <div class="mb-2"><strong>The following will be copied:</strong></div>
              <ul class="ml-4">
                <li>Project configuration (YAML file)</li>
                <li>Materialized files (if any exist)</li>
                <li>Reconciliation configuration (if exists)</li>
              </ul>
            </div>
          </v-alert>

          <v-alert v-if="error" type="error" variant="tonal" class="mt-4">
            {{ error }}
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
          :disabled="!formValid || !targetName"
          prepend-icon="mdi-content-copy"
          @click="handleSubmit"
        >
          Copy
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { projectsApi } from '@/api/projects'
import { useProjects } from '@/composables'

interface Props {
  modelValue: boolean
  sourceName: string | null
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'copied', targetName: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { projects } = useProjects({ autoFetch: false })

// Form state
const formRef = ref()
const formValid = ref(false)
const targetName = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

// Computed
const dialogModel = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

// Validation rules
const nameRules = [
  (v: string) => !!v || 'Project name is required',
  (v: string) => v.length >= 3 || 'Name must be at least 3 characters',
  (v: string) => v.length <= 50 || 'Name must be less than 50 characters',
  (v: string) =>
    /^[a-zA-Z0-9_-]+(?:\.yml)?$/.test(v) ||
    'Name can only contain letters, numbers, hyphens, and underscores (with optional .yml extension)',
  (v: string) => {
    const cleanName = v.replace(/\.yml$/, '')
    return !projects.value.some((c) => c.name === cleanName) || 'A project with this name already exists'
  },
]

// Methods
async function handleSubmit() {
  if (!formValid.value || !targetName.value || !props.sourceName) return

  // Validate form
  const { valid } = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  error.value = null

  try {
    await projectsApi.copy(props.sourceName, targetName.value)

    // Emit the clean name (without .yml)
    const cleanName = targetName.value.replace(/\.yml$/, '')
    emit('copied', cleanName)
    handleClose()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to copy project'
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  handleClose()
}

function handleClose() {
  targetName.value = ''
  error.value = null
  formRef.value?.reset()
  dialogModel.value = false
}

// Reset form when dialog opens
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      targetName.value = ''
      error.value = null
      formRef.value?.resetValidation()
    }
  }
)
</script>
