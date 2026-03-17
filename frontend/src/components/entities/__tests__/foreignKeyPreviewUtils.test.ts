import { describe, expect, it } from 'vitest'

import {
  buildForeignKeySummary,
  getKeyPairRows,
  hasKeyCountMismatch,
  hasSuspiciousKeyReorder,
} from '../foreignKeyPreviewUtils'

describe('foreignKeyPreviewUtils', () => {
  it('builds numbered key pair rows', () => {
    expect(
      getKeyPairRows({
        local_keys: ['Fustel', 'EVNr'],
        remote_keys: ['Fustel', 'EVNr'],
      } as any)
    ).toEqual([
      { index: 1, local: 'Fustel', remote: 'Fustel' },
      { index: 2, local: 'EVNr', remote: 'EVNr' },
    ])
  })

  it('detects suspicious reordering of the same key names', () => {
    expect(
      hasSuspiciousKeyReorder({
        local_keys: ['Fustel', 'EVNr'],
        remote_keys: ['EVNr', 'Fustel'],
      } as any)
    ).toBe(true)
  })

  it('detects key count mismatches and exposes missing pair slots', () => {
    expect(
      hasKeyCountMismatch({
        local_keys: ['location_type', 'location_name'],
        remote_keys: ['location_type'],
      } as any)
    ).toBe(true)

    expect(
      getKeyPairRows({
        local_keys: ['location_type', 'location_name'],
        remote_keys: ['location_type'],
      } as any)
    ).toEqual([
      { index: 1, local: 'location_type', remote: 'location_type' },
      { index: 2, local: 'location_name', remote: '' },
    ])
  })

  it('builds a compact numbered summary for the expansion panel title', () => {
    expect(
      buildForeignKeySummary(
        {
          local_keys: ['Fustel', 'EVNr', 'site_name'],
          remote_keys: ['Fustel', 'EVNr', 'site_name'],
        } as any,
        'site'
      )
    ).toBe('site: 1:Fustel→Fustel, 2:EVNr→EVNr +1 more')
  })
})