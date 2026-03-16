import { describe, expect, it } from 'vitest'

import { normalizeForeignKeyKeys } from '../foreignKeyEditorUtils'

describe('normalizeForeignKeyKeys', () => {
  it('deduplicates repeated string keys while preserving order', () => {
    expect(normalizeForeignKeyKeys(['X', 'X', 'Y', 'X', 'Y', 'Z', 'Z'])).toEqual(['X', 'Y', 'Z'])
  })

  it('normalizes object values from combobox selections', () => {
    expect(normalizeForeignKeyKeys([{ value: 'alpha' }, { value: 'beta' }, { value: 'alpha' }])).toEqual(['alpha', 'beta'])
  })

  it('wraps a scalar directive string as a single value', () => {
    expect(normalizeForeignKeyKeys(' @value:keys.site ')).toEqual(['@value:keys.site'])
  })

  it('drops empty and invalid values', () => {
    expect(normalizeForeignKeyKeys(['', '  ', null, undefined, { value: '' }, { value: 'ok' }])).toEqual(['ok'])
  })
})