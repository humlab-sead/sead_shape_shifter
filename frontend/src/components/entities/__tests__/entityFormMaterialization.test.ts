import { describe, expect, it } from 'vitest'

import {
  applyMaterializationRoundTripToFixedEntity,
  extractMaterializationRoundTripState,
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
})
