<template>
  <div class="pa-4">
    <v-list>
      <v-list-item v-for="(item, index) in append" :key="index" class="px-0 mb-2">
        <v-card variant="outlined">
          <v-card-text>
            <div class="d-flex align-center justify-space-between mb-2">
              <v-select
                v-model="item.type"
                :items="appendTypes"
                label="Append Type"
                variant="outlined"
                density="compact"
                style="max-width: 200px"
              />
              <v-btn icon="mdi-delete" variant="text" size="small" color="error" @click="handleRemoveAppend(index)" />
            </div>

            <v-textarea
              v-if="item.type === 'fixed'"
              v-model="item.valuesText"
              label="Values (JSON Array)"
              hint='Example: [["value1", "value2"], ["value3", "value4"]]'
              persistent-hint
              variant="outlined"
              rows="3"
            />

            <template v-else-if="item.type === 'sql'">
              <v-text-field
                v-model="item.data_source"
                label="Data Source"
                variant="outlined"
                density="compact"
                class="mb-2"
              />
              <v-textarea v-model="item.query" label="SQL Query" variant="outlined" rows="4" />
            </template>
          </v-card-text>
        </v-card>
      </v-list-item>
    </v-list>

    <v-btn variant="outlined" prepend-icon="mdi-plus" size="small" block @click="handleAddAppend">
      Add Append
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface AppendConfig {
  type: 'fixed' | 'sql'
  values?: any[][]
  valuesText?: string
  data_source?: string
  query?: string
}

interface Props {
  modelValue?: AppendConfig[]
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: AppendConfig[] | undefined]
}>()

const append = ref<AppendConfig[]>(props.modelValue || [])

const appendTypes = [
  { title: 'Fixed Values', value: 'fixed' },
  { title: 'SQL Query', value: 'sql' },
]

function handleAddAppend() {
  append.value.push({
    type: 'fixed',
    valuesText: '',
  })
}

function handleRemoveAppend(index: number) {
  append.value.splice(index, 1)
}

watch(
  append,
  (newValue) => {
    emit('update:modelValue', newValue.length > 0 ? newValue : undefined)
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      append.value = newValue
    }
  },
  { deep: true }
)
</script>
