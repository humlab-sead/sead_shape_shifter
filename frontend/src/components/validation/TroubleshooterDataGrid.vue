<template>
  <ag-grid-vue
    class="ag-theme-material troubleshooter-data-grid"
    :style="{ height }"
    :columnDefs="columnDefs"
    :rowData="rows"
    :defaultColDef="defaultColDef"
    :suppressCellFocus="true"
    :loading="loading"
    :rowSelection="rowSelection"
    @row-clicked="onRowClicked"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type { ColDef, RowClickedEvent } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-material.css'

/** One read-only column in a troubleshooter grid. */
export interface TroubleshooterGridColumn {
  /** Row record key the column reads. */
  field: string
  /** Column header text. */
  header: string
  /** Alignment for numeric values. */
  align?: 'left' | 'right'
  /** Optional fixed column width in pixels; otherwise the column flexes. */
  width?: number
}

interface Props {
  columns: TroubleshooterGridColumn[]
  rows: Record<string, unknown>[]
  /** Grid height; the grid does not grow the dialog. */
  height?: string
  loading?: boolean
  /** Whether the grid lets the user select one row at a time. */
  selectable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  height: '320px',
  loading: false,
  selectable: false,
})

const emit = defineEmits<{
  (event: 'row-click', row: Record<string, unknown>): void
}>()

const columnDefs = computed<ColDef[]>(() =>
  props.columns.map((column) => ({
    field: column.field,
    headerName: column.header,
    width: column.width,
    minWidth: 90,
    sortable: false,
    filter: false,
    editable: false,
    resizable: true,
    cellStyle: column.align === 'right' ? { textAlign: 'right' } : undefined,
  }))
)

// These grids are read-only inspection views over a bounded server page, so
// sorting and filtering stay off: they would only reorder the rows returned.
const defaultColDef: ColDef = {
  flex: 1,
  sortable: false,
  filter: false,
  editable: false,
  suppressHeaderMenuButton: true,
}

const rowSelection = computed(() => (props.selectable ? 'single' : undefined))

function onRowClicked(event: RowClickedEvent): void {
  if (!props.selectable || event.data === undefined) {
    return
  }
  emit('row-click', event.data as Record<string, unknown>)
}
</script>

<style scoped>
.troubleshooter-data-grid {
  width: 100%;
  --ag-row-height: 26px;
  --ag-header-height: 32px;
  --ag-font-size: 12px;
}

.troubleshooter-data-grid :deep(.ag-cell) {
  font-size: 0.75rem;
  line-height: 26px;
}
</style>
