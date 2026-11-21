<template>
  <ag-grid-vue
    class="ag-theme-material selection-browse-grid"
    :columnDefs="columnDefs"
    :rowData="items"
    :defaultColDef="defaultColDef"
    :rowHeight="ROW_HEIGHT"
    :headerHeight="36"
    :rowClassRules="rowClassRules"
    :getRowId="getRowId"
    :suppressRowClickSelection="true"
    :animateRows="false"
    :domLayout="'normal'"
    @grid-ready="onGridReady"
    @row-clicked="onRowClicked"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type { ColDef, GridApi, GridReadyEvent, RowClassParams, RowClickedEvent } from 'ag-grid-community'
import type { SelectionDisplayField, SelectionRecord } from '@/types/reconciliation'
import { selectionFieldValue } from '@/utils/selectionRecord'

import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-material.css'

interface Props {
  /** Records to show. The caller filters and orders them before passing them in. */
  items: SelectionRecord[]
  /** Display fields to render, in their declared order. */
  columns: SelectionDisplayField[]
  /** Record ID of the current selection, or null when nothing is selected. */
  selectedId: string | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  select: [record: SelectionRecord]
}>()

const ROW_HEIGHT = 32
const SELECTED_ROW_CLASS = 'selection-row-selected'

const gridApi = ref<GridApi<SelectionRecord> | null>(null)

/** Numeric IDs stay narrow so the text columns get the remaining width. */
function sizingFor(field: string): ColDef<SelectionRecord> {
  if (field === 'target_id') return { width: 110, type: 'numericColumn' }
  if (field === 'name') return { flex: 1, minWidth: 180 }
  if (field === 'description') return { flex: 2, minWidth: 240 }
  return { flex: 1, minWidth: 140 }
}

const columnDefs = computed<ColDef<SelectionRecord>[]>(() =>
  props.columns.map((column) => ({
    headerName: column.label,
    colId: column.name,
    valueGetter: (params) => (params.data ? selectionFieldValue(params.data, column.name) : null),
    ...sizingFor(column.name),
    // Descriptions are the column most likely to be clipped, so name them in a tooltip.
    ...(column.name === 'description'
      ? { tooltipValueGetter: (params: { value?: unknown }) => (params.value == null ? '' : String(params.value)) }
      : {}),
  }))
)

const defaultColDef: ColDef<SelectionRecord> = {
  resizable: true,
  sortable: true,
  filter: false,
  editable: false,
  suppressMovable: true,
}

/** Highlight the selected row without relying on ag-Grid row selection state. */
const rowClassRules = {
  [SELECTED_ROW_CLASS]: (params: RowClassParams<SelectionRecord>) =>
    Boolean(params.data && params.data.id === props.selectedId),
}

function getRowId(params: { data: SelectionRecord }): string {
  return params.data.id
}

function onGridReady(event: GridReadyEvent<SelectionRecord>) {
  gridApi.value = event.api
}

function onRowClicked(event: RowClickedEvent<SelectionRecord>) {
  if (event.data) emit('select', event.data)
}

// Class rules are re-evaluated only for re-rendered rows, so repaint on change.
watch(
  () => props.selectedId,
  () => gridApi.value?.redrawRows()
)
</script>

<style scoped>
/*
 * A fixed height keeps row virtualization on. Without it ag-Grid renders every
 * row, and the page scrolls once more as the record count grows.
 */
.selection-browse-grid {
  width: 100%;
  height: min(56vh, 460px);
  min-height: 260px;
}

:deep(.selection-browse-grid .ag-row.selection-row-selected) {
  background-color: #e3f2fd;
}
</style>
