<template>
  <div class="monaco-text-editor-wrapper">
    <vue-monaco-editor
      v-model:value="content"
      :language="language"
      :options="editorOptions"
      :height="height"
      @change="handleChange"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

interface Props {
  modelValue: string
  language?: string
  height?: string
  readonly?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'change', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  language: 'markdown',
  height: '400px',
  readonly: false,
})

const emit = defineEmits<Emits>()

const content = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})

const editorOptions = computed(() => ({
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
  quickSuggestions: true,
  suggestOnTriggerCharacters: true,
  padding: { top: 8, bottom: 8 },
}))

function handleChange(value: string) {
  emit('change', value)
}
</script>

<style scoped>
.monaco-text-editor-wrapper {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  overflow: hidden;
}
</style>