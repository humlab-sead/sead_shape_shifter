<template>
  <div class="fixed-values-grid">
    <div class="d-flex justify-space-between align-center mb-2">
      <span class="text-caption">Fixed Values Data</span>
      <div>
        <v-btn size="small" variant="outlined" prepend-icon="mdi-plus" @click="addRow" class="mr-2"> Add Row </v-btn>
        <v-btn
          size="small"
          variant="outlined"
          prepend-icon="mdi-delete"
          color="error"
          @click="deleteSelectedRows"
          :disabled="!hasSelection"
        >
          Delete Selected
        </v-btn>
      </div>
    </div>
    <ag-grid-vue
      ref="gridRef"
      class="ag-theme-alpine compact-grid"
      :style="{ height: gridHeight }"
      :columnDefs="columnDefs"
      :rowData="rowData"
      :defaultColDef="defaultColDef"
      :rowSelection="'multiple'"
      :suppressRowClickSelection="true"
      :animateRows="true"
      :headerHeight="28"
      :rowHeight="26"
      @grid-ready="onGridReady"
      @cell-value-changed="onCellValueChanged"
      @selection-changed="onSelectionChanged"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import type { ColDef, GridApi, GridReadyEvent, CellValueChangedEvent } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'

interface Props {
  modelValue: any[][] // 2D array of values (includes all columns)
  columns: string[] // All column names including system_id and public_id
  publicId?: string // Name of the public_id column (for special styling)
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '300px',
  publicId: undefined,
})

const emit = defineEmits<{
  'update:modelValue': [value: any[][]]
}>()

const gridRef = ref<InstanceType<typeof AgGridVue>>()
const gridApi = ref<GridApi>()
const hasSelection = ref(false)

// Grid configuration
const gridHeight = computed(() => props.height)

const defaultColDef: ColDef = {
  editable: true,
  sortable: true,
  filter: true,
  resizable: true,
  minWidth: 100,
  flex: 1,
}

// Generate column definitions from props.columns
// Detect system_id and public_id columns and apply special behavior
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
        // system_id is read-only, others are editable
        editable: !isSystemId,
        sortable: true,
        filter: true,
        resizable: true,
        minWidth: 100,
        flex: 1,
        // Ensure system_id is always an integer
        valueParser: isSystemId ? (params: any) => {
          const val = params.newValue
          return val !== null && val !== undefined ? parseInt(String(val), 10) : val
        } : undefined,
        // Apply special styling
        cellClass: isSystemId ? 'system-id-column' : (isPublicId ? 'public-id-column' : ''),
        headerClass: isSystemId ? 'system-id-header' : (isPublicId ? 'public-id-header' : ''),
      }
    }),
  ]
})

// Convert 2D array to row objects for ag-grid
// Auto-populate system_id column with sequence numbers
const rowData = computed(() => {
  if (!props.modelValue || props.modelValue.length === 0) {
    return []
  }

  return props.modelValue.map((row, rowIndex) => {
    const rowObj: any = { id: rowIndex }
    row.forEach((value, colIndex) => {
      const columnName = props.columns[colIndex]
      // Auto-populate system_id with sequential numbers (1-based) as integer
      if (columnName === 'system_id') {
        // Always use rowIndex + 1 for display (system_id is auto-managed)
        rowObj[`col_${colIndex}`] = rowIndex + 1
      } else {
        rowObj[`col_${colIndex}`] = value
      }
    })
    return rowObj
  })
})

function onGridReady(params: GridReadyEvent) {
  gridApi.value = params.api
}

function onCellValueChanged(event: CellValueChangedEvent) {
  // Convert row objects back to 2D array
  const allRows = getAllRows()
  emit('update:modelValue', allRows)
}

function onSelectionChanged() {
  const selectedRows = gridApi.value?.getSelectedRows() || []
  hasSelection.value = selectedRows.length > 0
}

function getAllRows(): any[][] {
  if (!gridApi.value) return []

  const rows: any[][] = []
  gridApi.value.forEachNode((node) => {
    const row: any[] = []
    // Save ALL column values including system_id and public_id
    // The columns field in YAML includes all columns, values must match
    for (let i = 0; i < props.columns.length; i++) {
      const value = node.data[`col_${i}`]
      row.push(value ?? null)
    }
    rows.push(row)
  })
  return rows
}

function addRow() {
  if (!gridApi.value) return

  // Get current row count to calculate next system_id
  let rowCount = 0
  gridApi.value.forEachNode(() => rowCount++)

  // Create a new row with null values for all columns
  const newRow: any = { id: Date.now() }
  for (let i = 0; i < props.columns.length; i++) {
    const columnName = props.columns[i]
    // Auto-populate system_id with next sequential number as integer
    if (columnName === 'system_id') {
      newRow[`col_${i}`] = parseInt(String(rowCount + 1), 10)
    } else {
      newRow[`col_${i}`] = null
    }
  }

  gridApi.value.applyTransaction({ add: [newRow] })

  // Update model
  const allRows = getAllRows()
  emit('update:modelValue', allRows)
}

function deleteSelectedRows() {
  if (!gridApi.value) return

  const selectedRows = gridApi.value.getSelectedRows()
  if (selectedRows.length === 0) return

  gridApi.value.applyTransaction({ remove: selectedRows })

  // Update model
  const allRows = getAllRows()
  emit('update:modelValue', allRows)

  hasSelection.value = false
}

// Watch for external changes to modelValue
watch(
  () => props.modelValue,
  () => {
    if (gridApi.value) {
      gridApi.value.setGridOption('rowData', rowData.value)
    }
  },
  { deep: true }
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

/* system_id column - read-only, auto-numbered */
.compact-grid :deep(.system-id-column) {
  background: rgba(var(--v-theme-surface), 0.5) !important;
  font-style: italic;
  color: rgba(var(--v-theme-on-background), 0.6) !important;
}

.compact-grid :deep(.system-id-header) {
  background: rgba(var(--v-theme-surface), 0.8) !important;
  font-weight: 700;
}

/* public_id column - editable, highlighted */
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
