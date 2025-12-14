<template>
  <div class="empty-state text-center py-12">
    <v-icon
      :icon="icon"
      :size="iconSize"
      :color="iconColor"
      class="mb-4"
    />
    
    <h3 class="text-h6 mb-2">{{ title }}</h3>
    
    <p v-if="description" class="text-grey mb-4">
      {{ description }}
    </p>

    <slot name="actions">
      <v-btn
        v-if="actionText && actionIcon"
        :prepend-icon="actionIcon"
        color="primary"
        variant="flat"
        @click="$emit('action')"
      >
        {{ actionText }}
      </v-btn>
    </slot>
  </div>
</template>

<script setup lang="ts">
interface Props {
  icon?: string
  iconSize?: number
  iconColor?: string
  title: string
  description?: string
  actionText?: string
  actionIcon?: string
}

withDefaults(defineProps<Props>(), {
  icon: 'mdi-inbox',
  iconSize: 64,
  iconColor: 'grey',
})

defineEmits<{
  action: []
}>()
</script>

<style scoped>
.empty-state {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
</style>
