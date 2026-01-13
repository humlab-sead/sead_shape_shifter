<template>
  <v-menu
    v-model="isOpen"
    :style="menuStyle"
    :close-on-content-click="false"
    location="bottom left"
  >
    <template #activator="{ props: menuProps }">
      <!-- Invisible activator positioned at click location -->
      <div
        v-bind="menuProps"
        :style="activatorStyle"
        style="position: fixed; width: 1px; height: 1px; pointer-events: none;"
      />
    </template>
    
    <v-list density="compact" min-width="180">
      <v-list-item
        prepend-icon="mdi-eye"
        title="Preview Data"
        @click="handlePreview"
      />
      <v-list-item
        prepend-icon="mdi-content-copy"
        title="Duplicate Entity"
        @click="handleDuplicate"
      />
      <v-divider />
      <v-list-item
        prepend-icon="mdi-delete"
        title="Delete Entity"
        class="text-error"
        @click="handleDelete"
      />
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  modelValue: boolean
  x: number
  y: number
  entityName: string | null
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'preview', entityName: string): void
  (e: 'duplicate', entityName: string): void
  (e: 'delete', entityName: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const menuStyle = computed(() => ({
  position: 'fixed',
  left: `${props.x}px`,
  top: `${props.y}px`,
  zIndex: 9999,
}))

const activatorStyle = computed(() => ({
  left: `${props.x}px`,
  top: `${props.y}px`,
}))

function handlePreview() {
  if (props.entityName) {
    emit('preview', props.entityName)
  }
  isOpen.value = false
}

function handleDuplicate() {
  console.log('[GraphNodeContextMenu] handleDuplicate called for:', props.entityName)
  if (props.entityName) {
    console.log('[GraphNodeContextMenu] Emitting duplicate event')
    emit('duplicate', props.entityName)
  }
  isOpen.value = false
}

function handleDelete() {
  console.log('[GraphNodeContextMenu] handleDelete called for:', props.entityName)
  if (props.entityName) {
    console.log('[GraphNodeContextMenu] Emitting delete event')
    emit('delete', props.entityName)
  }
  isOpen.value = false
}
</script>

<style scoped>
.text-error {
  color: rgb(var(--v-theme-error));
}
</style>
