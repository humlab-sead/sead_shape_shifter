/**
 * Read declared display values from one record-selection result.
 *
 * The reconciliation service advertises `display_fields` for each selectable
 * type, with a `source` of `record` or `fields`. The browse filter and the
 * browse grid both read values through these helpers, so a column and the
 * filter that hides rows in it can never disagree.
 */

import type { SelectionDisplayField, SelectionRecord } from '@/types/reconciliation'

/** Shown when a type declares no display fields at all. */
const FALLBACK_SELECTION_FIELDS: SelectionDisplayField[] = [
  { name: 'name', source: 'record', label: 'Name', value_type: 'string', display: true },
  { name: 'target_id', source: 'record', label: 'ID', value_type: 'integer', display: true },
]

/**
 * Read one field from a selection record.
 *
 * Record-level fields are read by name. Anything else is looked up in the
 * record's `fields` map, which is where field-sourced display fields live.
 * Returns null when the record has no value for the field.
 */
export function selectionFieldValue(record: SelectionRecord, field: string): unknown {
  switch (field) {
    case 'id':
      return record.id
    case 'target_id':
      return record.target_id
    case 'type':
      return record.type
    case 'name':
      return record.name
    case 'description':
      return record.description ?? null
    case 'score':
      return record.score ?? null
    default:
      return record.fields?.[field] ?? null
  }
}

/**
 * Return the display fields to show, in their declared order.
 *
 * Fields the service marked `display: false` are dropped. A type that declares
 * no display fields falls back to name and ID so the grid is never empty.
 */
export function displayedSelectionFields(
  fields: readonly SelectionDisplayField[] | null | undefined
): SelectionDisplayField[] {
  const declared = (fields ?? []).filter((field) => field.display)
  const source = declared.length > 0 ? declared : FALLBACK_SELECTION_FIELDS
  // Copy each descriptor so a caller cannot mutate the shared fallback list.
  return source.map((field) => ({ ...field }))
}
