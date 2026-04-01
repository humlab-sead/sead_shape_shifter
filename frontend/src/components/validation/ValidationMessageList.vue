<template>
  <div v-if="messages.length === 0" class="text-center py-8">
    <v-icon icon="mdi-check-circle" size="48" color="success" />
    <p class="text-body-1 mt-4">{{ emptyMessage }}</p>
  </div>

  <v-list v-else>
    <v-list-item v-for="(message, index) in messages" :key="index" :value="index">
      <template #prepend>
        <v-icon
          :icon="message.severity === 'error' ? 'mdi-alert-circle' : 'mdi-alert'"
          :color="message.severity === 'error' ? 'error' : 'warning'"
        />
      </template>

      <v-list-item-title>{{ message.message }}</v-list-item-title>

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
          @click="handleOpenEntity(message.entity)"
        >
          {{ message.entity }}
        </v-chip>
        <v-chip v-if="message.branch_name || message.branch_source" size="x-small" color="teal" variant="outlined" class="mr-1">
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

      <template v-if="message.suggestion" #append>
        <v-tooltip location="top">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" icon="mdi-lightbulb-outline" color="info" size="small" />
          </template>
          <span>{{ message.suggestion }}</span>
        </v-tooltip>
      </template>
    </v-list-item>
  </v-list>
</template>

<script setup lang="ts">
import type { ValidationError, ValidationPriority } from '@/types'

interface Props {
  messages: ValidationError[]
  emptyMessage?: string
}

interface Emits {
  (e: 'open-entity', entityName: string): void
}

withDefaults(defineProps<Props>(), {
  emptyMessage: 'No messages',
})

const emit = defineEmits<Emits>()

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
.validation-entity-chip {
  cursor: pointer;
}
</style>
