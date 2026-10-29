<template>
  <v-menu v-model="previewOpen" location="bottom" :close-on-content-click="false">
    <template #activator="{ props: activatorProps }">
      <v-chip v-bind="chipProps">
        <span>{{ value }}</span>
        <v-btn
          v-bind="activatorProps"
          type="button"
          icon="mdi-eye-outline"
          variant="text"
          size="x-small"
          density="compact"
          aria-label="Preview value reference"
          title="Preview value reference"
          class="ml-1"
          @click.stop="openPreview"
          @keydown.enter.prevent.stop="openPreview"
          @keydown.space.prevent.stop="openPreview"
        />
      </v-chip>
    </template>

    <v-card role="dialog" aria-label="Value reference preview" class="pa-3" min-width="240" max-width="420">
      <div class="text-caption font-weight-medium mb-2">Based on cached configuration</div>
      <div v-if="previewColumns === null" role="status" data-testid="value-reference-preview-unavailable">
        Preview unavailable
      </div>
      <div v-else-if="previewColumns.length === 0" role="status" data-testid="value-reference-preview-empty">
        This reference contains no columns.
      </div>
      <div v-else class="value-reference-preview__columns">
        <div
          v-for="(column, index) in previewColumns"
          :key="`${index}-${column}`"
          data-testid="value-reference-preview-column"
        >
          {{ column }}
        </div>
      </div>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { EntityResponse } from '@/api/entities'
import { expandValueReference } from '@/utils/valueReferenceColumns'

interface Props {
  value: string
  chipProps: Record<string, unknown>
  entities: EntityResponse[] | null
}

const props = defineProps<Props>()
const previewOpen = ref(false)
const previewColumns = computed(() => expandValueReference(props.value, props.entities))

function openPreview() {
  previewOpen.value = true
}

watch(
  () => props.entities,
  () => (previewOpen.value = false),
  { deep: true }
)
</script>
