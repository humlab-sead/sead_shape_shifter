<template>
  <v-alert
    :type="alertType"
    :variant="variant"
    prominent
    border="start"
    :closable="closable"
    @click:close="handleClose"
  >
    <v-alert-title v-if="title || errorType">
      {{ title || readableErrorType }}
      <v-chip
        v-if="errorType && title"
        :color="recoverable === false ? 'error' : 'warning'"
        size="x-small"
        class="ml-2"
      >
        {{ errorType }}
      </v-chip>
    </v-alert-title>

    <p class="mb-0">{{ message }}</p>

    <p v-if="details" class="text-caption mt-2 mb-0 preserve-whitespace">
      {{ details }}
    </p>

    <!-- Tips section (collapsible when many tips) -->
    <v-expand-transition>
      <div v-if="showTips && tips && tips.length > 0" class="error-tips mt-3">
        <div class="text-subtitle-2 mb-1">
          <v-icon size="small" class="mr-1">mdi-lightbulb-outline</v-icon>
          Suggestions:
        </div>
        <ul class="tips-list">
          <li v-for="(tip, index) in visibleTips" :key="index" class="text-body-2">
            {{ tip }}
          </li>
        </ul>
        <v-btn
          v-if="tips.length > maxVisibleTips"
          variant="text"
          size="small"
          class="mt-1"
          @click="showAllTips = !showAllTips"
        >
          {{ showAllTips ? 'Show less' : `Show ${tips.length - maxVisibleTips} more...` }}
        </v-btn>
      </div>
    </v-expand-transition>

    <!-- Context information for debugging (collapsible) -->
    <v-expand-transition>
      <div v-if="showContext && context && Object.keys(context).length > 0" class="mt-3">
        <details class="context-details">
          <summary class="text-caption cursor-pointer">
            <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
            Technical Details
          </summary>
          <pre class="context-data mt-1">{{ formatContext(context) }}</pre>
        </details>
      </div>
    </v-expand-transition>

    <!-- Action slot or default action button -->
    <template v-if="$slots.actions || actionText">
      <div class="mt-4">
        <slot name="actions">
          <v-btn
            v-if="actionText"
            :variant="recoverable === false ? 'outlined' : 'tonal'"
            :color="recoverable === false ? undefined : 'primary'"
            @click="$emit('action')"
          >
            {{ actionText }}
          </v-btn>
        </slot>
      </div>
    </template>
  </v-alert>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// Local type definition to avoid import issues
interface FormattedError {
  message: string
  detail?: string
  errorType?: string
  tips?: string[]
  context?: Record<string, any>
  recoverable?: boolean
}

interface Props {
  /** Alert type - auto-determined from recoverable if not set */
  type?: 'error' | 'warning' | 'success' | 'info'
  /** Alert variant style */
  variant?: 'elevated' | 'flat' | 'tonal' | 'outlined' | 'text' | 'plain'
  /** Custom title - uses readable errorType if not provided */
  title?: string
  /** Main error message */
  message: string
  /** Additional details */
  details?: string
  /** Actionable tips for the user */
  tips?: string[]
  /** Error type code from backend */
  errorType?: string
  /** Additional context data for debugging */
  context?: Record<string, any>
  /** Whether the error is recoverable (affects styling) */
  recoverable?: boolean
  /** Text for the action button */
  actionText?: string
  /** Whether the alert can be closed */
  closable?: boolean
  /** Whether to show tips section */
  showTips?: boolean
  /** Whether to show context section */
  showContext?: boolean
  /** Maximum tips to show before collapsing */
  maxVisibleTips?: number
}

const props = withDefaults(defineProps<Props>(), {
  type: undefined,
  variant: 'tonal',
  title: undefined,
  tips: undefined,
  errorType: undefined,
  context: undefined,
  recoverable: undefined,
  actionText: undefined,
  closable: false,
  showTips: true,
  showContext: false,
  maxVisibleTips: 3,
})

const emit = defineEmits<{
  action: []
  close: []
}>()

// State
const showAllTips = ref(false)

// Computed
const alertType = computed(() => {
  if (props.type) return props.type
  // Auto-determine based on recoverable flag
  return props.recoverable === false ? 'error' : 'warning'
})

const readableErrorType = computed(() => {
  if (!props.errorType) return ''
  // Convert SNAKE_CASE or PascalCase to readable format
  return props.errorType
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase())
})

const visibleTips = computed(() => {
  if (!props.tips) return []
  if (showAllTips.value || props.tips.length <= props.maxVisibleTips) {
    return props.tips
  }
  return props.tips.slice(0, props.maxVisibleTips)
})

// Methods
function formatContext(ctx: Record<string, any>): string {
  return JSON.stringify(ctx, null, 2)
}

function handleClose() {
  emit('close')
}

/**
 * Create props from a FormattedError object
 * Usage: <ErrorAlert v-bind="ErrorAlert.fromFormattedError(error)" />
 */
export function fromFormattedError(error: FormattedError): Partial<Props> {
  return {
    message: error.message,
    details: error.detail,
    tips: error.tips,
    errorType: error.errorType,
    context: error.context,
    recoverable: error.recoverable,
  }
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
}

.tips-list {
  margin: 0;
  padding-left: 1.2em;
}

.tips-list li {
  margin-bottom: 4px;
}

.tips-list li:last-child {
  margin-bottom: 0;
}

.context-details {
  background-color: rgba(var(--v-theme-surface-variant), 0.2);
  border-radius: 4px;
  padding: 8px 12px;
}

.context-data {
  background-color: rgba(var(--v-theme-surface), 0.5);
  border-radius: 4px;
  padding: 8px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  margin: 0;
}

.cursor-pointer {
  cursor: pointer;
}

.cursor-pointer:hover {
  text-decoration: underline;
}
</style>
