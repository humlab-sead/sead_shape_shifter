<template>
  <div class="fixed-values-grid" @paste="onPaste">
    <div class="d-flex justify-space-between align-center mb-2">
      <span class="text-caption">Fixed Values Data</span>
      <div>
        <v-btn size="small" variant="outlined" prepend-icon="mdi-plus" @click="addRow" class="mr-2"> Add Row </v-btn>
        <v-btn size="small" variant="outlined" prepend-icon="mdi-delete" color="error" @click="deleteSelectedRows"
          :disabled="!hasSelection">
          Delete Selected
        </v-btn>
      </div>
    </div>

    <v-alert v-if="validationErrors.length > 0" type="error" variant="tonal" density="compact" class="mb-2">
      <div v-for="error in validationErrors" :key="error" class="text-caption">{{ error }}</div>
    </v-alert>

    <ag-grid-vue class="ag-theme-alpine compact-grid" :style="{ height: gridHeight }" :columnDefs="columnDefs"
      :rowData="rowData" :getRowId="getRowId" :defaultColDef="defaultColDef" :rowSelection="'multiple'"
      :suppressRowClickSelection="true" :animateRows="true" :headerHeight="28" :rowHeight="26" :singleClickEdit="true"
      :stopEditingWhenCellsLoseFocus="true" @grid-ready="onGridReady" @cell-value-changed="onCellValueChanged"
      @selection-changed="onSelectionChanged" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type { CellValueChangedEvent, ColDef, GetRowIdParams, GridApi, GridReadyEvent } from 'ag-grid-community'
import {
  applyClipboardMatrix,
  buildGridRowData,
  coerceGridRows,
  coerceGridValue,
  inferColumnType,
  parseClipboardTable,
} from './fixedValuesGridClipboard'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'

interface Props {
  modelValue: any[][]
  columns: string[]
  publicId?: string
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '300px',
  publicId: undefined,
})

const emit = defineEmits<{
  'update:modelValue': [value: any[][]]
  'validation-errors': [value: string[]]
}>()

const gridApi = ref<GridApi>()
const hasSelection = ref(false)
const lastEmittedModelSignature = ref<string | null>(null)
const validationErrors = ref<string[]>([])

const gridHeight = computed(() => props.height)
const systemIdColumnIndex = computed(() => props.columns.findIndex((col) => col === 'system_id'))

const defaultColDef: ColDef = {
  editable: true,
  sortable: true,
  filter: true,
  resizable: true,
  minWidth: 100,
  flex: 1,
}

function setValidationErrors(errors: string[]) {
  validationErrors.value = errors
  emit('validation-errors', errors)
}

function clearValidationErrors() {
  if (validationErrors.value.length === 0) {
    return
  }

  validationErrors.value = []
  emit('validation-errors', [])
}

function formatValidationError(columnName: string, rowIndex: number, error: string): string {
  return `Row ${rowIndex + 1}, column ${columnName}: ${error}`
}

const columnDefs = computed<ColDef[]>(() => {
  if (!props.columns || props.columns.length === 0) {
    return []
  }

  return [
    {
      headerName: '',
      checkboxSelection: true,
      headerCheckboxSelection: true,
      width: 50,
      minWidth: 50,
      maxWidth: 50,
      flex: 0,
      editable: false,
      sortable: false,
      filter: false,
      resizable: false,
    },
    ...props.columns.map((col, index) => {
      const isSystemId = col === 'system_id'
      const isPublicId = col === props.publicId
      const isIntegerColumn = inferColumnType(col) === 'number'

      return {
        field: `col_${index}`,
        headerName: col,
        editable: !isSystemId,
        sortable: true,
        filter: true,
        resizable: true,
        minWidth: 100,
        flex: 1,
        valueParser: isSystemId ? undefined : (params: any) => {
          const result = coerceGridValue(col, params.newValue, params.oldValue)

          if (result.error) {
            setValidationErrors([
              formatValidationError(col, params.node?.rowIndex ?? 0, result.error),
            ])
            return params.oldValue
          }

          if (isIntegerColumn) {
            clearValidationErrors()
          }

          return result.value
        },
        cellClass: isSystemId ? 'system-id-column' : (isPublicId ? 'public-id-column' : ''),
        headerClass: isSystemId ? 'system-id-header' : (isPublicId ? 'public-id-header' : ''),
      }
    }),
  ]
})

const rowData = computed(() => {
  if (!props.modelValue || props.modelValue.length === 0) {
    return []
  }

  return buildGridRowData(props.modelValue, systemIdColumnIndex.value)
})

