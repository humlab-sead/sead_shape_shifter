<template>
  <div class="pa-4">
    <v-switch v-model="unnestEnabled" label="Enable Unnest" density="compact" hide-details class="mb-4" />

    <template v-if="unnestEnabled">
      <v-combobox
        v-model="unnest.id_vars"
        label="ID Variables"
        hint="Columns to keep as-is"
        persistent-hint
        chips
        multiple
        variant="outlined"
        density="compact"
        class="mb-4"
      />

      <v-combobox
        v-model="unnest.value_vars"
        label="Value Variables"
        hint="Columns to unpivot"
        persistent-hint
        chips
        multiple
        variant="outlined"
        density="compact"
        class="mb-4"
      />

      <v-text-field
        v-model="unnest.var_name"
        label="Variable Name Column"
        hint="Name for the new column containing variable names"
        persistent-hint
        variant="outlined"
        density="compact"
        class="mb-4"
      />

      <v-text-field
        v-model="unnest.value_name"
        label="Value Name Column"
        hint="Name for the new column containing values"
        persistent-hint
        variant="outlined"
        density="compact"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface UnnestConfig {
  id_vars: string[]
  value_vars: string[]
  var_name: string
  value_name: string
}

interface Props {
  modelValue?: UnnestConfig | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: UnnestConfig | null]
}>()

const unnest = ref<UnnestConfig>(
  props.modelValue || {
    id_vars: [],
    value_vars: [],
    var_name: '',
    value_name: '',
  }
)

const unnestEnabled = ref(!!props.modelValue)

watch(
  [unnestEnabled, unnest],
  () => {
    emit('update:modelValue', unnestEnabled.value ? unnest.value : null)
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      unnest.value = newValue
      unnestEnabled.value = true
    } else {
      unnestEnabled.value = false
    }
  },
  { deep: true }
)
</script>
