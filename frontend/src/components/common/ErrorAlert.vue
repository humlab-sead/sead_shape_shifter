<template>
  <v-alert :type="type" :variant="variant" prominent border="start" :closable="closable">
    <v-alert-title v-if="title">{{ title }}</v-alert-title>

    <p>{{ message }}</p>

    <p v-if="details" class="text-caption mt-2">
      {{ details }}
    </p>

    <slot name="actions">
      <v-btn v-if="actionText" variant="outlined" class="mt-4" @click="$emit('action')">
        {{ actionText }}
      </v-btn>
    </slot>
  </v-alert>
</template>

<script setup lang="ts">
interface Props {
  type?: 'error' | 'warning' | 'success' | 'info'
  variant?: 'elevated' | 'flat' | 'tonal' | 'outlined' | 'text' | 'plain'
  title?: string
  message: string
  details?: string
  actionText?: string
  closable?: boolean
}

withDefaults(defineProps<Props>(), {
  type: 'error',
  variant: 'tonal',
  closable: false,
})

defineEmits<{
  action: []
}>()
</script>
