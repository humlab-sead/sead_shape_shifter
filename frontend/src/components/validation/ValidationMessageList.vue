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
    >
      <template #prepend>
        <v-icon
          :icon="message.severity === 'error' ? 'mdi-alert-circle' : 'mdi-alert'"
          :color="message.severity === 'error' ? 'error' : 'warning'"
        />
      </template>

      <v-list-item-title>{{ message.message }}</v-list-item-title>

      <v-list-item-subtitle class="mt-1">
        <v-chip
          v-if="message.entity"
          size="x-small"
          variant="outlined"
          prepend-icon="mdi-cube"
          class="mr-1"
        >
          {{ message.entity }}
        </v-chip>
        <v-chip
          v-if="message.field"
          size="x-small"
          variant="outlined"
          prepend-icon="mdi-table-column"
          class="mr-1"
        >
          {{ message.field }}
        </v-chip>
        <v-chip
          v-if="message.code"
          size="x-small"
          variant="outlined"
          class="mr-1"
        >
          {{ message.code }}
        </v-chip>
      </v-list-item-subtitle>

      <template v-if="message.suggestion" #append>
        <v-tooltip location="top">
          <template #activator="{ props: tooltipProps }">
            <v-icon
              v-bind="tooltipProps"
              icon="mdi-lightbulb-outline"
              color="info"
              size="small"
            />
          </template>
          <span>{{ message.suggestion }}</span>
        </v-tooltip>
      </template>
    </v-list-item>
  </v-list>
</template>

<script setup lang="ts">
import type { ValidationError } from '@/types'

interface Props {
  messages: ValidationError[]
  emptyMessage?: string
}

withDefaults(defineProps<Props>(), {
  emptyMessage: 'No messages',
})
</script>
