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

    <v-alert v-if="validationSummary.length > 0" type="error" variant="tonal" density="compact" class="mb-2">
      <div v-for="error in validationSummary" :key="error" class="text-caption">{{ error }}</div>
    </v-alert>

    <ag-grid-vue class="ag-theme-alpine compact-grid" :style="{ height: gridHeight }" :columnDefs="columnDefs"
      :rowData="rowData" :getRowId="getRowId" :defaultColDef="defaultColDef" :components="gridComponents"
      :rowSelection="'multiple'" :suppressRowClickSelection="true" :animateRows="true" :headerHeight="48" :rowHeight="26" :singleClickEdit="true"
      :stopEditingWhenCellsLoseFocus="true" @grid-ready="onGridReady" @cell-value-changed="onCellValueChanged"
      @selection-changed="onSelectionChanged" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type { CellValueChangedEvent, ColDef, GetRowIdParams, GridApi, GridReadyEvent } from 'ag-grid-community'
import FixedValuesGridHeader from './FixedValuesGridHeader.vue'
import {
  applyClipboardMatrix,
  buildGridRowData,
  coerceGridRows,
  coerceGridValue,
  type FixedGridColumnTypeName,
  type GridValidationIssue,
  inferColumnType,
  normalizeGridColumnTypes,
  parseClipboardTable,
  summarizeValidationIssues,
} from './fixedValuesGridClipboard'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'

interface ColumnTypeOption {
  value: 'auto' | FixedGridColumnTypeName
  label: string
}

interface ColumnTypeHeaderParams {
  columnName: string
  getSelectorValue: (columnName: string) => 'auto' | FixedGridColumnTypeName
  getSourceLabel: (columnName: string) => string
  getOptions: (columnName: string) => ColumnTypeOption[]
  onTypeChange: (columnName: string, nextValue: 'auto' | FixedGridColumnTypeName) => void
}

interface Props {
  modelValue: any[][]
  columns: string[]
  columnTypes?: Record<string, string>
  publicId?: string
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '300px',
  columnTypes: () => ({}),
  publicId: undefined,
})

const emit = defineEmits<{
  'update:modelValue': [value: any[][]]
  'update:columnTypes': [value: Record<string, string>]
  'validation-errors': [value: string[]]
}>()

const gridApi = ref<GridApi>()
const hasSelection = ref(false)
const lastEmittedModelSignature = ref<string | null>(null)
const validationSummary = ref<string[]>([])
const invalidCellMessages = ref<Record<string, string>>({})
const gridComponents = {
  FixedValuesGridHeader,
}

const gridHeight = computed(() => props.height)
const systemIdColumnIndex = computed(() => props.columns.findIndex((col) => col === 'system_id'))
const normalizedColumnTypes = computed<Record<string, FixedGridColumnTypeName>>(() => normalizeGridColumnTypes(props.columnTypes))

const defaultColDef: ColDef = {
  editable: true,
  sortable: true,
  filter: true,
  resizable: true,
  minWidth: 100,
  flex: 1,
}

function buildInvalidCellKey(rowIndex: number, columnName: string): string {
  return `${rowIndex}:${columnName}`
}

function setValidationIssues(issues: GridValidationIssue[]) {
  invalidCellMessages.value = Object.fromEntries(
    issues.map((issue) => [buildInvalidCellKey(issue.rowIndex, issue.columnName), issue.message])
  )

  const summary = summarizeValidationIssues(issues)
  validationSummary.value = summary
  emit('validation-errors', summary)
}

function clearValidationIssues() {
  if (validationSummary.value.length === 0 && Object.keys(invalidCellMessages.value).length === 0) {
    return
  }

  validationSummary.value = []
  invalidCellMessages.value = {}
  emit('validation-errors', [])
}

function hasValidationIssue(rowIndex: number, columnName: string): boolean {
  return Boolean(invalidCellMessages.value[buildInvalidCellKey(rowIndex, columnName)])
}

function getValidationIssueMessage(rowIndex: number, columnName: string): string | undefined {
  return invalidCellMessages.value[buildInvalidCellKey(rowIndex, columnName)]
}

function formatTypeLabel(typeName: FixedGridColumnTypeName): string {
  if (typeName === 'int') {
    return 'Integer'
  }

  return typeName.charAt(0).toUpperCase() + typeName.slice(1)
}

function getColumnTypeSelectorValue(columnName: string): 'auto' | FixedGridColumnTypeName {
  return normalizedColumnTypes.value[columnName] || 'auto'
}

