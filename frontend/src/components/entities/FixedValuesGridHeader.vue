<template>
  <div class="column-type-header">
    <button
      type="button"
      class="column-type-header__name"
      :class="{ 'column-type-header__name--sortable': canSort }"
      :title="sourceLabel"
      :disabled="!canSort"
      @click="onNameClick"
    >
      {{ columnName }}
    </button>

    <select
      class="column-type-header__select"
      :value="selectorValue"
      :title="sourceLabel"
      @click.stop
      @mousedown.stop
      @change="onSelectChange"
    >
      <option
        v-for="option in options"
        :key="`${columnName}-${option.value}`"
        :value="option.value"
      >
        {{ option.label }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { IHeaderParams } from 'ag-grid-community'

import type { FixedGridColumnTypeName } from './fixedValuesGridClipboard'

interface ColumnTypeOption {
  value: 'auto' | FixedGridColumnTypeName
  label: string
}

interface ColumnTypeHeaderParams extends Partial<IHeaderParams> {
  columnName: string
  getSelectorValue: (columnName: string) => 'auto' | FixedGridColumnTypeName
  getSourceLabel: (columnName: string) => string
  getOptions: (columnName: string) => ColumnTypeOption[]
  onTypeChange: (columnName: string, nextValue: 'auto' | FixedGridColumnTypeName) => void
}

const props = defineProps<{
  params: ColumnTypeHeaderParams
}>()

const columnName = computed(() => props.params.columnName)
const selectorValue = computed(() => props.params.getSelectorValue(columnName.value))
const sourceLabel = computed(() => props.params.getSourceLabel(columnName.value))
const options = computed(() => props.params.getOptions(columnName.value))
const canSort = computed(() => props.params.enableSorting !== false)

function onNameClick(): void {
  if (!canSort.value) {
    return
  }

  props.params.progressSort?.(false)
}

function onSelectChange(event: Event): void {
  const target = event.target as HTMLSelectElement | null
  const nextValue = (target?.value ?? 'auto') as 'auto' | FixedGridColumnTypeName
  props.params.onTypeChange(columnName.value, nextValue)
}
</script>

<style scoped>
.column-type-header {
  display: grid;
  gap: 2px;
  width: 100%;
  min-width: 0;
  padding: 2px 0;
}

.column-type-header__name {
  min-width: 0;
  overflow: hidden;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 9px;
  font-weight: 600;
  line-height: 1.1;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.column-type-header__name--sortable {
  cursor: pointer;
}

.column-type-header__name:disabled {
  cursor: default;
  opacity: 1;
}

.column-type-header__select {
  width: 100%;
  min-width: 0;
  min-height: 20px;
  padding: 1px 2px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.18);
  border-radius: 4px;
  background: rgb(var(--v-theme-background));
  color: rgb(var(--v-theme-on-background));
  font-size: 9px;
}
</style>