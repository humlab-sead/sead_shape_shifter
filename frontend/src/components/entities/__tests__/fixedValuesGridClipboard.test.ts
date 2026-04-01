import { describe, expect, it } from 'vitest'

import { applyClipboardMatrix, buildGridRowData, parseClipboardTable } from '../fixedValuesGridClipboard'

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

    expect(updated).toEqual([
      [1, 'oak', null],
      [3, 'pine', 'count'],
    ])
  })

  it('builds grid row ids from stable system_id values', () => {
    expect(buildGridRowData([[10, 'oak']], 0)).toEqual([
      { id: 10, col_0: 10, col_1: 'oak' },
    ])
  })
})
