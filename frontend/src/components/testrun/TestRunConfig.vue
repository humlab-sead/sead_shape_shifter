<template>
  <div class="test-run-config">
    <h3 class="text-h6 mb-4">Test Run Project</h3>

    <v-form>
      <!-- Entity Selection -->
      <div class="mb-6">
        <v-label class="mb-2">Entities to Test</v-label>
        <div class="d-flex ga-2 mb-2">
          <v-select
            v-model="selectedEntity"
            :items="availableEntitiesForSelect"
            placeholder="Select entity to add..."
            variant="outlined"
            density="comfortable"
            hide-details
            clearable
            @update:model-value="handleEntitySelect"
          />
          <v-btn variant="outlined" @click="handleSelectAll">All</v-btn>
          <v-btn variant="outlined" @click="handleClear">Clear</v-btn>
        </div>
        <v-chip
          v-for="entity in modelSelectedEntities"
          :key="entity"
          class="ma-1"
          closable
          @click:close="handleRemoveEntity(entity)"
        >
          {{ entity }}
        </v-chip>
        <div class="text-caption text-medium-emphasis mt-2">
          {{
            modelSelectedEntities.length > 0
              ? `${modelSelectedEntities.length} entities selected`
              : 'All entities will be tested'
          }}
        </div>
      </div>

      <!-- Max Rows -->
      <v-text-field
        v-model.number="localOptions.max_rows_per_entity"
        label="Max Rows Per Entity"
        type="number"
        :min="10"
        :max="10000"
        :step="10"
        hint="Limit rows per entity to prevent timeouts (10-10000)"
        persistent-hint
        variant="outlined"
        class="mb-4"
      />

      <!-- Output Format -->
      <v-select
        v-model="localOptions.output_format"
        :items="outputFormatItems"
        label="Output Format"
        hint="Format for entity output data"
        persistent-hint
        variant="outlined"
        class="mb-4"
      />

      <!-- Validation Options -->
      <div class="mb-2">
        <h4 class="text-subtitle-1 mb-3">Validation Options</h4>

        <v-switch
          v-model="localOptions.validate_foreign_keys"
          label="Validate Foreign Keys"
          color="primary"
          hide-details
        />
        <div class="text-caption text-medium-emphasis ml-12 mb-3">Check foreign key relationships and constraints</div>

        <v-switch
          v-model="localOptions.validate_constraints"
          label="Validate Constraints"
          color="primary"
          hide-details
        />
        <div class="text-caption text-medium-emphasis ml-12 mb-3">Check all constraint validations</div>

        <v-switch v-model="localOptions.stop_on_error" label="Stop on Error" color="primary" hide-details />
        <div class="text-caption text-medium-emphasis ml-12">Stop test run when first error encountered</div>
      </div>
    </v-form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { TestRunOptions } from '@/types/testRun'
import { OutputFormat, DEFAULT_TEST_RUN_OPTIONS } from '@/types/testRun'

interface Props {
  options: Partial<TestRunOptions>
  selectedEntities: string[]
  entities: string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:options': [options: Partial<TestRunOptions>]
  'update:selectedEntities': [entities: string[]]
}>()

const selectedEntity = ref<string | null>(null)
const localOptions = ref<TestRunOptions>({
  ...DEFAULT_TEST_RUN_OPTIONS,
  ...props.options,
})

const modelSelectedEntities = computed({
  get: () => props.selectedEntities,
  set: (value) => emit('update:selectedEntities', value),
})

const availableEntitiesForSelect = computed(() =>
  props.entities.filter((e) => !modelSelectedEntities.value.includes(e))
)

const outputFormatItems = [
  { title: 'Preview (first N rows)', value: OutputFormat.PREVIEW },
  { title: 'CSV', value: OutputFormat.CSV },
  { title: 'JSON', value: OutputFormat.JSON },
]

// Watch localOptions and emit changes
watch(
  localOptions,
  (newOptions) => {
    emit('update:options', newOptions)
  },
  { deep: true }
)

const handleEntitySelect = (entity: string | null) => {
  if (entity && !modelSelectedEntities.value.includes(entity)) {
    modelSelectedEntities.value = [...modelSelectedEntities.value, entity]
  }
  selectedEntity.value = null
}

const handleRemoveEntity = (entity: string) => {
  modelSelectedEntities.value = modelSelectedEntities.value.filter((e) => e !== entity)
}

const handleSelectAll = () => {
  modelSelectedEntities.value = [...props.entities]
}

const handleClear = () => {
  modelSelectedEntities.value = []
}
</script>

<style scoped>
.test-run-config {
  width: 100%;
}
</style>
