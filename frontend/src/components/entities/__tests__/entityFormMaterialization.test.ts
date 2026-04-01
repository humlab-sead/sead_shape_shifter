import { describe, expect, it } from 'vitest'

import {
  buildFixedValuesColumns,
  applyMaterializationRoundTripToFixedEntity,
  extractMaterializationRoundTripState,
  getExternalValuesUpdateColumns,
  normalizeFixedValuesRowsForForm,
  remapFixedValuesRowsToColumns,
  normalizeEditableFixedColumns,
} from '../entityFormMaterialization'

describe('entityFormMaterialization', () => {
  it('extracts @load directive and materialized metadata from entity data', () => {
    const entityData = {
      type: 'fixed',
      values: '@load:materialized/feature_type.parquet',
      materialized: {
        enabled: true,
        materialized_at: '2026-03-06T09:13:44.556193',
        source_state: {
          type: 'sql',
          query: 'select [Befundtyp], [Beschreibung] from [Befundtypen];',
        },
      },
    }

    const result = extractMaterializationRoundTripState(entityData)

    expect(result.externalValuesDirective).toBe('@load:materialized/feature_type.parquet')
    expect(result.inlineValues).toEqual([])
    expect(result.materializedConfig).toEqual(entityData.materialized)
  })

  it('extracts inline values when entity is not externally loaded', () => {
    const entityData = {
      type: 'fixed',
      values: [
        [1, null, 'value_a'],
        [2, null, 'value_b'],
      ],
    }

    const result = extractMaterializationRoundTripState(entityData)

    expect(result.externalValuesDirective).toBeNull()
    expect(result.materializedConfig).toBeNull()
    expect(result.inlineValues).toEqual(entityData.values)
  })

  it('applies round-trip fields to fixed entity save payload', () => {
    const savePayload: Record<string, unknown> = {
      type: 'fixed',
      columns: ['system_id', 'feature_type_id', 'description'],
    }

    const materializedConfig = {
      enabled: true,
      materialized_at: '2026-03-06T09:13:44.556193',
      source_state: {
        type: 'sql',
        data_source: 'arbodat_lookup',
      },
    }

    applyMaterializationRoundTripToFixedEntity(
      savePayload,
      [],
      '@load:materialized/feature_type.parquet',
      materializedConfig
    )

    expect(savePayload.values).toBe('@load:materialized/feature_type.parquet')
    expect(savePayload.materialized).toEqual(materializedConfig)
  })

  it('uses fixed values columns for external fixed-entity updates', () => {
    const result = getExternalValuesUpdateColumns(
      'fixed',
      ['description', 'feature_type_name', 'Befundtyp', 'Beschreibung'],
      ['system_id', 'feature_type_id', 'description', 'feature_type_name', 'Befundtyp', 'Beschreibung']
    )

    expect(result).toEqual(['system_id', 'feature_type_id', 'description', 'feature_type_name', 'Befundtyp', 'Beschreibung'])
  })

  it('uses form columns for non-fixed external updates', () => {
    const result = getExternalValuesUpdateColumns('sql', ['a', 'b'], ['system_id', 'x_id', 'a', 'b'])

    expect(result).toEqual(['a', 'b'])
  })

  it('strips only identity columns from editable fixed columns', () => {
    const result = normalizeEditableFixedColumns(
      [
        'system_id',
        'site_id',
        'Fustel',
        'EVNr',
        'site_type_id',
        'altitude',
        'coordinate_system',
        'latitude_dd',
        'longitude_dd',
        'national_site_identifier',
        'site_name',
        'FustelTyp',
      ],
      ['Fustel', 'EVNr'],
      'site_id'
    )

    expect(result).toEqual([
      'Fustel',
      'EVNr',
      'site_type_id',
      'altitude',
      'coordinate_system',
      'latitude_dd',
      'longitude_dd',
      'national_site_identifier',
      'site_name',
      'FustelTyp',
    ])
  })

  it('builds canonical fixed values column order', () => {
    const result = buildFixedValuesColumns(
      [
        'site_type_id',
        'altitude',
        'coordinate_system',
        'latitude_dd',
        'longitude_dd',
        'national_site_identifier',
        'site_name',
        'FustelTyp',
        'KoordSys',
      ],
      ['Fustel', 'EVNr'],
      'site_id'
    )

    expect(result).toEqual([
      'system_id',
      'site_id',
      'Fustel',
      'EVNr',
      'site_type_id',
      'altitude',
      'coordinate_system',
      'latitude_dd',
      'longitude_dd',
      'national_site_identifier',
      'site_name',
      'FustelTyp',
      'KoordSys',
    ])
  })

  it('expands legacy fixed rows to full grid columns using stored column names', () => {
    const result = normalizeFixedValuesRowsForForm(
      [
        [null, 'S1', 'Oak', 12, 'count'],
        [null, 'S2', 'Pine', 8, 'count'],
      ],
      ['abundance_id', 'sample_code', 'taxon_name', 'abundance', 'unit'],
      ['sample_code', 'taxon_name'],
      'abundance_id'
    )

    expect(result).toEqual([
      [1, null, 'S1', 'Oak', 12, 'count'],
      [2, null, 'S2', 'Pine', 8, 'count'],
    ])
  })

  it('keeps already-normalized fixed rows unchanged', () => {
    const rows = [
      [1, null, 'S1', 'Oak', 12, 'count'],
      [2, null, 'S2', 'Pine', 8, 'count'],
    ]

    const result = normalizeFixedValuesRowsForForm(
      rows,
      ['abundance_id', 'sample_code', 'taxon_name', 'abundance', 'unit'],
      ['sample_code', 'taxon_name'],
      'abundance_id'
    )

    expect(result).toEqual(rows)
  })

  it('remaps fixed rows by column name when schema changes', () => {
    const result = remapFixedValuesRowsToColumns(
      [
        [1, null, 'S1', 'Oak', 12, 'count'],
        [2, null, 'S2', 'Pine', 8, 'count'],
      ],
      ['system_id', 'abundance_id', 'sample_code', 'taxon_name', 'abundance', 'unit'],
      ['system_id', 'abundance_id', 'taxon_name', 'abundance', 'unit']
    )

    expect(result).toEqual([
      [1, null, 'Oak', 12, 'count'],
      [2, null, 'Pine', 8, 'count'],
    ])
  })
})
