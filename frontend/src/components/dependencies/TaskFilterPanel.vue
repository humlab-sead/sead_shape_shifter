<template>
  <v-expansion-panels v-model="panel" variant="accordion">
    <v-expansion-panel value="filters">
      <v-expansion-panel-title>
        <template #default="{ expanded }">
          <v-row no-gutters align="center">
            <v-col cols="auto">
              <v-icon :icon="expanded ? 'mdi-filter' : 'mdi-filter-outline'" class="mr-2" />
            </v-col>
            <v-col>
              <span class="text-subtitle-2">Task Filters</span>
            </v-col>
            <v-col cols="auto" class="text-caption text-medium-emphasis">
              {{ activeFilterCount }} active
            </v-col>
          </v-row>
        </template>
      </v-expansion-panel-title>
      
      <v-expansion-panel-text>
        <v-list density="compact">
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

          <!-- Critical (errors) -->
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
        </v-list>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ProjectTaskStatus } from '@/composables/useTaskStatus'

export type TaskFilter = 'all' | 'todo' | 'done' | 'ignored' | 'blocked' | 'critical'

interface Props {
  /**
   * Current task status data
   */
  taskStatus: ProjectTaskStatus | null
  
  /**
   * Current filter selection
   */
  modelValue?: TaskFilter
}

interface Emits {
  (e: 'update:modelValue', value: TaskFilter): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: 'all'
})

const emit = defineEmits<Emits>()

// Panel state (null = collapsed, 'filters' = expanded)
const panel = ref<string | null>(null)

// Computed filter value
const selectedFilter = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Stats from task status
const stats = computed(() => props.taskStatus?.completion_stats)

// Count of blocked entities
const blockedCount = computed(() => {
  if (!props.taskStatus) return 0
  return Object.values(props.taskStatus.entities).filter(
    entity => entity.blocked_by && entity.blocked_by.length > 0
  ).length
})

// Count of critical entities (required + errors)
const criticalCount = computed(() => {
  if (!props.taskStatus) return 0
  return Object.values(props.taskStatus.entities).filter(
    entity => entity.priority === 'critical'
  ).length
})

// Count of active filters
const activeFilterCount = computed(() => {
  return selectedFilter.value === 'all' ? 0 : 1
})

/**
 * Select a filter
 */
function selectFilter(filter: TaskFilter) {
  selectedFilter.value = filter
}
</script>

<style scoped>
:deep(.v-expansion-panel-text__wrapper) {
  padding: 8px 0;
}
</style>
