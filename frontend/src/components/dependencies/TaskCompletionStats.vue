<template>
  <v-card
    v-if="taskStatus"
    variant="flat"
    class="task-completion-card"
  >
    <v-card-text class="pa-2">
      <v-row no-gutters align="center">
        <!-- Icon -->
        <v-col cols="auto" class="mr-2">
          <v-icon 
            :icon="completionIcon" 
            :color="completionColor"
            size="small"
          />
        </v-col>

        <!-- Stats text -->
        <v-col>
          <div class="text-caption">
            <span class="font-weight-medium">{{ stats.completed }}</span>
            <span class="text-medium-emphasis"> of </span>
            <span class="font-weight-medium">{{ stats.total }}</span>
            <span class="text-medium-emphasis"> complete</span>
          </div>
        </v-col>

        <!-- Percentage badge -->
        <v-col cols="auto" class="ml-2">
          <v-chip
            :color="completionColor"
            size="small"
            variant="flat"
          >
            {{ Math.round(stats.completion_percentage) }}%
          </v-chip>
        </v-col>
      </v-row>

      <!-- Progress bar -->
      <v-progress-linear
        :model-value="stats.completion_percentage"
        :color="completionColor"
        height="4"
        rounded
        class="mt-2"
      />

      <!-- Breakdown (optional, shown on hover/click) -->
      <v-expand-transition>
        <div v-if="showDetails" class="mt-2 text-caption">
          <v-row no-gutters dense>
            <v-col cols="6">
              <v-icon icon="mdi-circle-outline" size="x-small" class="mr-1" />
              To Do: {{ stats.todo }}
            </v-col>
            <v-col cols="6">
              <v-icon icon="mdi-cancel" size="x-small" class="mr-1" />
              Ignored: {{ stats.ignored }}
            </v-col>
          </v-row>
        </div>
      </v-expand-transition>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ProjectTaskStatus } from '@/composables/useTaskStatus'

interface Props {
  /**
   * Task status data
   */
  taskStatus: ProjectTaskStatus | null
  
  /**
   * Whether to show detailed breakdown
   */
  showDetails?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showDetails: false
})

// Completion stats
const stats = computed(() => {
  if (!props.taskStatus) {
    return {
      total: 0,
      completed: 0,
      ignored: 0,
      todo: 0,
      completion_percentage: 0
    }
  }
  return props.taskStatus.completion_stats
})

// Completion color based on percentage
const completionColor = computed(() => {
  const percentage = stats.value.completion_percentage
  if (percentage === 100) return 'success'
  if (percentage >= 75) return 'info'
  if (percentage >= 50) return 'warning'
  return 'error'
})

// Completion icon
const completionIcon = computed(() => {
  const percentage = stats.value.completion_percentage
  if (percentage === 100) return 'mdi-check-circle'
  if (percentage >= 75) return 'mdi-progress-check'
  if (percentage >= 25) return 'mdi-progress-clock'
  return 'mdi-clock-outline'
})
</script>

<style scoped>
.task-completion-card {
  border: 1px solid rgba(var(--v-border-color), 0.12);
}
</style>
