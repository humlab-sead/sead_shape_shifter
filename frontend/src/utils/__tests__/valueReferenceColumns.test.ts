import { describe, expect, it } from 'vitest'
import type { EntityResponse } from '@/api/entities'
import { expandValueReference, getValueReferenceSuggestions } from '../valueReferenceColumns'

function makeEntity(name: string, entity_data: Record<string, unknown>): EntityResponse {
  return { name, entity_data, etag: `${name}-etag` }
}

describe('expandValueReference', () => {
  it('expands nested list references in order and retains duplicates', () => {
    const entities = [
      makeEntity('site', {
        keys: ['site_id', 'site_id'],
        columns: ['name', '@value: entities.site.keys'],
      }),
      makeEntity('sample', {
        keys: '@value: entities.site.columns',
        columns: ['sample_id', '@value: entities.sample.keys'],
      }),
    ]

    expect(expandValueReference('@value: entities.sample.columns', entities)).toEqual([
      'sample_id',
      'name',
      'site_id',
      'site_id',
    ])
  })

  it('expands supported scalar and mixed list values', () => {
    const entities = [
      makeEntity('site', { keys: ['site_id', 'name'] }),
      makeEntity('sample', {
        keys: '@value: entities.site.keys',
        columns: ['sample_id', '@value: entities.site.keys', '@value: entities.site.keys'],
      }),
    ]

    expect(expandValueReference('@value: entities.sample.keys', entities)).toEqual(['site_id', 'name'])
    expect(expandValueReference('@value: entities.sample.columns', entities)).toEqual([
      'sample_id',
      'site_id',
      'name',
      'site_id',
      'name',
    ])
  })

  it('returns an empty list for a supported empty reference target', () => {
    const entities = [makeEntity('site', { keys: [] })]

    expect(expandValueReference('@value: entities.site.keys', entities)).toEqual([])
  })

  it.each([
    ['missing cache', '@value: entities.site.keys', null],
    ['missing entity', '@value: entities.missing.keys', []],
    ['missing property', '@value: entities.site.columns', [makeEntity('site', { keys: ['site_id'] })]],
    ['cycle', '@value: entities.site.keys', [makeEntity('site', { keys: '@value: entities.site.keys' })]],
    ['null item', '@value: entities.site.keys', [makeEntity('site', { keys: ['site_id', null] })]],
    ['number item', '@value: entities.site.keys', [makeEntity('site', { keys: ['site_id', 3] })]],
    ['object item', '@value: entities.site.keys', [makeEntity('site', { keys: ['site_id', { value: 'other' }] })]],
    ['nested list', '@value: entities.site.keys', [makeEntity('site', { keys: ['site_id', ['nested']] })]],
    ['legacy concatenation', "@value: entities.site.keys + ['other']", [makeEntity('site', { keys: ['site_id'] })]],
    ['partial reference', '@value: entities.site.keys + other', [makeEntity('site', { keys: ['site_id'] })]],
    ['other directive', '@include: entities.site.keys', [makeEntity('site', { keys: ['site_id'] })]],
    [
      'unsupported nested directive',
      '@value: entities.site.keys',
      [makeEntity('site', { keys: ['@load:source.csv'] })],
    ],
  ])('returns no result for %s', (_caseName, reference, entities) => {
    expect(expandValueReference(reference, entities)).toBeNull()
  })

  it('does not mutate cached entity data', () => {
    const entities = [
      makeEntity('site', { keys: ['site_id'] }),
      makeEntity('sample', { columns: ['sample_id', '@value: entities.site.keys'] }),
    ]
    const original = JSON.stringify(entities)

    expect(expandValueReference('@value: entities.sample.columns', entities)).toEqual(['sample_id', 'site_id'])
    expect(JSON.stringify(entities)).toBe(original)
  })
})

describe('getValueReferenceSuggestions', () => {
  it('returns only complete supported keys and columns references in cache order', () => {
    const entities = [
      makeEntity('site', {
        keys: ['site_id'],
        columns: ['name', '@value: entities.site.keys'],
      }),
      makeEntity('sample', {
        keys: '@value: entities.site.columns',
        columns: [],
      }),
      makeEntity('broken', {
        keys: ['broken_id', ['nested']],
        columns: '@value: entities.missing.columns',
      }),
      makeEntity('cycle', {
        keys: '@value: entities.cycle.columns',
        columns: '@value: entities.cycle.keys',
      }),
      makeEntity('partial', {
        keys: "@value: entities.site.keys + ['other']",
      }),
    ]
    const original = JSON.stringify(entities)

    expect(getValueReferenceSuggestions(entities)).toEqual([
      '@value: entities.site.keys',
      '@value: entities.site.columns',
      '@value: entities.sample.keys',
      '@value: entities.sample.columns',
    ])
    expect(JSON.stringify(entities)).toBe(original)
  })

  it('returns no suggestions for an unavailable or empty cache', () => {
    expect(getValueReferenceSuggestions(null)).toEqual([])
    expect(getValueReferenceSuggestions([])).toEqual([])
  })
})
