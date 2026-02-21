<template>
  <v-alert :type="type" :variant="variant" prominent border="start" :closable="closable">
    <v-alert-title v-if="title || errorType">
      {{ title || formattedErrorType }}
      <v-chip
        v-if="errorType && title"
        :color="recoverable === false ? 'error' : 'warning'"
        size="x-small"
        class="ml-2"
      >
        {{ formattedErrorType }}
      </v-chip>
    </v-alert-title>

    <p>{{ message }}</p>

    <p v-if="details" class="text-caption mt-2 preserve-whitespace">
      {{ details }}
    </p>

    <div v-if="tips && tips.length > 0" class="error-tips mt-3">
      <div class="text-subtitle-2 mb-1">💡 Troubleshooting Tips:</div>
      <ul class="ml-4">
        <li v-for="(tip, index) in tips" :key="index" class="text-body-2">
          {{ tip }}
        </li>
      </ul>
    </div>

    <!-- Context information for debugging (collapsible) -->
    <v-expansion-panels v-if="context && Object.keys(context).length > 0" class="mt-3">
      <v-expansion-panel>
        <v-expansion-panel-title class="text-caption">
          <v-icon size="small" class="mr-2">mdi-information-outline</v-icon>
          Additional Context
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <pre class="text-caption context-data">{{ formatContext(context) }}</pre>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <slot name="actions">
      <v-btn v-if="actionText" variant="outlined" class="mt-4" @click="$emit('action')">
        {{ actionText }}
      </v-btn>
    </slot>
  </v-alert>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  type?: 'error' | 'warning' | 'success' | 'info'
  variant?: 'elevated' | 'flat' | 'tonal' | 'outlined' | 'text' | 'plain'
  title?: string
  message: string
  details?: string
  tips?: string[]
  errorType?: string
  context?: Record<string, any>
  recoverable?: boolean
  actionText?: string
  closable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'error',
  variant: 'tonal',
  tips: undefined,
  errorType: undefined,
  context: undefined,
  recoverable: undefined,
  closable: false,
})

defineEmits<{
  action: []
}>()

/**
 * Format error type for display
 * Converts SNAKE_CASE or PascalCase to readable format
 */
const formattedErrorType = computed(() => {
  if (!props.errorType) return ''
  return props.errorType
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase())
})

/**
 * Format context object for display
 */
function formatContext(ctx: Record<string, any>): string {
  return JSON.stringify(ctx, null, 2)
}
</script>

<style scoped>
.preserve-whitespace {
  white-space: pre-line;
}

.error-tips {
  background-color: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 4px;
  padding: 12px;
  margin-top: 12px;
}

.error-tips ul {
  margin: 0;
  padding-left: 1.2em;
}

.error-tips li {
  margin-bottom: 4px;
}

.error-tips li:last-child {
  margin-bottom: 0;
}

.context-data {
  background-color: rgba(var(--v-theme-surface), 0.5);
  border-radius: 4px;
  padding: 8px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
}
</style>
