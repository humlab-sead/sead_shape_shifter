export interface MaterializationRoundTripState {
  externalValuesDirective: string | null
  materializedConfig: Record<string, any> | null
  inlineValues: any[][]
}

/**
 * Fixed-entity columns in YAML include the full persisted row schema.
 * The form hides identity columns, but keeps business-key columns visible so
 * the editable grid shape remains obvious to users.
 */
export function normalizeEditableFixedColumns(
  columns: string[],
  keys: string[],
  publicId: string | null | undefined
): string[] {
  const hiddenColumns = new Set<string>(['system_id'])

  if (publicId && publicId.trim().length > 0) {
    hiddenColumns.add(publicId)
  }

  return columns.filter((column) => !hiddenColumns.has(column))
}

/**
 * Build the canonical fixed-values column order.
 */
export function buildFixedValuesColumns(
  columns: string[],
  keys: string[],
  publicId: string | null | undefined
): string[] {
  const canonical: string[] = ['system_id']

  if (publicId && publicId.trim().length > 0) {
    canonical.push(publicId)
  }

  for (const key of keys) {
    if (typeof key === 'string' && key.trim().length > 0 && !canonical.includes(key)) {
      canonical.push(key)
    }
  }

  for (const column of columns) {
    if (typeof column !== 'string' || column.trim().length === 0) {
      continue
    }
    if (!canonical.includes(column)) {
      canonical.push(column)
    }
  }

  return canonical
}

/**
 * Normalize inline fixed rows for the editor/grid.
 *
 * Older project files may store fixed rows in a data-only layout that matches
 * the persisted `columns` array exactly, without an explicit `system_id` column.
 * The editor grid, preview override config, and external values update flow all
 * operate on the canonical full column order, so expand those legacy rows here.
 */
export function normalizeFixedValuesRowsForForm(
  values: any[][],
  storedColumns: string[],
  keys: string[],
  publicId: string | null | undefined
): any[][] {
  if (!Array.isArray(values) || values.length === 0) {
    return values
  }

  const fullColumns = buildFixedValuesColumns(storedColumns, keys, publicId)
  const rowLength = Array.isArray(values[0]) ? values[0].length : 0

  if (rowLength === 0 || values.some((row) => !Array.isArray(row) || row.length !== rowLength)) {
    return values
  }

  if (rowLength === fullColumns.length) {
    return values
  }

  if (rowLength !== storedColumns.length) {
    return values
  }

  return values.map((row, rowIndex) => {
    const expandedRow = fullColumns.map((columnName) => {
      const storedIndex = storedColumns.indexOf(columnName)
      if (storedIndex >= 0) {
        return row[storedIndex] ?? null
      }

      if (columnName === 'system_id') {
        return rowIndex + 1
      }

      return null
    })

    return expandedRow
  })
}

/**
 * Remap fixed rows when the editor schema changes in memory.
 *
 * The grid stores rows positionally, but users expect edits to follow column
 * names. When keys/columns move in or out of the fixed schema, rebuild rows by
 * column name so surviving fields keep their values.
 */
export function remapFixedValuesRowsToColumns(
  values: any[][],
  fromColumns: string[],
  toColumns: string[]
): any[][] {
  if (!Array.isArray(values) || values.length === 0) {
    return values
  }

  if (JSON.stringify(fromColumns) === JSON.stringify(toColumns)) {
    return values
  }

  return values.map((row, rowIndex) => {
    const rowByColumn = new Map<string, any>()

    fromColumns.forEach((columnName, index) => {
      rowByColumn.set(columnName, row[index] ?? null)
    })

    return toColumns.map((columnName) => {
      if (rowByColumn.has(columnName)) {
        return rowByColumn.get(columnName)
      }

      if (columnName === 'system_id') {
        return rowByColumn.get('system_id') ?? rowIndex + 1
      }

      return null
    })
  })
}

/**
 * Extract materialization fields so they can be round-tripped through form state.
 */
export function extractMaterializationRoundTripState(entityData: Record<string, any>): MaterializationRoundTripState {
  const rawValues = entityData.values

  return {
    externalValuesDirective:
      typeof rawValues === 'string' && rawValues.startsWith('@load:') ? rawValues : null,
    materializedConfig:
      entityData.materialized && typeof entityData.materialized === 'object'
        ? (entityData.materialized as Record<string, any>)
        : null,
    inlineValues: Array.isArray(rawValues) ? rawValues : [],
  }
}

/**
 * Apply preserved materialization fields when building fixed-entity save payloads.
 */
export function applyMaterializationRoundTripToFixedEntity(
  entityData: Record<string, unknown>,
  values: any[][],
  externalValuesDirective: string | null,
  materializedConfig: Record<string, any> | null
): void {
  entityData.values = externalValuesDirective || values || []

  if (materializedConfig) {
    entityData.materialized = materializedConfig
  }
}

/**
 * Select columns for external values update requests.
 * Fixed entities must use the full positional grid columns.
 */
export function getExternalValuesUpdateColumns(
  entityType: string,
  formColumns: string[],
  fixedValuesColumns: string[]
): string[] {
  return entityType === 'fixed' ? fixedValuesColumns : formColumns
}
