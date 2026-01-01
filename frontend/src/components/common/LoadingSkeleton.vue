<template>
  <v-card :variant="variant" :class="containerClass">
    <v-card-text>
      <v-skeleton-loader v-for="n in count" :key="n" :type="type" :class="{ 'mb-2': n < count }" />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
interface Props {
  type?: string
  count?: number
  variant?: 'elevated' | 'flat' | 'tonal' | 'outlined' | 'text' | 'plain'
  containerClass?: string
}

withDefaults(defineProps<Props>(), {
  type: 'list-item-avatar-two-line',
  count: 3,
  variant: 'outlined',
  containerClass: '',
})
</script>
