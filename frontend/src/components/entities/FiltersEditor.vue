<template>
  <div class="pa-4">
    <v-list>
      <v-list-item v-for="(filter, index) in filters" :key="index" class="px-0 mb-2">
        <v-card variant="outlined">
          <v-card-text>
            <div class="d-flex align-center justify-space-between mb-2">
              <v-select
                v-model="filter.type"
                :items="filterTypes"
                label="Filter Type"
                variant="outlined"
                density="compact"
                style="max-width: 200px"
              />
              <v-btn icon="mdi-delete" variant="text" size="small" color="error" @click="handleRemoveFilter(index)" />
            </div>

            <v-row dense v-if="filter.type === 'exists_in'">
              <v-col cols="12" md="4">
                <v-autocomplete
                  v-model="filter.entity"
                  :items="availableEntities"
                  label="Entity"
                  variant="outlined"
                  density="compact"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field v-model="filter.column" label="Column" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="filter.remote_column"
                  label="Remote Column"
                  variant="outlined"
                  density="compact"
                />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-list-item>
    </v-list>

    <v-btn variant="outlined" prepend-icon="mdi-plus" size="small" block @click="handleAddFilter">
      Add Filter
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface FilterConfig {
  type: string
  entity?: string
  column?: string
  remote_column?: string
}

interface Props {
  modelValue?: FilterConfig[]
  availableEntities?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  availableEntities: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: FilterConfig[] | undefined]
}>()

const filters = ref<FilterConfig[]>(props.modelValue || [])

const filterTypes = [{ title: 'Exists In', value: 'exists_in' }]

function handleAddFilter() {
  filters.value.push({
    type: 'exists_in',
    entity: '',
    column: '',
    remote_column: '',
  })
}

function handleRemoveFilter(index: number) {
  filters.value.splice(index, 1)
}

watch(
  filters,
  (newValue) => {
    emit('update:modelValue', newValue.length > 0 ? newValue : undefined)
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      filters.value = newValue
    }
  },
  { deep: true }
)
</script>
