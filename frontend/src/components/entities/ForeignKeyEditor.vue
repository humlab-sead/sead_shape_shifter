<template>
  <v-card>
    <v-card-title class="d-flex align-center justify-space-between">
      <span>Foreign Keys</span>
      <v-btn
        variant="text"
        size="small"
        prepend-icon="mdi-plus"
        @click="handleAddForeignKey"
      >
        Add
      </v-btn>
    </v-card-title>

    <v-divider />

    <v-card-text>
      <v-list v-if="foreignKeys.length > 0">
        <v-list-item
          v-for="(fk, index) in foreignKeys"
          :key="index"
          class="px-0"
        >
          <v-card variant="outlined" class="mb-2">
            <v-card-text>
              <div class="d-flex align-center justify-space-between mb-2">
                <v-chip size="small" prepend-icon="mdi-link-variant">
                  {{ fk.entity }}
                </v-chip>
                <v-btn
                  icon="mdi-delete"
                  variant="text"
                  size="small"
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
                  <v-icon icon="mdi-arrow-right" />
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

              <v-row dense class="mt-2">
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
                    <v-expansion-panel title="Constraints">
                      <v-expansion-panel-text>
                        <v-select
                          v-model="fk.constraints!.cardinality"
                          :items="cardinalityTypes"
                          label="Cardinality"
                          variant="outlined"
                          density="compact"
                          class="mb-2"
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

interface Props {
  modelValue: ForeignKeyConfig[]
  availableEntities?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  availableEntities: () => [],
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
