<template>
  <div class="pa-4">
    <v-switch v-model="unnestEnabled" label="Enable Unnest" density="compact" hide-details class="mb-4" />

    <template v-if="unnestEnabled">
      <v-combobox
        v-model="unnest.id_vars"
        :items="availableColumns"
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
        :items="availableColumns"
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

    <v-alert
      type="info"
      variant="tonal"
      density="compact"
      class="mt-3 text-caption"
    >
      <strong>Unnesting</strong> allows you to reshape data from wide format to long format.
      <ul class="mt-2 mb-0 pl-4">
        <li><strong>ID variables:</strong> columns to keep fixed (identifiers)</li>
        <li><strong>Value variables:</strong> columns to unpivot (optional; defaults to all others)</li>
        <li><strong>Variable name:</strong> name of the new column holding former column names</li>
        <li><strong>Value name:</strong> name of the new column holding values</li>
      </ul>

    </v-alert>


  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface UnnestConfig {
  id_vars: string[]
  value_vars: string[]
  var_name: string
  value_name: string
}

interface Props {
  modelValue?: UnnestConfig | null
  availableColumns?: string[]
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

const availableColumns = computed(() => props.availableColumns || [])

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
