<template>
  <div class="sql-editor-wrapper">
    <div class="text-caption text-medium-emphasis mb-1">SQL Query</div>
    <vue-monaco-editor
      v-model:value="content"
      language="sql"
      :options="editorOptions"
      :height="height"
      @mount="handleMount"
      @change="handleChange"
    />

    <!-- Help Text -->
    <div v-if="showHelp" class="text-caption text-medium-emphasis mt-1">
      {{ helpText }}
    </div>

    <!-- Validation Error -->
    <div v-if="error" class="text-caption text-error mt-1">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

interface Props {
  modelValue: string
  height?: string
  readonly?: boolean
  helpText?: string
  showHelp?: boolean
  error?: string
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'change', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  height: '250px',
  readonly: false,
  helpText: 'SQL query to execute',
  showHelp: true,
  error: '',
})

const emit = defineEmits<Emits>()

const content = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})

const editorOptions = computed(() => ({
  minimap: { enabled: false },
  fontSize: 13,
  lineNumbers: 'on' as const,
  scrollBeyondLastLine: true,
  wordWrap: 'on' as const,
  automaticLayout: true,
  tabSize: 2,
  readOnly: props.readonly,
  scrollbar: {
    vertical: 'visible' as const,
    horizontal: 'visible' as const,
    useShadows: false,
    verticalScrollbarSize: 10,
    horizontalScrollbarSize: 10,
    alwaysConsumeMouseWheel: false,
  },
  renderLineHighlight: 'line' as const,
  quickSuggestions: true,
  suggestOnTriggerCharacters: true,
  acceptSuggestionOnEnter: 'on' as const,
  padding: { top: 8, bottom: 8 },
  fixedOverflowWidgets: true,
}))

function handleMount(editor: any) {
  // Configure SQL language features
  editor.updateOptions({
    suggest: {
      showKeywords: true,
      showSnippets: true,
    },
  })
}

function handleChange(value: string) {
  emit('change', value)
}
</script>

<style scoped>
.sql-editor-wrapper {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.sql-editor-wrapper:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
}

.sql-editor-wrapper:focus-within {
  border-color: rgb(var(--v-theme-primary));
  border-width: 2px;
}
</style>
