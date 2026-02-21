<template>
  <v-menu offset-y>
    <template #activator="{ props: menuProps }">
      <v-btn
        v-bind="menuProps"
        size="small"
        variant="tonal"
        prepend-icon="mdi-eye-outline"
        append-icon="mdi-menu-down"
        :color="hasActiveOptions ? 'primary' : undefined"
        class="text-capitalize"
      >
        Display
        <v-badge
          v-if="activeOptionsCount > 0"
          :content="activeOptionsCount"
          color="primary"
          inline
          class="ml-1"
        />
      </v-btn>
    </template>

    <v-list density="compact" min-width="200">
      <v-list-subheader>Graph Display Options</v-list-subheader>
      
      <!-- Node Labels -->
      <v-list-item @click="toggleOption('nodeLabels')">
        <template #prepend>
          <v-checkbox-btn
            :model-value="options.nodeLabels"
            hide-details
            density="compact"
          />
        </template>
        <v-list-item-title>Node Labels</v-list-item-title>
      </v-list-item>

      <!-- Edge Labels -->
      <v-list-item @click="toggleOption('edgeLabels')">
        <template #prepend>
          <v-checkbox-btn
            :model-value="options.edgeLabels"
            hide-details
            density="compact"
          />
        </template>
        <v-list-item-title>Edge Labels</v-list-item-title>
      </v-list-item>

      <v-divider class="my-2" />

      <!-- Show Sources (databases, files) -->
      <v-list-item @click="toggleOption('showSources')">
        <template #prepend>
          <v-checkbox-btn
            :model-value="options.showSources"
            hide-details
            density="compact"
          />
        </template>
        <v-list-item-title>Show Sources</v-list-item-title>
        <v-list-item-subtitle class="text-caption">Databases, Files</v-list-item-subtitle>
      </v-list-item>

      <!-- Show Source Entities (tables, sheets) -->
      <v-list-item @click="toggleOption('showSourceEntities')">
        <template #prepend>
          <v-checkbox-btn
            :model-value="options.showSourceEntities"
            hide-details
            density="compact"
          />
        </template>
        <v-list-item-title>Show Source Entities</v-list-item-title>
        <v-list-item-subtitle class="text-caption">Tables, Sheets</v-list-item-subtitle>
      </v-list-item>

      <v-divider class="my-2" />

      <!-- Reset to defaults -->
      <v-list-item @click="resetToDefaults">
        <template #prepend>
          <v-icon icon="mdi-restore" size="small" />
        </template>
        <v-list-item-title class="text-caption">Reset to Defaults</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface GraphDisplayOptions {
  nodeLabels: boolean
  edgeLabels: boolean
  showSources: boolean  // Show top-level sources (databases, files)
  showSourceEntities: boolean  // Show intermediate source entities (tables, sheets)
}

interface Props {
  options: GraphDisplayOptions
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:options', value: GraphDisplayOptions): void
}>()

const hasActiveOptions = computed(() => {
  return props.options.nodeLabels || props.options.edgeLabels || props.options.showSources || props.options.showSourceEntities
})

const activeOptionsCount = computed(() => {
  let count = 0
  if (props.options.nodeLabels) count++
  if (props.options.edgeLabels) count++
  if (props.options.showSources) count++
  if (props.options.showSourceEntities) count++
  return count
})

function toggleOption(option: keyof GraphDisplayOptions) {
  const newOptions = { ...props.options }
  newOptions[option] = !newOptions[option]
  emit('update:options', newOptions)
}

function resetToDefaults() {
  emit('update:options', {
    nodeLabels: true,
    edgeLabels: true,
    showSources: false,
    showSourceEntities: false,
  })
}
</script>
