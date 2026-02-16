<template>
  <v-dialog v-model="dialogModel" max-width="600" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-plus-circle" class="mr-2" />
        <span>Create New Project</span>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" v-model="formValid" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="projectName"
            label="Project Name or Path"
            :rules="nameRules"
            variant="outlined"
            density="comfortable"
            autofocus
            required
            hint="Enter a name (e.g., 'my-project') or path (e.g., 'arbodat/my-project'). Parent directories will be created automatically."
            persistent-hint
            class="mb-4"
          />

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
          :disabled="!formValid || !projectName"
          @click="handleSubmit"
        >
          Create
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useProjects } from '@/composables'

interface Props {
  modelValue: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'created', name: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { create, projects } = useProjects({ autoFetch: false })

// Form state
const formRef = ref()
const formValid = ref(false)
const projectName = ref('')
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
  (v: string) => v.length <= 100 || 'Name must be less than 100 characters',
  (v: string) => /^[a-zåäöA-ZÅÄÖ0-9_\-./]+$/.test(v) || 'Name can only contain letters, numbers, hyphens, underscores, and forward slashes',
  (v: string) => !v.includes('..') || 'Name cannot contain ".." for security reasons',
  (v: string) => !projects.value.some((c) => c.name === v) || 'A project with this name already exists',
]

// Methods
async function handleSubmit() {
  if (!formValid.value || !projectName.value) return

  // Validate form
  const { valid } = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  error.value = null

  try {
    await create({
      name: projectName.value,
      entities: {},
    })

    emit('created', projectName.value)
    handleClose()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to create project'
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  handleClose()
}

function handleClose() {
  projectName.value = ''
  error.value = null
  formRef.value?.reset()
  dialogModel.value = false
}

// Reset form when dialog opens
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      projectName.value = ''
      error.value = null
      formRef.value?.resetValidation()
    }
  }
)
</script>
