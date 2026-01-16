<template>
  <v-menu offset-y>
    <template #activator="{ props: menuProps }">
      <v-btn
        v-bind="menuProps"
        size="small"
        variant="tonal"
        prepend-icon="mdi-page-layout-body"
        append-icon="mdi-menu-down"
        :color="layoutType === 'custom' ? 'primary' : undefined"
        class="text-capitalize"
      >
        Layout: {{ layoutLabel }}
      </v-btn>
    </template>

    <v-list density="compact" min-width="220">
      <v-list-subheader>Graph Layout</v-list-subheader>
      
      <!-- Hierarchical Layout -->
      <v-list-item @click="selectLayout('hierarchical')">
        <template #prepend>
          <v-icon 
            :icon="layoutType === 'hierarchical' ? 'mdi-radiobox-marked' : 'mdi-radiobox-blank'"
            :color="layoutType === 'hierarchical' ? 'primary' : undefined"
          />
        </template>
        <template #append>
          <v-icon icon="mdi-file-tree" size="small" class="ml-2" />
        </template>
        <v-list-item-title>Hierarchical</v-list-item-title>
        <v-list-item-subtitle class="text-caption">Tree structure</v-list-item-subtitle>
      </v-list-item>

      <!-- Force Layout -->
      <v-list-item @click="selectLayout('force')">
        <template #prepend>
          <v-icon 
            :icon="layoutType === 'force' ? 'mdi-radiobox-marked' : 'mdi-radiobox-blank'"
            :color="layoutType === 'force' ? 'primary' : undefined"
          />
        </template>
        <template #append>
          <v-icon icon="mdi-vector-arrange-above" size="small" class="ml-2" />
        </template>
        <v-list-item-title>Force Directed</v-list-item-title>
        <v-list-item-subtitle class="text-caption">Physics-based</v-list-item-subtitle>
      </v-list-item>

      <!-- Custom Layout -->
      <v-list-item 
        @click="selectLayout('custom')"
        :disabled="!hasCustomLayout"
      >
        <template #prepend>
          <v-icon 
            :icon="layoutType === 'custom' ? 'mdi-radiobox-marked' : 'mdi-radiobox-blank'"
            :color="layoutType === 'custom' ? 'primary' : undefined"
          />
        </template>
        <template #append>
          <v-icon icon="mdi-cursor-move" size="small" class="ml-2" />
        </template>
        <v-list-item-title>Custom</v-list-item-title>
        <v-list-item-subtitle class="text-caption">
          {{ hasCustomLayout ? 'Saved positions' : 'Not saved yet' }}
        </v-list-item-subtitle>
      </v-list-item>

      <v-divider class="my-2" />

      <!-- Save as Custom -->
      <v-list-item 
        @click="$emit('save-custom')"
        :disabled="saving"
      >
        <template #prepend>
          <v-icon 
            icon="mdi-content-save" 
            :class="{ 'rotating': saving }"
          />
        </template>
        <v-list-item-title>
          {{ saving ? 'Saving...' : 'Save as Custom' }}
        </v-list-item-title>
        <v-list-item-subtitle class="text-caption">
          Save current positions
        </v-list-item-subtitle>
      </v-list-item>

      <!-- Clear Custom -->
      <v-list-item 
        v-if="hasCustomLayout"
        @click="$emit('clear-custom')"
      >
        <template #prepend>
          <v-icon icon="mdi-delete" color="error" />
        </template>
        <v-list-item-title>Clear Custom Layout</v-list-item-title>
        <v-list-item-subtitle class="text-caption">
          Remove saved positions
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export type LayoutType = 'hierarchical' | 'force' | 'custom'

interface Props {
  layoutType: LayoutType
  hasCustomLayout: boolean
  saving?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  layoutType: 'hierarchical',
  hasCustomLayout: false,
  saving: false
})

const emit = defineEmits<{
  (e: 'update:layoutType', value: LayoutType): void
  (e: 'save-custom'): void
  (e: 'clear-custom'): void
}>()

const layoutLabel = computed(() => {
  switch (props.layoutType) {
    case 'hierarchical': return 'Hierarchical'
    case 'force': return 'Force'
    case 'custom': return 'Custom'
    default: return 'Unknown'
  }
})

function selectLayout(layout: LayoutType) {
  if (layout === 'custom' && !props.hasCustomLayout) {
    return // Disabled
  }
  emit('update:layoutType', layout)
}
</script>

<style scoped>
@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.rotating {
  animation: rotate 1s linear infinite;
}
</style>
