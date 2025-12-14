<template>
  <v-card variant="outlined" class="mb-2">
    <v-card-text class="d-flex align-center pa-3">
      <!-- Column Selector -->
      <v-select
        v-model="condition.column"
        :items="availableColumns"
        label="Column"
        density="compact"
        style="max-width: 200px"
        class="mr-2"
        hide-details
      >
        <template #prepend-inner>
          <v-icon size="small">mdi-table-column</v-icon>
        </template>
      </v-select>

      <!-- Operator Selector -->
      <v-select
        v-model="condition.operator"
        :items="operators"
        item-title="label"
        item-value="value"
        label="Operator"
        density="compact"
        style="max-width: 150px"
        class="mr-2"
        hide-details
      />

      <!-- Value Input (only for operators that need a value) -->
      <v-text-field
        v-if="!isNullOperator(condition.operator)"
        v-model="condition.value"
        label="Value"
        density="compact"
        style="flex: 1"
        class="mr-2"
        hide-details
        placeholder="Enter value..."
      >
        <template #prepend-inner>
          <v-icon size="small">mdi-form-textbox</v-icon>
        </template>
      </v-text-field>

      <!-- Delete Button -->
      <v-btn
        icon="mdi-delete"
        variant="text"
        color="error"
        size="small"
        @click="$emit('delete')"
      />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue';

export interface QueryConditionData {
  column: string;
  operator: string;
  value: string;
}

interface Props {
  modelValue: QueryConditionData;
  availableColumns: string[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  'update:modelValue': [value: QueryConditionData];
  'delete': [];
}>();

// Local reactive copy for two-way binding
const condition = reactive<QueryConditionData>({
  column: props.modelValue.column,
  operator: props.modelValue.operator,
  value: props.modelValue.value,
});

// Watch for changes and emit updates
watch(condition, (newVal) => {
  emit('update:modelValue', { ...newVal });
}, { deep: true });

// Watch for prop changes (external updates)
watch(() => props.modelValue, (newVal) => {
  Object.assign(condition, newVal);
}, { deep: true });

// Operator options
const operators = [
  { label: '= (equals)', value: '=' },
  { label: '!= (not equals)', value: '!=' },
  { label: '< (less than)', value: '<' },
  { label: '<= (less or equal)', value: '<=' },
  { label: '> (greater than)', value: '>' },
  { label: '>= (greater or equal)', value: '>=' },
  { label: 'LIKE (pattern match)', value: 'LIKE' },
  { label: 'NOT LIKE', value: 'NOT LIKE' },
  { label: 'IN (in list)', value: 'IN' },
  { label: 'NOT IN', value: 'NOT IN' },
  { label: 'IS NULL', value: 'IS NULL' },
  { label: 'IS NOT NULL', value: 'IS NOT NULL' },
  { label: 'BETWEEN', value: 'BETWEEN' },
];

// Check if operator doesn't need a value
const isNullOperator = (operator: string): boolean => {
  return operator === 'IS NULL' || operator === 'IS NOT NULL';
};
</script>

<style scoped>
.v-card {
  transition: all 0.2s ease;
}

.v-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
