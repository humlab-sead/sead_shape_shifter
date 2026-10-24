<template>
  <div class="pa-4">
    <v-switch v-model="unnestEnabled" label="Enable Unnest" density="compact" hide-details class="mb-4" />

    <template v-if="unnestEnabled">
      <column-reference-combobox
        v-model="unnest.id_vars"
        :items="idVarColumns"
        :project-name="projectName"
        :entity-name="entityName"
        :entity-draft="entityDraft"
        :disabled="referenceControlsDisabled"
        :edited-field-path="`entities.${entityName}.unnest.id_vars`"
        label="ID Variables"
        hint="Columns to keep as-is"
        persistent-hint
        variant="outlined"
        density="compact"
        class="mb-4"
      />

      <column-reference-combobox
        v-model="unnest.value_vars"
        :items="valueVarColumns"
        :project-name="projectName"
        :entity-name="entityName"
        :entity-draft="entityDraft"
        :disabled="referenceControlsDisabled"
        :edited-field-path="`entities.${entityName}.unnest.value_vars`"
        label="Value Variables"
        hint="Columns to unpivot"
        persistent-hint
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

    <v-alert type="info" variant="tonal" density="compact" class="mt-3 text-caption">
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
import { normalizeColumnListChips } from './columnListValue'
import ColumnReferenceCombobox from './ColumnReferenceCombobox.vue'

interface UnnestConfig {
  id_vars: string[]
  value_vars: string[]
  var_name: string
  value_name: string
}

interface Props {
  modelValue?: UnnestConfig | null
  idVarColumns?: string[]
  valueVarColumns?: string[]
  projectName?: string
  entityName?: string
  entityDraft?: Record<string, unknown>
  referenceControlsDisabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  projectName: '',
  entityName: '',
  entityDraft: () => ({}),
  referenceControlsDisabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: UnnestConfig | null]
}>()

function cloneUnnest(value?: UnnestConfig | null): UnnestConfig {
  if (!value) {
    return {
      id_vars: [],
      value_vars: [],
      var_name: '',
      value_name: '',
    }
  }

  return {
    ...value,
    id_vars: normalizeColumnListChips(value.id_vars),
    value_vars: normalizeColumnListChips(value.value_vars),
  }
}

const unnest = ref<UnnestConfig>(cloneUnnest(props.modelValue))

const unnestEnabled = ref(!!props.modelValue)

const idVarColumns = computed(() => props.idVarColumns ?? [])
const valueVarColumns = computed(() => props.valueVarColumns ?? [])
const projectName = computed(() => props.projectName)
const entityName = computed(() => props.entityName)
const entityDraft = computed(() => props.entityDraft)
const referenceControlsDisabled = computed(() => props.referenceControlsDisabled)

watch(
  [unnestEnabled, unnest],
  () => {
    emit(
      'update:modelValue',
      unnestEnabled.value
        ? {
            ...unnest.value,
            id_vars: [...unnest.value.id_vars],
            value_vars: [...unnest.value.value_vars],
          }
        : null
    )
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  (newValue) => {
    if (!newValue) {
      unnestEnabled.value = false
      return
    }

    const normalized = cloneUnnest(newValue)
    if (unnestEnabled.value && JSON.stringify(unnest.value) === JSON.stringify(normalized)) {
      return
    }

    unnest.value = normalized
    unnestEnabled.value = true
  },
  { deep: true }
)
</script>
