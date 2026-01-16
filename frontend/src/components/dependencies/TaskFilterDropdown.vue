<template>
  <v-menu offset-y>
    <template #activator="{ props: menuProps }">
      <v-btn
        v-bind="menuProps"
        size="small"
        variant="tonal"
        prepend-icon="mdi-filter-outline"
        append-icon="mdi-menu-down"
        :color="selectedFilter !== 'all' ? 'primary' : undefined"
        class="text-capitalize"
      >
        Tasks
        <v-badge
          v-if="activeFilterCount > 0 && selectedFilter !== 'all'"
          :content="activeFilterCount"
          color="primary"
          inline
          class="ml-1"
        />
      </v-btn>
    </template>

    <v-list density="compact" min-width="220">
      <!-- Show All -->
      <v-list-item
        :active="selectedFilter === 'all'"
        @click="selectFilter('all')"
      >
        <template #prepend>
          <v-icon icon="mdi-view-grid" />
        </template>
        <v-list-item-title>Show All</v-list-item-title>
        <template #append>
          <v-chip size="x-small" variant="flat">
            {{ stats?.total ?? 0 }}
          </v-chip>
        </template>
      </v-list-item>

      <v-divider class="my-2" />

      <!-- Todo -->
      <v-list-item
        :active="selectedFilter === 'todo'"
        @click="selectFilter('todo')"
      >
        <template #prepend>
          <v-icon icon="mdi-circle-outline" color="grey" />
        </template>
        <v-list-item-title>To Do</v-list-item-title>
        <template #append>
          <v-chip size="x-small" color="grey" variant="flat">
            {{ stats?.todo ?? 0 }}
          </v-chip>
        </template>
      </v-list-item>

      <!-- Done -->
      <v-list-item
        :active="selectedFilter === 'done'"
        @click="selectFilter('done')"
      >
        <template #prepend>
          <v-icon icon="mdi-check-circle" color="success" />
        </template>
        <v-list-item-title>Complete</v-list-item-title>
        <template #append>
          <v-chip size="x-small" color="success" variant="flat">
            {{ stats?.completed ?? 0 }}
          </v-chip>
        </template>
      </v-list-item>

      <!-- Ignored -->
      <v-list-item
        :active="selectedFilter === 'ignored'"
        @click="selectFilter('ignored')"
      >
        <template #prepend>
          <v-icon icon="mdi-cancel" color="grey-darken-2" />
        </template>
        <v-list-item-title>Ignored</v-list-item-title>
        <template #append>
          <v-chip size="x-small" color="grey-darken-2" variant="flat">
            {{ stats?.ignored ?? 0 }}
          </v-chip>
        </template>
      </v-list-item>

      <!-- Blocked -->
      <v-list-item
        :active="selectedFilter === 'blocked'"
        @click="selectFilter('blocked')"
      >
        <template #prepend>
          <v-icon icon="mdi-alert" color="warning" />
        </template>
        <v-list-item-title>Blocked</v-list-item-title>
        <template #append>
          <v-chip size="x-small" color="warning" variant="flat">
            {{ blockedCount }}
          </v-chip>
        </template>
      </v-list-item>

      <!-- Critical -->
      <v-list-item
        :active="selectedFilter === 'critical'"
        @click="selectFilter('critical')"
      >
        <template #prepend>
          <v-icon icon="mdi-alert-circle" color="error" />
        </template>
        <v-list-item-title>Critical</v-list-item-title>
        <template #append>
          <v-chip size="x-small" color="error" variant="flat">
            {{ criticalCount }}
          </v-chip>
        </template>
      </v-list-item>

      <template v-if="!taskStatus || (stats?.total ?? 0) === 0">
        <v-divider class="my-2" />
        <v-list-item disabled>
          <v-list-item-title class="text-caption text-medium-emphasis">
            <v-icon icon="mdi-information-outline" size="small" class="mr-1" />
            {{ !taskStatus ? 'Task list not initialized' : 'No entities yet' }}
          </v-list-item-title>
        </v-list-item>
        
        <v-list-item v-if="!taskStatus" @click="$emit('initialize')">
          <template #prepend>
            <v-icon icon="mdi-plus-circle" color="primary" />
          </template>
          <v-list-item-title>Initialize Task List</v-list-item-title>
        </v-list-item>
      </template>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ProjectTaskStatus, EntityTaskStatus } from '@/composables/useTaskStatus'

export type TaskFilter = 'all' | 'todo' | 'done' | 'ignored' | 'blocked' | 'critical'

interface Props {
  modelValue: TaskFilter
  taskStatus: ProjectTaskStatus | null
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: 'all',
  taskStatus: null
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: TaskFilter): void
  (e: 'initialize'): void
}>()

const selectedFilter = computed({
  get: () => props.modelValue,
  set: (value: TaskFilter) => emit('update:modelValue', value)
})

// Compute statistics from task status
const stats = computed(() => {
  if (!props.taskStatus) return null

  const entities = Object.values(props.taskStatus.entities) as EntityTaskStatus[]
  return {
    total: entities.length,
    todo: entities.filter(e => e.status === 'todo').length,
    completed: entities.filter(e => e.status === 'done').length,
    ignored: entities.filter(e => e.status === 'ignored').length,
  }
})

const blockedCount = computed(() => {
  if (!props.taskStatus) return 0
  const entities = Object.values(props.taskStatus.entities) as EntityTaskStatus[]
  return entities.filter(e => e.blocked_by && e.blocked_by.length > 0).length
})

const criticalCount = computed(() => {
  if (!props.taskStatus) return 0
  const entities = Object.values(props.taskStatus.entities) as EntityTaskStatus[]
  return entities.filter(e => e.priority === 'critical').length
})

const activeFilterCount = computed(() => {
  if (!props.taskStatus) return 0
  
  switch (selectedFilter.value) {
    case 'all': return stats.value?.total ?? 0
    case 'todo': return stats.value?.todo ?? 0
    case 'done': return stats.value?.completed ?? 0
    case 'ignored': return stats.value?.ignored ?? 0
    case 'blocked': return blockedCount.value
    case 'critical': return criticalCount.value
    default: return 0
  }
})

function selectFilter(filter: TaskFilter) {
  selectedFilter.value = filter
}
</script>