function getColumnTypeSourceLabel(columnName: string): string {
  const explicitType = normalizedColumnTypes.value[columnName]

  if (explicitType) {
    return `Declared: ${explicitType}`
  }

  return `Inferred: ${inferColumnType(columnName) === 'number' ? 'int' : 'string'}`
}

function getColumnTypeOptions(columnName: string): ColumnTypeOption[] {
  const currentType = normalizedColumnTypes.value[columnName]
  const inferredType = inferColumnType(columnName) === 'number' ? 'int' : 'string'
  const autoLabel = `Auto (${inferredType})`
  const options: ColumnTypeOption[] = [
    { value: 'auto', label: autoLabel },
    { value: 'int', label: 'Integer' },
    { value: 'string', label: 'String' },
  ]

  if (currentType && !['int', 'string'].includes(currentType)) {
    options.unshift({ value: currentType, label: `Preserve: ${formatTypeLabel(currentType)}` })
  }

  return options
}

function updateColumnType(columnName: string, nextValue: 'auto' | FixedGridColumnTypeName): void {
  const nextColumnTypes: Record<string, string> = { ...normalizedColumnTypes.value }

  if (!nextValue || nextValue === 'auto') {
    delete nextColumnTypes[columnName]
  } else {
    nextColumnTypes[columnName] = nextValue
  }

  emit('update:columnTypes', nextColumnTypes)
}

function buildHeaderParams(columnName: string): ColumnTypeHeaderParams {
  return {
    columnName,
    getSelectorValue: getColumnTypeSelectorValue,
    getSourceLabel: getColumnTypeSourceLabel,
    getOptions: getColumnTypeOptions,
    onTypeChange: updateColumnType,
  }
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

      return {
        field: `col_${index}`,
        headerName: col,
        headerComponent: isSystemId ? undefined : 'FixedValuesGridHeader',
        headerComponentParams: isSystemId ? undefined : buildHeaderParams(col),
        editable: !isSystemId,
        sortable: true,
        filter: true,
        resizable: true,
        minWidth: 100,
        flex: 1,
        valueParser: isSystemId ? undefined : (params: any) => {
          const result = coerceGridValue(col, params.newValue, params.oldValue, props.columnTypes)

          if (result.error) {
            setValidationIssues([{ rowIndex: params.node?.rowIndex ?? 0, columnName: col, message: result.error }])
            return params.oldValue
          }

          return result.value
        },
        cellClass: isSystemId ? 'system-id-column' : (isPublicId ? 'public-id-column' : ''),
        cellClassRules: {
          'invalid-fixed-value-cell': (params: any) => hasValidationIssue(params.node?.rowIndex ?? -1, col),
        },
        headerClass: isSystemId ? 'system-id-header' : (isPublicId ? 'public-id-header' : ''),
        tooltipValueGetter: (params: any) => getValidationIssueMessage(params.node?.rowIndex ?? -1, col) || null,
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
  const coerced = coerceGridRows(props.columns, rows, props.columnTypes)
  if (coerced.issues.length > 0) {
    setValidationIssues(coerced.issues)
    return
  }

  clearValidationIssues()
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
    columnTypes: props.columnTypes,
    startRowIndex,
    startColIndex,
    matrix,
    createEmptyRow: () => {
      nextSystemId += 1
      return createEmptyRowValues(nextSystemId)
    },
  })

  if (pasteResult.issues.length > 0) {
    setValidationIssues(pasteResult.issues)
  } else {
    clearValidationIssues()
  }

  gridApi.value.setGridOption('rowData', buildGridRowData(pasteResult.rows, systemIdColumnIndex.value))
  emitModelValueUpdate(pasteResult.rows)
}

watch(
  [() => props.modelValue, () => props.columnTypes],
  ([newValue]) => {
    const incomingRows = newValue || []
    const incomingSignature = serializeModelValue(incomingRows)

    if (incomingSignature === lastEmittedModelSignature.value) {
      return
    }

    const coerced = coerceGridRows(props.columns, incomingRows, props.columnTypes)
    const coercedSignature = serializeModelValue(coerced.rows)

    if (coerced.issues.length > 0) {
      setValidationIssues(coerced.issues)
    } else if (coercedSignature !== incomingSignature) {
      clearValidationIssues()
      emitModelValueUpdate(incomingRows)
      return
    } else {
      clearValidationIssues()
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

.compact-grid :deep(.invalid-fixed-value-cell) {
  background: rgba(var(--v-theme-error), 0.12) !important;
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-error), 0.35);
}
</style>
