import { describe, expect, it } from 'vitest'

import {
  applyClipboardMatrix,
  buildGridRowData,
  coerceGridRows,
  coerceGridValue,
  inferColumnType,
  normalizeGridColumnTypes,
  parseClipboardTable,
  parseStrictInteger,
  summarizeValidationIssues,
} from '../fixedValuesGridClipboard'

describe('fixedValuesGridClipboard', () => {
  it('removes only trailing empty clipboard rows', () => {
    expect(parseClipboardTable('a\tb\n\nc\td\n')).toEqual([
      ['a', 'b'],
      [''],
      ['c', 'd'],
    ])
  })

  it('extends rows, preserves system_id, and normalizes blank pasted cells to null', () => {
    let nextSystemId = 2
    const updated = applyClipboardMatrix({
      rows: [[1, 'alpha', 'beta']],
      columns: ['system_id', 'name', 'note'],
      startRowIndex: 0,
      startColIndex: 0,
      matrix: [
        ['999', 'oak', ''],
        ['1000', 'pine', 'count'],
      ],
      createEmptyRow: () => {
        nextSystemId += 1
        return [nextSystemId, null, null]
      },
    })

    expect(updated.rows).toEqual([
      [1, 'oak', null],
      [3, 'pine', 'count'],
    ])
    expect(updated.errors).toEqual([])
  })

  it('builds grid row ids from stable system_id values', () => {
    expect(buildGridRowData([[10, 'oak']], 0)).toEqual([
      { id: 10, col_0: 10, col_1: 'oak' },
    ])
  })

  it('infers _id columns as numeric and other columns as string', () => {
    expect(inferColumnType('system_id')).toBe('number')
    expect(inferColumnType('method_group_id')).toBe('number')
    expect(inferColumnType('label')).toBe('string')
  })

  it('uses explicit fixed column types ahead of naming inference', () => {
    expect(inferColumnType('rank', { rank: 'int' })).toBe('number')
    expect(inferColumnType('label', { label: 'string' })).toBe('string')
    expect(inferColumnType('created_at', { created_at: 'date' })).toBe('preserve')
  })

  it('parses strict integers without truncation', () => {
    expect(parseStrictInteger('53')).toBe(53)
    expect(parseStrictInteger('-7')).toBe(-7)
    expect(parseStrictInteger('')).toBeNull()
    expect(parseStrictInteger('53abc')).toBeNull()
    expect(parseStrictInteger('53.9')).toBeNull()
  })

  it('rejects invalid _id paste values and preserves the previous cell value', () => {
    const updated = applyClipboardMatrix({
      rows: [[1, 53, 'alpha']],
      columns: ['system_id', 'method_group_id', 'label'],
      startRowIndex: 0,
      startColIndex: 1,
      matrix: [['53abc']],
      createEmptyRow: () => [2, null, null],
    })

    expect(updated.rows).toEqual([[1, 53, 'alpha']])
    expect(updated.errors).toEqual([
      'Row 1, column method_group_id: Expected integer ID',
    ])
  })

  it('coerces valid _id values and preserves strings elsewhere', () => {
    expect(coerceGridValue('method_group_id', '53', null)).toEqual({
      value: 53,
      error: null,
    })
    expect(coerceGridValue('label', 'Method A', null)).toEqual({
      value: 'Method A',
      error: null,
    })
  })

  it('coerces declared int columns even when the name does not end with _id', () => {
    expect(coerceGridValue('rank', '7', null, { rank: 'int' })).toEqual({
      value: 7,
      error: null,
    })
    expect(coerceGridValue('rank', '7x', 3, { rank: 'int' })).toEqual({
      value: 3,
      error: 'Expected integer value',
    })
  })

  it('preserves unsupported-yet declared types without coercing loaded scalar values', () => {
    expect(coerceGridValue('created_at', '2026-05-19', null, { created_at: 'date' })).toEqual({
      value: '2026-05-19',
      error: null,
    })
    expect(coerceGridRows(['system_id', 'is_active'], [[1, true]], { is_active: 'bool' })).toEqual({
      rows: [[1, true]],
      issues: [],
      errors: [],
    })
  })

  it('coerces loaded rows so save can persist normalized integer ids', () => {
    expect(coerceGridRows(['system_id', 'method_group_id', 'label'], [[1, '53', 'Method A']])).toEqual({
      rows: [[1, 53, 'Method A']],
      issues: [],
      errors: [],
    })
  })

  it('collects row errors when loaded values contain invalid integer ids', () => {
    expect(coerceGridRows(['system_id', 'method_group_id', 'label'], [[1, '53abc', 'Method A']])).toEqual({
      rows: [[1, '53abc', 'Method A']],
      issues: [{ rowIndex: 0, columnName: 'method_group_id', message: 'Expected integer ID' }],
      errors: ['Row 1, column method_group_id: Expected integer ID'],
    })
  })

  it('summarizes validation issues per column', () => {
    expect(summarizeValidationIssues([
      { rowIndex: 0, columnName: 'rank', message: 'Expected integer value' },
      { rowIndex: 2, columnName: 'rank', message: 'Expected integer value' },
    ])).toEqual([
      'Column rank: 2 invalid values (rows 1, 3)',
    ])
  })

  it('normalizes only supported fixed column types', () => {
    expect(normalizeGridColumnTypes({ rank: 'INT', label: 'string', skip: 'json' })).toEqual({
      rank: 'int',
      label: 'string',
    })
  })
})
