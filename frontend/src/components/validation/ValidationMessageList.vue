<template>
  <div v-if="messages.length === 0" class="text-center py-8">
    <v-icon icon="mdi-check-circle" size="48" color="success" />
    <p class="text-body-1 mt-4">{{ emptyMessage }}</p>
  </div>

  <v-data-table
    v-else
    v-model:expanded="expandedRows"
    :headers="headers"
    :items="tableMessages"
    :items-per-page="-1"
    class="elevation-0 validation-message-table"
    density="compact"
    expand-on-click
    hide-default-footer
    hover
    item-value="rowKey"
    show-expand
  >
    <template #item.severity="{ item }">
      <div class="d-flex flex-column align-start">
        <div class="d-flex align-center" :data-severity="item.severity">
          <v-icon
            :icon="severityIcons[item.severity]"
            :color="severityColors[item.severity]"
            size="small"
            class="mr-2"
          />
          <span class="text-body-2">{{ formatSeverityLabel(item.severity) }}</span>
        </div>
        <span v-if="item.priority" class="text-caption text-medium-emphasis ml-6"> Priority: {{ item.priority }} </span>
      </div>
    </template>

    <template #item.message="{ item }">
      <div class="d-flex align-center ga-2">
        <v-tooltip location="top">
          <template #activator="{ props: tooltipProps }">
            <span v-bind="tooltipProps" class="validation-message-summary text-body-2">{{ item.message }}</span>
          </template>
          <span class="text-body-2">{{ item.message }}</span>
        </v-tooltip>
        <v-tooltip v-if="item.suggestion" location="top">
          <template #activator="{ props: tooltipProps }">
            <v-icon
              v-bind="tooltipProps"
              icon="mdi-lightbulb-outline"
              color="info"
              size="small"
              aria-label="Suggestion available"
            />
          </template>
          <span><strong>Suggestion:</strong> {{ item.suggestion }}</span>
        </v-tooltip>
      </div>
    </template>

    <template #item.location="{ item }">
      <div class="d-flex flex-column align-start">
        <button
          v-if="item.entity"
          type="button"
          class="validation-entity-link"
          @click.stop="handleOpenEntity(item.entity)"
        >
          {{ item.entity }}
          <v-icon icon="mdi-open-in-new" size="x-small" class="ml-1" />
        </button>
        <span v-if="item.field" class="text-caption text-medium-emphasis">{{ item.field }}</span>
        <span v-if="item.branch_name || item.branch_source" class="text-caption text-medium-emphasis">
          {{ formatBranchLabel(item.branch_name, item.branch_source) }}
        </span>
        <span
          v-if="!item.entity && !item.field && !item.branch_name && !item.branch_source"
          class="text-medium-emphasis"
        >
          -
        </span>
      </div>
    </template>

    <template #item.category="{ item }">
      <span class="text-body-2">{{ item.category || '-' }}</span>
    </template>

    <template #item.data-table-expand="{ internalItem, isExpanded, toggleExpand }">
      <v-btn
        class="validation-message-expand"
        :icon="isExpanded(internalItem) ? 'mdi-chevron-up' : 'mdi-chevron-down'"
        size="small"
        variant="text"
        :aria-label="isExpanded(internalItem) ? 'Collapse message' : 'Expand message'"
        :aria-expanded="isExpanded(internalItem)"
        @click.stop="toggleExpand(internalItem)"
      />
    </template>

    <template #expanded-row="{ columns, item }">
      <tr class="validation-message-details-row">
        <td :colspan="columns.length">
          <div class="pa-4">
            <div class="mb-3">
              <span class="text-caption text-medium-emphasis">Full message</span>
              <p class="text-body-2 mb-0 validation-message-full-text">{{ item.message }}</p>
            </div>

            <div class="d-flex flex-wrap ga-x-6 ga-y-2 mb-3">
              <div v-if="item.priority">
                <span class="text-caption text-medium-emphasis">Priority</span>
                <div class="text-body-2">{{ item.priority }}</div>
              </div>
              <div v-if="item.code">
                <span class="text-caption text-medium-emphasis">Code</span>
                <div class="text-body-2">
                  <code>{{ item.code }}</code>
                </div>
              </div>
              <div v-if="item.auto_fixable">
                <span class="text-caption text-medium-emphasis">Fix</span>
                <div class="text-body-2">Auto-fixable</div>
              </div>
              <div v-if="item.branch_name || item.branch_source">
                <span class="text-caption text-medium-emphasis">Branch / source</span>
                <div class="text-body-2">{{ formatBranchLabel(item.branch_name, item.branch_source) }}</div>
              </div>
            </div>

            <v-alert
              v-if="item.suggestion"
              type="info"
              variant="tonal"
              density="compact"
              class="validation-message-suggestion"
              @click.stop
            >
              <span class="text-body-2"><strong>Suggestion:</strong> {{ item.suggestion }}</span>
            </v-alert>
          </div>
        </td>
      </tr>
    </template>
  </v-data-table>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ValidationError, ValidationSeverity } from '@/types'

interface Props {
  messages: ValidationError[]
  emptyMessage?: string
}

interface ValidationTableMessage extends ValidationError {
  rowKey: string
}

interface Emits {
  (e: 'open-entity', entityName: string): void
}

const props = withDefaults(defineProps<Props>(), {
  emptyMessage: 'No messages',
})

const emit = defineEmits<Emits>()

const headers = [
  { title: 'Severity', key: 'severity', sortable: false, width: '130px' },
  { title: 'Message', key: 'message', sortable: false },
  { title: 'Location', key: 'location', sortable: false, width: '220px' },
  { title: 'Category', key: 'category', sortable: false, width: '130px' },
]

const severityIcons: Record<ValidationSeverity, string> = {
  error: 'mdi-alert-circle',
  warning: 'mdi-alert',
  info: 'mdi-information-outline',
}

const severityColors: Record<ValidationSeverity, string> = {
  error: 'error',
  warning: 'warning',
  info: 'info',
}

const tableMessages = computed<ValidationTableMessage[]>(() =>
  props.messages.map((message, index) => ({ ...message, rowKey: String(index) }))
)

const expandedRows = ref<string[]>([])

watch(
  () => props.messages,
  () => {
    expandedRows.value = []
  }
)

function formatSeverityLabel(severity: ValidationSeverity): string {
  return `${severity.charAt(0).toUpperCase()}${severity.slice(1)}`
}

function handleOpenEntity(entityName: string | null | undefined) {
  if (!entityName) {
    return
  }

  emit('open-entity', entityName)
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
.validation-message-summary {
  display: block;
  max-width: min(38rem, 100%);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.validation-entity-link {
  display: inline-flex;
  align-items: center;
  border: 0;
  padding: 0;
  color: rgb(var(--v-theme-primary));
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.validation-entity-link:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

.validation-message-full-text {
  overflow-wrap: anywhere;
}

.validation-message-details-row > td {
  background: rgba(var(--v-theme-on-surface), 0.03);
}

.validation-message-suggestion {
  cursor: text;
}
</style>
