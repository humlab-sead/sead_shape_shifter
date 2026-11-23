import { describe, expect, it } from 'vitest'
import type { SelectionDisplayField, SelectionRecord } from '@/types/reconciliation'
import { displayedSelectionFields, selectionFieldValue } from '../selectionRecord'

function record(overrides: Partial<SelectionRecord> = {}): SelectionRecord {
  return {
    id: 'https://w3id.org/sead/id/feature_type/101',
    target_id: 101,
    type: 'feature_type',
    name: 'Bronze Age',
    description: 'A period',
    fields: {},
    score: null,
    ...overrides,
  }
}

describe('selectionFieldValue', () => {
  it('reads record-level fields by name', () => {
    const value = record()

    expect(selectionFieldValue(value, 'name')).toBe('Bronze Age')
    expect(selectionFieldValue(value, 'target_id')).toBe(101)
    expect(selectionFieldValue(value, 'description')).toBe('A period')
    expect(selectionFieldValue(value, 'id')).toBe('https://w3id.org/sead/id/feature_type/101')
  })

  it('reads field-sourced values from the fields map', () => {
    const value = record({ fields: { coordinate_n: 64.5 } })

    expect(selectionFieldValue(value, 'coordinate_n')).toBe(64.5)
  })

  it('returns null for a field the record does not carry', () => {
    expect(selectionFieldValue(record(), 'missing')).toBeNull()
    expect(selectionFieldValue(record({ description: null }), 'description')).toBeNull()
  })
})

describe('displayedSelectionFields', () => {
  it('keeps the declared order and drops hidden fields', () => {
    const fields: SelectionDisplayField[] = [
      { name: 'name', source: 'record', label: 'Name', value_type: 'string', display: true },
      { name: 'target_id', source: 'record', label: 'ID', value_type: 'integer', display: true },
      { name: 'notes', source: 'fields', label: 'Notes', value_type: 'string', display: false },
      { name: 'description', source: 'record', label: 'Description', value_type: 'string', display: true },
    ]

    expect(displayedSelectionFields(fields).map((field) => field.name)).toEqual(['name', 'target_id', 'description'])
  })

  it('falls back to name and ID when nothing is declared', () => {
    expect(displayedSelectionFields([]).map((field) => field.name)).toEqual(['name', 'target_id'])
    expect(displayedSelectionFields(null).map((field) => field.name)).toEqual(['name', 'target_id'])
  })

  it('returns a copy so callers cannot mutate the fallback', () => {
    const first = displayedSelectionFields(null)
    first[0]!.label = 'Changed'

    expect(displayedSelectionFields(null)[0]!.label).toBe('Name')
  })
})
