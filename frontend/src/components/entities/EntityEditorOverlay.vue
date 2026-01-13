<template>
  <v-overlay v-model="isOpen" class="entity-editor-overlay" persistent :scrim="true" @click:outside="handleClose">
    <transition name="slide-from-right">
      <v-card v-if="isOpen" class="overlay-panel" elevation="24">
        <v-toolbar color="primary" density="compact">
          <v-toolbar-title>
            <v-icon icon="mdi-pencil" class="mr-2" />
            Edit {{ entityName }}
          </v-toolbar-title>
          <v-spacer />
          
          <!-- View mode toggle -->
          <v-btn-toggle v-model="viewMode" mandatory density="compact" class="mr-2">
            <v-btn value="form" size="small">
              <v-icon size="small">mdi-form-select</v-icon>
              <v-tooltip activator="parent" location="bottom">Form Only</v-tooltip>
            </v-btn>
            <v-btn value="both" size="small">
              <v-icon size="small">mdi-view-split-vertical</v-icon>
              <v-tooltip activator="parent" location="bottom">Split View</v-tooltip>
            </v-btn>
            <v-btn value="preview" size="small">
              <v-icon size="small">mdi-table</v-icon>
              <v-tooltip activator="parent" location="bottom">Preview Only</v-tooltip>
            </v-btn>
          </v-btn-toggle>

          <v-btn icon @click="handleClose">
            <v-icon>mdi-close</v-icon>
            <v-tooltip activator="parent" location="bottom">Close (Esc)</v-tooltip>
          </v-btn>
        </v-toolbar>

        <v-tabs v-model="activeTab" bg-color="primary">
          <v-tab value="basic">Basic</v-tab>
          <v-tab value="relationships">Foreign Keys</v-tab>
          <v-tab value="filters">Filters</v-tab>
          <v-tab value="unnest">Unnest</v-tab>
          <v-tab value="append">Append</v-tab>
          <v-tab value="extra_columns">Extra Columns</v-tab>
          <v-tab value="yaml">
            <v-icon icon="mdi-code-braces" class="mr-1" size="small" />
            YAML
          </v-tab>
        </v-tabs>

        <v-card-text class="pa-0 overlay-content" :class="{ 'split-container': viewMode !== 'form' }">
          <div :class="viewMode !== 'form' ? 'split-layout' : ''" :data-view-mode="viewMode">
            <!-- Left: Form panels -->
            <div v-show="viewMode === 'form' || viewMode === 'both'" :class="viewMode === 'both' ? 'form-panel' : 'pt-6 px-4 form-content'">
              <v-window v-model="activeTab">
                <!-- We'll reuse the form content from EntityFormDialog -->
                <v-window-item value="basic">
                  <div class="pa-4">
                    <p class="text-caption text-medium-emphasis mb-4">
                      Edit entity properties. Changes are saved automatically.
                    </p>
                    <!-- Entity form content will be loaded here -->
                    <slot name="form-content" :active-tab="activeTab" />
                  </div>
                </v-window-item>

                <v-window-item value="relationships">
                  <div class="pa-4">
                    <slot name="form-content" :active-tab="activeTab" />
                  </div>
                </v-window-item>

                <v-window-item value="filters">
                  <div class="pa-4">
                    <slot name="form-content" :active-tab="activeTab" />
                  </div>
                </v-window-item>

                <v-window-item value="unnest">
                  <div class="pa-4">
                    <slot name="form-content" :active-tab="activeTab" />
                  </div>
                </v-window-item>

                <v-window-item value="append">
                  <div class="pa-4">
                    <slot name="form-content" :active-tab="activeTab" />
                  </div>
                </v-window-item>

                <v-window-item value="extra_columns">
                  <div class="pa-4">
                    <slot name="form-content" :active-tab="activeTab" />
                  </div>
                </v-window-item>

                <v-window-item value="yaml">
                  <div class="pa-4">
                    <slot name="form-content" :active-tab="activeTab" />
                  </div>
                </v-window-item>
              </v-window>
            </div>

            <!-- Right: Preview panel -->
            <div v-show="viewMode === 'preview' || viewMode === 'both'" :class="viewMode === 'both' ? 'preview-panel' : 'preview-content'">
              <slot name="preview-content" />
            </div>
          </div>
        </v-card-text>

        <v-divider />

        <v-card-actions class="justify-space-between">
          <div>
            <v-chip v-if="hasUnsavedChanges" color="warning" size="small" prepend-icon="mdi-content-save-alert">
              Unsaved Changes
            </v-chip>
          </div>
          <div class="d-flex gap-2">
            <v-btn variant="text" @click="handleClose"> Cancel </v-btn>
            <v-btn color="primary" :loading="saving" :disabled="!hasUnsavedChanges" @click="handleSave">
              Save Changes
            </v-btn>
          </div>
        </v-card-actions>
      </v-card>
    </transition>
  </v-overlay>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

interface Props {
  modelValue: boolean
  entityName: string | null
  projectName: string
  hasUnsavedChanges?: boolean
  saving?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'save'): void
  (e: 'close'): void
}

const props = withDefaults(defineProps<Props>(), {
  hasUnsavedChanges: false,
  saving: false,
})

const emit = defineEmits<Emits>()

// Local state
const activeTab = ref('basic')
const viewMode = ref<'form' | 'both' | 'preview'>('both')

// Computed
const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

// Methods
function handleClose() {
  if (props.hasUnsavedChanges) {
    const confirmed = confirm('You have unsaved changes. Are you sure you want to close?')
    if (!confirmed) return
  }
  emit('close')
  emit('update:modelValue', false)
}

function handleSave() {
  emit('save')
}

// Keyboard shortcuts
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isOpen.value) {
    handleClose()
  }
  // Ctrl+S or Cmd+S to save
  if ((event.ctrlKey || event.metaKey) && event.key === 's' && isOpen.value) {
    event.preventDefault()
    if (props.hasUnsavedChanges) {
      handleSave()
    }
  }
}

// Lifecycle
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// Watch for entity changes
watch(
  () => props.entityName,
  (newName) => {
    if (newName) {
      activeTab.value = 'basic' // Reset to basic tab when switching entities
    }
  }
)
</script>

<style scoped>
.entity-editor-overlay {
  z-index: 2000;
}

.overlay-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 85vw;
  max-width: 1400px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.overlay-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Split view layout */
.split-container {
  height: 100%;
  overflow: hidden;
}

.split-layout {
  display: grid;
  height: 100%;
  overflow: hidden;
}

.split-layout[data-view-mode='both'] {
  grid-template-columns: 1fr 1fr;
}

.split-layout[data-view-mode='form'] {
  grid-template-columns: 1fr;
}

.split-layout[data-view-mode='preview'] {
  grid-template-columns: 1fr;
}

.form-panel {
  overflow-y: auto;
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  padding: 16px;
}

.preview-panel {
  overflow-y: auto;
  padding: 16px;
}

.form-content {
  overflow-y: auto;
  height: 100%;
}

.preview-content {
  overflow-y: auto;
  height: 100%;
  padding: 16px;
}

/* Slide animation */
.slide-from-right-enter-active,
.slide-from-right-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-from-right-enter-from {
  transform: translateX(100%);
}

.slide-from-right-leave-to {
  transform: translateX(100%);
}

.slide-from-right-enter-to,
.slide-from-right-leave-from {
  transform: translateX(0);
}
</style>