function onGridReady(params: GridReadyEvent) {
  gridApi.value = params.api
}

function getRowId(params: GetRowIdParams): string {
  return String(params.data?.id ?? '')
}

function serializeModelValue(rows: any[][]): string {
  return JSON.stringify(rows)
}

function emitModelValueUpdate(rows: any[][]) {
  const coerced = coerceGridRows(props.columns, rows)
  if (coerced.errors.length > 0) {
    setValidationErrors(coerced.errors)
    return
  }

  clearValidationErrors()
  lastEmittedModelSignature.value = serializeModelValue(coerced.rows)
  emit('update:modelValue', coerced.rows)
}

function onCellValueChanged(_event: CellValueChangedEvent) {
  const allRows = getAllRows(false)
  emitModelValueUpdate(allRows)
}

function onSelectionChanged() {
  const selectedRows = gridApi.value?.getSelectedRows() || []
  hasSelection.value = selectedRows.length > 0
}

function getAllRows(stopEditing = false): any[][] {
  if (!gridApi.value) {
    return []
  }

  if (stopEditing) {
    gridApi.value.stopEditing()
  }

  const rows: any[][] = []
  gridApi.value.forEachNode((node) => {
    const row: any[] = []
    for (let i = 0; i < props.columns.length; i += 1) {
      const value = node.data[`col_${i}`]
      row.push(value ?? null)
    }
    rows.push(row)
  })
  return rows
}

function getMaxSystemId(): number {
  if (!gridApi.value) {
    return 0
  }

  const systemIdIndex = props.columns.findIndex((col) => col === 'system_id')
  if (systemIdIndex === -1) {
    return 0
  }

  let maxId = 0
  gridApi.value.forEachNode((node) => {
    const systemIdValue = node.data[`col_${systemIdIndex}`]
    if (systemIdValue !== null && systemIdValue !== undefined) {
      const idNum = parseInt(String(systemIdValue), 10)
      if (!isNaN(idNum) && idNum > maxId) {
        maxId = idNum
      }
    }
  })

  return maxId
}

function createEmptyRowValues(nextSystemId: number): any[] {
  const newRow: any[] = []
  for (let i = 0; i < props.columns.length; i += 1) {
    const columnName = props.columns[i]
    if (columnName === 'system_id') {
      newRow.push(nextSystemId)
    } else {
      newRow.push(null)
    }
  }

  return newRow
}

function createEmptyRow(nextSystemId: number): Record<string, any> {
  return buildGridRowData([createEmptyRowValues(nextSystemId)], systemIdColumnIndex.value)[0] ?? { id: nextSystemId }
}

function addRow() {
  if (!gridApi.value) {
    return
  }

  gridApi.value.stopEditing()

  const maxSystemId = getMaxSystemId()
  const nextSystemId = maxSystemId + 1
  const newRow = createEmptyRow(nextSystemId)

  gridApi.value.applyTransaction({ add: [newRow] })

  const allRows = getAllRows(false)
  emitModelValueUpdate(allRows)
}

function deleteSelectedRows() {
  if (!gridApi.value) {
    return
  }

  gridApi.value.stopEditing()

  const selectedRows = gridApi.value.getSelectedRows()
  if (selectedRows.length === 0) {
    return
  }

  gridApi.value.applyTransaction({ remove: selectedRows })

  const allRows = getAllRows(false)
  emitModelValueUpdate(allRows)

  hasSelection.value = false
}

function getFocusedGridColumnIndex(): number {
  if (!gridApi.value) {
    return -1
  }

  const focusedCell = gridApi.value.getFocusedCell()
  if (!focusedCell?.column) {
    return -1
  }

  const colId = focusedCell.column.getColId()
  if (!colId.startsWith('col_')) {
    return -1
  }

  const match = colId.match(/^col_(\d+)$/)
  const indexText = match?.[1]
  return indexText ? parseInt(indexText, 10) : -1
}

