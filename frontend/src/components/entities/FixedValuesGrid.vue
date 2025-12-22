<template>
  <div class="fixed-values-grid">
    <div class="d-flex justify-space-between align-center mb-2">
      <span class="text-caption">Fixed Values Data</span>
      <div>
        <v-btn
          size="small"
          variant="outlined"
          prepend-icon="mdi-plus"
          @click="addRow"
          class="mr-2"
        >
          Add Row
        </v-btn>
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
  modelValue: any[][] // 2D array of values
  columns: string[] // Column names from keys + columns
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '300px',
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
    ...props.columns.map((col, index) => ({
      field: `col_${index}`,
      headerName: col,
      editable: true,
    })),
  ]
})

// Convert 2D array to row objects for ag-grid
const rowData = computed(() => {
  if (!props.modelValue || props.modelValue.length === 0) {
    return []
  }

  return props.modelValue.map((row, rowIndex) => {
    const rowObj: any = { id: rowIndex }
    row.forEach((value, colIndex) => {
      rowObj[`col_${colIndex}`] = value
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

  // Create a new row with null values
  const newRow: any = { id: Date.now() }
  for (let i = 0; i < props.columns.length; i++) {
    newRow[`col_${i}`] = null
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
  font-size: 12px;
}

:deep(.ag-header-cell-label) {
  font-size: 12px;
}

:deep(.ag-cell) {
  font-size: 12px;
}

:deep(.ag-root-wrapper) {
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
}
</style>
