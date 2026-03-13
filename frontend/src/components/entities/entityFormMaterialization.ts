export interface MaterializationRoundTripState {
  externalValuesDirective: string | null
  materializedConfig: Record<string, any> | null
  inlineValues: any[][]
}

/**
 * Fixed-entity columns in YAML already include identity columns and keys.
 * The form edits keys separately, so strip those columns out of the editable
 * columns array to avoid duplicating them on save.
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

  for (const key of keys) {
    if (typeof key === 'string' && key.trim().length > 0) {
      hiddenColumns.add(key)
    }
  }

  return columns.filter((column) => !hiddenColumns.has(column))
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
