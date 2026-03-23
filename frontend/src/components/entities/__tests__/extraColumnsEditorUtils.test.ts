import { describe, expect, it } from 'vitest'

import {
  applySuggestionToExpression,
  analyzeExtraColumnExpression,
  extractFormulaReferences,
  extractInterpolationReferences,
  getExtraColumnDiagnostics,
  getExtraColumnSuggestions,
} from '../extraColumnsEditorUtils'

describe('extraColumnsEditorUtils', () => {
  it('extracts interpolation references', () => {
    expect(extractInterpolationReferences('{first_name} {last_name}')).toEqual(['first_name', 'last_name'])
  })

  it('extracts formula references without DSL function names', () => {
    expect(extractFormulaReferences("=concat(upper(code), trim(name))")).toEqual(['code', 'name'])
  })

  it('classifies copy expressions using available columns', () => {
    expect(analyzeExtraColumnExpression('existing_column', ['existing_column']).kind).toBe('copy')
  })

  it('classifies interpolation and formula expressions', () => {
    expect(analyzeExtraColumnExpression('{first} {last}').kind).toBe('interpolation')
    expect(analyzeExtraColumnExpression('=concat(first, last)').kind).toBe('formula')
  })

  it('reports duplicate and reserved-name conflicts', () => {
    const diagnostics = getExtraColumnDiagnostics(
      [
        { column: 'system_id', source: 'sample_code' },
        { column: 'system_id', source: '{sample_code}' },
      ],
      0,
      {
        reservedNames: ['system_id', 'sample_code'],
        availableColumns: ['sample_code'],
      }
    )

    expect(diagnostics.some((diagnostic) => diagnostic.severity === 'error' && diagnostic.message.includes('Duplicate'))).toBe(true)
    expect(diagnostics.some((diagnostic) => diagnostic.severity === 'error' && diagnostic.message.includes('reserved'))).toBe(true)
  })

  it('warns when interpolation references are not currently available', () => {
    const diagnostics = getExtraColumnDiagnostics(
      [{ column: 'label', source: '{country_name} / {sample_code}' }],
      0,
      {
        reservedNames: [],
        availableColumns: ['sample_code'],
      }
    )

    expect(diagnostics.some((diagnostic) => diagnostic.message.includes('Interpolates: country_name, sample_code'))).toBe(true)
    expect(diagnostics.some((diagnostic) => diagnostic.severity === 'warning' && diagnostic.message.includes('country_name'))).toBe(true)
  })

  it('suggests placeholders for empty or interpolation expressions', () => {
    expect(getExtraColumnSuggestions('', ['sample_code', 'country_name'])).toEqual([
      { label: '{sample_code}', value: '{sample_code}', category: 'placeholder' },
      { label: '{country_name}', value: '{country_name}', category: 'placeholder' },
    ])
  })

  it('suggests functions and raw columns for formula expressions', () => {
    const suggestions = getExtraColumnSuggestions('=concat(code)', ['code', 'name'])

    expect(suggestions.some((suggestion) => suggestion.category === 'function' && suggestion.value === 'upper()')).toBe(true)
    expect(suggestions.some((suggestion) => suggestion.category === 'column' && suggestion.value === 'name')).toBe(true)
  })

  it('applies suggestions based on expression mode', () => {
    expect(
      applySuggestionToExpression('', { label: 'concat()', value: 'concat()', category: 'function' }, ['code'])
    ).toBe('=concat()')

    expect(
      applySuggestionToExpression('{sample_code}', { label: '{country_name}', value: '{country_name}', category: 'placeholder' }, ['sample_code'])
    ).toBe('{sample_code} {country_name}')

    expect(
      applySuggestionToExpression('=concat(code', { label: 'name', value: 'name', category: 'column' }, ['code', 'name'])
    ).toBe('=concat(code, name')
  })
})
