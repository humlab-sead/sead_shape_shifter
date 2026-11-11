import { describe, expect, it } from 'vitest'

import { getReconciliationCompatibility, parseReconciliationManifest } from '../reconciliationManifest'

const validManifest = {
  defaultTypes: [
    { id: 'site', name: 'Site' },
    { id: 'feature_type', name: 'Feature type' },
    { id: 'taxon', name: 'Taxon' },
  ],
  reconciliation: { supportedTypes: ['site', 'feature_type'] },
  extend: {
    property_settings: [
      { name: 'place_name', entity_types: ['site'] },
      { name: 'latitude', entity_types: ['site', 'site_archive'] },
    ],
  },
}

describe('parseReconciliationManifest', () => {
  it('uses only supported IDs and exact property type membership', () => {
    const result = parseReconciliationManifest(validManifest)

    expect(result).toEqual({
      status: 'valid',
      manifest: {
        supportedTypes: [
          { id: 'site', name: 'Site' },
          { id: 'feature_type', name: 'Feature type' },
        ],
        propertiesByType: {
          site: ['place_name', 'latitude'],
          feature_type: [],
        },
      },
    })
  })

  it('uses the type ID when an optional display name is absent or blank', () => {
    const result = parseReconciliationManifest({
      ...validManifest,
      defaultTypes: [{ id: 'site', name: ' ' }, { id: 'feature_type' }, { id: 'taxon' }],
    })

    expect(result.status).toBe('valid')
    if (result.status === 'valid') {
      expect(result.manifest.supportedTypes[0]).toEqual({ id: 'site', name: 'site' })
    }
  })

  it('accepts an empty supported list', () => {
    const result = parseReconciliationManifest({
      ...validManifest,
      reconciliation: { supportedTypes: [] },
    })

    expect(result).toEqual({
      status: 'valid',
      manifest: { supportedTypes: [], propertiesByType: {} },
    })
  })

  it.each([
    ['missing defaultTypes', { ...validManifest, defaultTypes: undefined }],
    ['duplicate default type IDs', { ...validManifest, defaultTypes: [...validManifest.defaultTypes, { id: 'site' }] }],
    ['blank supported type ID', { ...validManifest, reconciliation: { supportedTypes: [' '] } }],
    ['duplicate supported type IDs', { ...validManifest, reconciliation: { supportedTypes: ['site', 'site'] } }],
    ['unsupported type absent from defaultTypes', { ...validManifest, reconciliation: { supportedTypes: ['other'] } }],
    ['missing supportedTypes', { ...validManifest, reconciliation: {} }],
    ['missing property settings', { ...validManifest, extend: {} }],
    [
      'malformed property setting',
      { ...validManifest, extend: { property_settings: [{ name: 'place_name', entity_types: 'site' }] } },
    ],
    [
      'blank property type ID',
      { ...validManifest, extend: { property_settings: [{ name: 'place_name', entity_types: [' '] }] } },
    ],
  ])('rejects %s', (_description, value) => {
    expect(parseReconciliationManifest(value).status).toBe('error')
  })
})

describe('getReconciliationCompatibility', () => {
  const parsedManifest = parseReconciliationManifest(validManifest)

  it('allows supported types with no properties when no mappings are saved', () => {
    expect(getReconciliationCompatibility(parsedManifest, 'feature_type', {})).toEqual({
      status: 'supported',
      canMatch: true,
      message: null,
    })
  })

  it('blocks unsupported types, unsupported properties, and unknown metadata', () => {
    expect(getReconciliationCompatibility(parsedManifest, 'taxon', {})).toMatchObject({
      status: 'unsupported',
      canMatch: false,
    })
    expect(getReconciliationCompatibility(parsedManifest, 'site', { old_name: 'site_name' })).toMatchObject({
      status: 'unsupported',
      canMatch: false,
    })
    expect(getReconciliationCompatibility({ status: 'error', error: 'Manifest unavailable.' }, 'site', {})).toEqual({
      status: 'unknown',
      canMatch: false,
      message: 'Manifest unavailable.',
    })
  })
})
