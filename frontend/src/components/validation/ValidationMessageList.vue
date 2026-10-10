<template>
  <div v-if="messages.length === 0" class="text-center py-8">
    <v-icon icon="mdi-check-circle" size="48" color="success" />
    <p class="text-body-1 mt-4">{{ emptyMessage }}</p>
  </div>

  <v-list v-else>
    <v-list-item
      v-for="(message, index) in messages"
      :key="index"
      :value="index"
      class="validation-message-item"
      :class="{ 'validation-message-item--expanded': isExpanded(index) }"
      @click="toggleExpanded(index)"
    >
      <template #prepend>
        <v-icon
          :icon="message.severity === 'error' ? 'mdi-alert-circle' : 'mdi-alert'"
          :color="message.severity === 'error' ? 'error' : 'warning'"
        />
      </template>

      <v-list-item-title class="validation-message-text">{{ message.message }}</v-list-item-title>

      <v-list-item-subtitle class="mt-1">
        <v-chip v-if="message.priority" size="x-small" :color="getPriorityColor(message.priority)" class="mr-1">
          {{ message.priority.toUpperCase() }}
        </v-chip>
        <v-chip v-if="message.category" size="x-small" variant="outlined" prepend-icon="mdi-tag" class="mr-1">
          {{ message.category }}
        </v-chip>
        <v-chip
          v-if="message.entity"
          size="x-small"
          color="primary"
          variant="outlined"
          prepend-icon="mdi-cube"
          append-icon="mdi-open-in-new"
          class="mr-1 validation-entity-chip"
          @click.stop="handleOpenEntity(message.entity)"
        >
          {{ message.entity }}
        </v-chip>
        <v-chip
          v-if="message.branch_name || message.branch_source"
          size="x-small"
          color="teal"
          variant="outlined"
          class="mr-1"
        >
          {{ formatBranchLabel(message.branch_name, message.branch_source) }}
        </v-chip>
        <v-chip v-if="message.field" size="x-small" variant="outlined" prepend-icon="mdi-table-column" class="mr-1">
          {{ message.field }}
        </v-chip>
        <v-chip v-if="message.code" size="x-small" variant="outlined" class="mr-1">
          {{ message.code }}
        </v-chip>
        <v-chip
          v-if="message.auto_fixable"
          size="x-small"
          color="success"
          variant="outlined"
          prepend-icon="mdi-wrench"
          class="mr-1"
        >
          Auto-fixable
        </v-chip>
      </v-list-item-subtitle>

      <v-alert
        v-if="isExpanded(index) && message.suggestion"
        type="info"
        variant="tonal"
        density="compact"
        class="mt-3 validation-message-suggestion"
        @click.stop
      >
        <span class="text-body-2"><strong>Suggestion:</strong> {{ message.suggestion }}</span>
      </v-alert>

      <template #append>
        <div class="d-flex align-center">
          <v-tooltip v-if="message.suggestion && !isExpanded(index)" location="top">
            <template #activator="{ props: tooltipProps }">
              <v-icon v-bind="tooltipProps" icon="mdi-lightbulb-outline" color="info" size="small" class="mr-1" />
            </template>
            <span>{{ message.suggestion }}</span>
          </v-tooltip>
          <v-btn
            :icon="isExpanded(index) ? 'mdi-chevron-up' : 'mdi-chevron-down'"
            size="x-small"
            variant="text"
            :aria-label="isExpanded(index) ? 'Collapse message' : 'Expand message'"
            :aria-expanded="isExpanded(index)"
            @click.stop="toggleExpanded(index)"
          />
        </div>
      </template>
    </v-list-item>
  </v-list>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ValidationError, ValidationPriority } from '@/types'

interface Props {
  messages: ValidationError[]
  emptyMessage?: string
}

interface Emits {
  (e: 'open-entity', entityName: string): void
}

const props = withDefaults(defineProps<Props>(), {
  emptyMessage: 'No messages',
})

const emit = defineEmits<Emits>()

const expandedIndexes = ref<Set<number>>(new Set())

// Collapse every row when the displayed messages change (for example after re-validation or a tab switch).
watch(
  () => props.messages,
  () => {
    expandedIndexes.value = new Set()
  }
)

function isExpanded(index: number): boolean {
  return expandedIndexes.value.has(index)
}

function toggleExpanded(index: number) {
  const next = new Set(expandedIndexes.value)
  if (next.has(index)) {
    next.delete(index)
  } else {
    next.add(index)
  }
  expandedIndexes.value = next
}

function handleOpenEntity(entityName: string | null | undefined) {
  if (!entityName) {
    return
  }

  emit('open-entity', entityName)
}

function getPriorityColor(priority: ValidationPriority): string {
  const colors: Record<ValidationPriority, string> = {
    critical: 'error',
    high: 'orange-darken-2',
    medium: 'warning',
    low: 'grey',
  }
  return colors[priority] || 'grey'
}

function formatBranchLabel(branchName: string | null | undefined, branchSource: string | null | undefined): string {
  if (branchName && branchSource) {
    return `branch: ${branchName} (${branchSource})`
  }

  if (branchName) {
    return `branch: ${branchName}`
  }

  return `source: ${branchSource}`
}
</script>

<style scoped>
.validation-message-item {
  cursor: pointer;
}

.validation-entity-chip {
  cursor: pointer;
}

/* Expanded rows drop the single-line ellipsis so the full message is readable. */
.validation-message-item--expanded .validation-message-text {
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
  overflow-wrap: anywhere;
}

.validation-message-suggestion {
  cursor: text;
}
</style>
