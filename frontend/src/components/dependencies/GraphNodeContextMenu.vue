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
    
    <v-list density="compact" min-width="200">
      <v-list-item
        prepend-icon="mdi-pencil"
        title="Edit Entity"
        @click="handleEdit"
      />
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
      
      <!-- Task Status Actions -->
      <template v-if="taskStatus">
        <v-divider />
        
        <!-- Mark as Done -->
        <v-list-item
          v-if="canMarkComplete"
          prepend-icon="mdi-check-circle"
          title="Mark as Done"
          @click="handleMarkComplete"
        />
        
        <!-- Mark as Ignored -->
        <v-list-item
          v-if="taskStatus.status !== 'ignored'"
          prepend-icon="mdi-cancel"
          title="Mark as Ignored"
          @click="handleMarkIgnored"
        />
        
        <!-- Reset Status -->
        <v-list-item
          v-if="taskStatus.status !== 'todo'"
          prepend-icon="mdi-refresh"
          title="Reset Status"
          @click="handleResetStatus"
        />
      </template>
      
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
import type { EntityTaskStatus } from '@/composables/useTaskStatus'

interface Props {
  modelValue: boolean
  x: number
  y: number
  entityName: string | null
  taskStatus?: EntityTaskStatus
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'edit', entityName: string): void
  (e: 'preview', entityName: string): void
  (e: 'duplicate', entityName: string): void
  (e: 'delete', entityName: string): void
  (e: 'mark-complete', entityName: string): void
  (e: 'mark-ignored', entityName: string): void
  (e: 'reset-status', entityName: string): void
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

// Can mark complete if entity exists, validation passed, and preview available
const canMarkComplete = computed(() => {
  if (!props.taskStatus) return false
  return (
    props.taskStatus.exists &&
    props.taskStatus.validation_passed &&
    props.taskStatus.preview_available &&
    props.taskStatus.status !== 'done'
  )
})

function handleEdit() {
  if (props.entityName) {
    emit('edit', props.entityName)
  }
  isOpen.value = false
}

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

function handleMarkComplete() {
  if (props.entityName) {
    emit('mark-complete', props.entityName)
  }
  isOpen.value = false
}

function handleMarkIgnored() {
  if (props.entityName) {
    emit('mark-ignored', props.entityName)
  }
  isOpen.value = false
}

function handleResetStatus() {
  if (props.entityName) {
    emit('reset-status', props.entityName)
  }
  isOpen.value = false
}
</script>

<style scoped>
.text-error {
  color: rgb(var(--v-theme-error));
}
</style>
