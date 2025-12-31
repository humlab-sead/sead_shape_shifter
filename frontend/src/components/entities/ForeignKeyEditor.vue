<template>
  <v-card class="fk-editor-compact">
    <v-card-title class="d-flex align-center justify-space-between py-2">
      <span class="text-body-2">Foreign Keys</span>
      <v-btn variant="text" size="x-small" prepend-icon="mdi-plus" @click="handleAddForeignKey"> Add </v-btn>
    </v-card-title>

    <v-divider />

    <v-card-text class="pa-2">
      <v-list v-if="foreignKeys.length > 0">
        <v-list-item v-for="(fk, index) in foreignKeys" :key="index" class="px-0">
          <v-card variant="outlined" class="mb-2">
            <v-card-text class="pa-2">
              <div class="d-flex align-center justify-space-between mb-1">
                <v-autocomplete
                  v-model="fk.entity"
                  :items="availableEntities"
                  label="Target Entity"
                  variant="outlined"
                  density="compact"
                  hide-details
                  prepend-inner-icon="mdi-link-variant"
                  class="flex-grow-1 mr-2"
                />
                <v-btn
                  icon="mdi-delete"
                  variant="text"
                  size="x-small"
                  color="error"
                  @click="handleRemoveForeignKey(index)"
                />
              </div>

              <v-row dense>
                <v-col cols="12" md="5">
                  <v-combobox
                    v-model="fk.local_keys"
                    label="Local Keys"
                    chips
                    multiple
                    variant="outlined"
                    density="compact"
                    hide-details
                  />
                </v-col>

                <v-col cols="12" md="2" class="d-flex align-center justify-center">
                  <v-icon icon="mdi-arrow-right" size="small" />
                </v-col>

                <v-col cols="12" md="5">
                  <v-combobox
                    v-model="fk.remote_keys"
                    label="Remote Keys"
                    chips
                    multiple
                    variant="outlined"
                    density="compact"
                    hide-details
                  />
                </v-col>
              </v-row>

              <v-row dense class="mt-1">
                <v-col cols="12" md="4">
                  <v-select
                    v-model="fk.how"
                    :items="joinTypes"
                    label="Join Type"
                    variant="outlined"
                    density="compact"
                    hide-details
                  />
                </v-col>

                <v-col cols="12" md="8">
                  <v-expansion-panels variant="accordion" density="compact">
                    <v-expansion-panel>
                      <v-expansion-panel-title class="py-1 text-caption"> Constraints </v-expansion-panel-title>
                      <v-expansion-panel-text class="pt-1">
                        <v-select
                          v-model="fk.constraints!.cardinality"
                          :items="cardinalityTypes"
                          label="Cardinality"
                          variant="outlined"
                          density="compact"
                          class="mb-1"
                        />

                        <v-checkbox
                          v-model="fk.constraints!.require_unique_left"
                          label="Require Unique Left"
                          density="compact"
                          hide-details
                        />

                        <v-checkbox
                          v-model="fk.constraints!.allow_null_keys"
                          label="Allow Null Keys"
                          density="compact"
                          hide-details
                        />
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
                </v-col>
              </v-row>

              <!-- Test Join Button -->
              <v-row dense class="mt-1">
                <v-col cols="12">
                  <ForeignKeyTester
                    :config-name="projectName"
                    :entity-name="entityName"
                    :foreign-key="fk"
                    :foreign-key-index="index"
                    :disabled="!isEntitySaved"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-list-item>
      </v-list>

      <v-alert v-else type="info" variant="tonal" density="compact">
        No foreign keys defined. Click "Add" to create a relationship.
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ForeignKeyConfig } from '@/types'
import ForeignKeyTester from './ForeignKeyTester.vue'

interface Props {
  modelValue: ForeignKeyConfig[]
  availableEntities?: string[]
  projectName: string
  entityName: string
  isEntitySaved?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  availableEntities: () => [],
  isEntitySaved: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: ForeignKeyConfig[]]
}>()

const foreignKeys = ref<ForeignKeyConfig[]>([...props.modelValue])

const joinTypes = [
  { title: 'Inner Join', value: 'inner' },
  { title: 'Left Join', value: 'left' },
  { title: 'Right Join', value: 'right' },
  { title: 'Outer Join', value: 'outer' },
  { title: 'Cross Join', value: 'cross' },
]

const cardinalityTypes = [
  { title: 'One to One', value: 'one_to_one' },
  { title: 'One to Many', value: 'one_to_many' },
  { title: 'Many to One', value: 'many_to_one' },
]

function handleAddForeignKey() {
  foreignKeys.value.push({
    entity: '',
    local_keys: [],
    remote_keys: [],
    how: 'inner',
    constraints: {
      cardinality: 'many_to_one',
      require_unique_left: false,
      allow_null_keys: false,
    } as any,
  } as ForeignKeyConfig)
}

function handleRemoveForeignKey(index: number) {
  foreignKeys.value.splice(index, 1)
}

// Emit changes
watch(
  foreignKeys,
  (newValue) => {
    emit('update:modelValue', newValue)
  },
  { deep: true }
)

// Sync with prop changes
watch(
  () => props.modelValue,
  (newValue) => {
    foreignKeys.value = [...newValue]
  }
)
</script>
<style scoped>
.fk-editor-compact :deep(.v-field__input) {
  font-size: 11px;
  padding-top: 2px;
  padding-bottom: 2px;
}

.fk-editor-compact :deep(.v-field__prepend-inner) {
  padding-top: 2px;
}

.fk-editor-compact :deep(.v-label) {
  font-size: 11px;
}

.fk-editor-compact :deep(.v-chip) {
  font-size: 10px;
  height: 20px;
}

.fk-editor-compact :deep(.v-checkbox .v-label) {
  font-size: 11px;
}

.fk-editor-compact :deep(.v-field) {
  --v-field-padding-top: 2px;
  --v-field-padding-bottom: 2px;
}

.fk-editor-compact :deep(.v-field--variant-outlined .v-field__outline) {
  --v-field-border-opacity: 0.3;
}

.fk-editor-compact :deep(.v-expansion-panel-title) {
  min-height: 32px;
  font-size: 11px;
}

.fk-editor-compact :deep(.v-expansion-panel-text__wrapper) {
  padding: 4px 8px;
}

.fk-editor-compact :deep(.v-btn) {
  font-size: 11px;
}
</style>
