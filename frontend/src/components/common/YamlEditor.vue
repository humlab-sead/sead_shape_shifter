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

interface Props {
  modelValue: string
  height?: string
  readonly?: boolean
  validateOnChange?: boolean
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
})

const emit = defineEmits<Emits>()

const content = ref(props.modelValue)
const error = ref<string | null>(null)

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

function handleMount(editor: any) {
  // Editor mounted - can add custom functionality here
  console.log('Monaco editor mounted')
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
</script>

<style scoped>
.yaml-editor-wrapper {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  overflow: hidden;
}
</style>
