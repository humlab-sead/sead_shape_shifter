<template>
  <div class="yaml-editor-wrapper">
    <vue-monaco-editor
      v-model:value="content"
      language="yaml"
      :options="editorOptions"
      :height="height"
      @mount="handleMount"
      @change="handleChange"
    />

    <!-- Validation Errors -->
    <v-alert
      v-if="error"
      type="error"
      density="compact"
      variant="tonal"
      class="mt-2"
      closable
      @click:close="error = null"
    >
      <div class="text-caption font-weight-bold">YAML Parse Error</div>
      <div class="text-caption">{{ error }}</div>
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import * as yaml from 'js-yaml'
import { setupYamlIntelligence } from '@/composables/useMonacoYamlIntelligence'
import { validateProjectYaml, type ValidationContext } from '@/utils/projectYamlValidator'
import { registerProjectCompletions } from '@/utils/projectYamlCompletions'
import type * as monacoType from 'monaco-editor'

interface Props {
  modelValue: string
  height?: string
  readonly?: boolean
  validateOnChange?: boolean
  mode?: 'project' | 'entity'
  validationContext?: ValidationContext
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'validate', isValid: boolean, error?: string): void
  (e: 'change', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  height: '400px',
  readonly: false,
  validateOnChange: true,
  mode: 'project',
})

const emit = defineEmits<Emits>()

const content = ref(props.modelValue)
const error = ref<string | null>(null)
const editor = ref<monacoType.editor.IStandaloneCodeEditor | null>(null)
const model = ref<monacoType.editor.ITextModel | null>(null)
const monacoInstance = ref<typeof monacoType | null>(null)
const intelligenceInitialized = ref(false)

// Monaco editor options
const editorOptions = {
  automaticLayout: true,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  fontSize: 13,
  lineNumbers: 'on' as const,
  roundedSelection: false,
  readOnly: props.readonly,
  theme: 'vs-dark',
  wordWrap: 'on' as const,
  folding: true,
  tabSize: 2,
  insertSpaces: true,
  scrollbar: {
    vertical: 'auto' as const,
    horizontal: 'auto' as const,
  },
}

function handleMount(editorInstance: monacoType.editor.IStandaloneCodeEditor, monacoRef: typeof monacoType) {
  editor.value = editorInstance
  model.value = editorInstance.getModel()
  monacoInstance.value = monacoRef

  // Initialize YAML intelligence once
  if (!intelligenceInitialized.value && monacoRef) {
    setupYamlIntelligence(monacoRef, {
      mode: props.mode,
      context: props.validationContext
    })

    // Register custom completions with context provider
    registerProjectCompletions(
      monacoRef,
      props.validationContext ? () => props.validationContext : undefined
    )

    intelligenceInitialized.value = true
  }

  // Run initial validation if context is provided
  if (props.validationContext && model.value && monacoRef) {
    runCustomValidation(monacoRef)
  }
}

function runCustomValidation(monaco: typeof monacoType) {
  if (!model.value) return

  const markers = validateProjectYaml(
    content.value,
    model.value,
    props.validationContext
  )

  monaco.editor.setModelMarkers(model.value, 'yaml-custom', markers)
}

function validateYaml(yamlContent: string): { valid: boolean; error?: string } {
  try {
    yaml.load(yamlContent)
    return { valid: true }
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : 'Invalid YAML syntax'
    return { valid: false, error: errorMsg }
  }
}

function handleChange(value: string) {
  content.value = value
  emit('update:modelValue', value)
  emit('change', value)

  // Validate if enabled
  if (props.validateOnChange) {
    const validation = validateYaml(value)
    error.value = validation.error || null
    emit('validate', validation.valid, validation.error)

    // Run custom validation if we have context
    if (props.validationContext && monacoInstance.value) {
      runCustomValidation(monacoInstance.value)
    }
  }
}

// Watch for external changes
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue !== content.value) {
      content.value = newValue
    }
  }
)

// Re-validate when context changes
watch(
  () => props.validationContext,
  () => {
    if (props.validationContext && monacoInstance.value) {
      runCustomValidation(monacoInstance.value)
    }
  },
  { deep: true }
)
</script>

<style scoped>
.yaml-editor-wrapper {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  overflow: hidden;
}
</style>