function onPaste(event: ClipboardEvent) {
  if (!gridApi.value) {
    return
  }

  const text = event.clipboardData?.getData('text/plain')
  if (!text) {
    return
  }

  const focusedCell = gridApi.value.getFocusedCell()
  if (!focusedCell) {
    return
  }

  const startRowIndex = focusedCell.rowIndex
  const startColIndex = getFocusedGridColumnIndex()
  if (startRowIndex == null || startColIndex < 0) {
    return
  }

  const matrix = parseClipboardTable(text)
  if (matrix.length === 0) {
    return
  }

  event.preventDefault()
  gridApi.value.stopEditing()

  let nextSystemId = getMaxSystemId()
  const pasteResult = applyClipboardMatrix({
    rows: getAllRows(false),
    columns: props.columns,
    startRowIndex,
    startColIndex,
    matrix,
    createEmptyRow: () => {
      nextSystemId += 1
      return createEmptyRowValues(nextSystemId)
    },
  })

  if (pasteResult.errors.length > 0) {
    setValidationErrors(pasteResult.errors)
  } else {
    clearValidationErrors()
  }

  gridApi.value.setGridOption('rowData', buildGridRowData(pasteResult.rows, systemIdColumnIndex.value))
  emitModelValueUpdate(pasteResult.rows)
}

watch(
  () => props.modelValue,
  (newValue) => {
    const incomingRows = newValue || []
    const incomingSignature = serializeModelValue(incomingRows)

    if (incomingSignature === lastEmittedModelSignature.value) {
      return
    }

    const coerced = coerceGridRows(props.columns, incomingRows)
    const coercedSignature = serializeModelValue(coerced.rows)

    if (coerced.errors.length > 0) {
      setValidationErrors(coerced.errors)
    } else if (coercedSignature !== incomingSignature) {
      clearValidationErrors()
      emitModelValueUpdate(incomingRows)
      return
    }

    if (gridApi.value) {
      gridApi.value.setGridOption('rowData', rowData.value)
    }
  },
  { deep: true, immediate: true },
)
</script>

<style scoped>
.fixed-values-grid {
  width: 100%;
}

.compact-grid {
  font-size: 10px;
  --ag-background-color: rgb(var(--v-theme-background)) !important;
  --ag-foreground-color: rgb(var(--v-theme-on-background)) !important;
  --ag-header-foreground-color: rgb(var(--v-theme-on-surface)) !important;
  --ag-header-background-color: rgb(var(--v-theme-surface)) !important;
  --ag-odd-row-background-color: rgba(var(--v-theme-on-surface), 0.03) !important;
  --ag-row-hover-color: rgba(var(--v-theme-primary), 0.08) !important;
  --ag-border-color: rgba(var(--v-theme-on-surface), 0.12) !important;
  --ag-cell-horizontal-border: solid rgba(var(--v-theme-on-surface), 0.08) !important;
}

.compact-grid :deep(.ag-root-wrapper) {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 4px;
  background: rgb(var(--v-theme-background)) !important;
  color: rgb(var(--v-theme-on-background)) !important;
}

.compact-grid :deep(.ag-header) {
  background: rgb(var(--v-theme-surface)) !important;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12) !important;
}

.compact-grid :deep(.ag-header-cell) {
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface)) !important;
  background: rgb(var(--v-theme-surface)) !important;
}

.compact-grid :deep(.ag-header-cell-label) {
  font-size: 10px;
  color: rgb(var(--v-theme-on-surface)) !important;
}

.compact-grid :deep(.ag-cell) {
  padding: 2px 6px;
  font-size: 10px;
  line-height: 16px;
  color: rgb(var(--v-theme-on-background)) !important;
  border-color: rgba(var(--v-theme-on-surface), 0.08) !important;
  background: transparent;
}

.compact-grid :deep(.ag-row) {
  color: rgb(var(--v-theme-on-background)) !important;
  background: transparent;
}

.compact-grid :deep(.ag-row-odd) {
  background: rgba(var(--v-theme-on-surface), 0.03) !important;
}

.compact-grid :deep(.ag-row-even) {
  background: transparent !important;
}

.compact-grid :deep(.ag-row-hover) {
  background: rgba(var(--v-theme-primary), 0.08) !important;
}

.compact-grid :deep(.system-id-column) {
  background: rgba(var(--v-theme-surface), 0.5) !important;
  font-style: italic;
  color: rgba(var(--v-theme-on-background), 0.6) !important;
}

.compact-grid :deep(.system-id-header) {
  background: rgba(var(--v-theme-surface), 0.8) !important;
  font-weight: 700;
}

.compact-grid :deep(.public-id-column) {
  background: rgba(var(--v-theme-primary), 0.05) !important;
  font-weight: 500;
}

.compact-grid :deep(.public-id-header) {
  background: rgba(var(--v-theme-primary), 0.1) !important;
  font-weight: 700;
  color: rgb(var(--v-theme-primary)) !important;
}
</style>
