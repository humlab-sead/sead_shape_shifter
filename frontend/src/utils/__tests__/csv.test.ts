import { describe, expect, it } from 'vitest'
import { formatCsvCell, toCsv } from '../csv'

describe('formatCsvCell', () => {
  it('leaves plain text unquoted', () => {
    expect(formatCsvCell('MISSING-A')).toBe('MISSING-A')
    expect(formatCsvCell(42)).toBe('42')
  })

  it('writes null and undefined as an empty cell', () => {
    expect(formatCsvCell(null)).toBe('')
    expect(formatCsvCell(undefined)).toBe('')
  })

  it('quotes values that contain a delimiter, quote, or line break', () => {
    expect(formatCsvCell('a,b')).toBe('"a,b"')
    expect(formatCsvCell('say "hi"')).toBe('"say ""hi"""')
    expect(formatCsvCell('line1\nline2')).toBe('"line1\nline2"')
  })

  it('serializes an object key part instead of dropping it', () => {
    expect(formatCsvCell({ value: 'x' })).toBe('"{""value"":""x""}"')
  })
})

describe('toCsv', () => {
  it('writes a header row even when there are no value rows', () => {
    expect(toCsv(['Unmatched key', 'Local rows'], [])).toBe('Unmatched key,Local rows')
  })

  it('writes one row per value row', () => {
    const csv = toCsv(
      ['code', 'Local rows'],
      [
        ['MISSING-A', 1],
        ['MISSING-B', 3],
      ]
    )

    expect(csv.split('\r\n')).toEqual(['code,Local rows', 'MISSING-A,1', 'MISSING-B,3'])
  })

  it('pads a short row so later columns stay aligned', () => {
    expect(toCsv(['a', 'b'], [['only-a']])).toBe('a,b\r\nonly-a,')
  })
})
