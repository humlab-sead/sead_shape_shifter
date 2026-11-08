import { describe, expect, it } from 'vitest'
import {
  integrityTroubleshootRefusal,
  isIntegrityTroubleshootCandidate,
  isLinkTroubleshootCandidate,
  isSampleDataValidation,
  sampleDataTroubleshootRefusal,
  SAMPLE_DATA_TROUBLESHOOT_REFUSAL,
  toIntegrityTroubleshootRequest,
  toLinkTroubleshootRequest,
} from '../linkTroubleshooter'
import type { ValidationError } from '@/types'

function warning(overrides: Partial<ValidationError> = {}): ValidationError {
  return {
    severity: 'warning',
    entity: 'orders',
    message: 'The link changed the row count.',
    code: 'ROW_COUNT_MISMATCH',
    metadata: {
      fk_index: 0,
      fk_signature: 'saved-signature',
      link_pass: 'initial',
      join_type: 'inner',
    },
    ...overrides,
  }
}

describe('link troubleshooter warning helper', () => {
  it.each(['inner', 'left'] as const)('accepts a supported %s warning', (joinType) => {
    expect(isLinkTroubleshootCandidate(warning({ metadata: { ...warning().metadata, join_type: joinType } }))).toBe(
      true
    )
  })

  it('rejects a warning without a foreign-key index', () => {
    const metadata = { ...(warning().metadata ?? {}) }
    delete metadata.fk_index
    expect(isLinkTroubleshootCandidate(warning({ metadata }))).toBe(false)
  })

  it('rejects a warning without a foreign-key signature', () => {
    const metadata = { ...(warning().metadata ?? {}) }
    delete metadata.fk_signature
    expect(isLinkTroubleshootCandidate(warning({ metadata }))).toBe(false)
  })

  it('rejects a warning with an unsupported join type', () => {
    expect(isLinkTroubleshootCandidate(warning({ metadata: { ...warning().metadata, join_type: 'right' } }))).toBe(
      false
    )
  })

  it('rejects a non-row-count issue and a null entity', () => {
    expect(isLinkTroubleshootCandidate(warning({ code: 'OTHER_WARNING' }))).toBe(false)
    expect(isLinkTroubleshootCandidate(warning({ entity: null }))).toBe(false)
  })

  it('builds a request without changing the warning', () => {
    const message = warning()
    const before = structuredClone(message)

    expect(toLinkTroubleshootRequest(message)).toEqual({
      issue_type: 'row_count_mismatch',
      local_entity: 'orders',
      metadata: message.metadata,
    })
    expect(message).toEqual(before)
  })
})

describe('sample data gate', () => {
  it.each(['sample'] as const)('treats %s results as sample data', (mode) => {
    expect(isSampleDataValidation(mode)).toBe(true)
  })

  it.each(['complete', 'single_pass', null, undefined] as const)('leaves %s results alone', (mode) => {
    expect(isSampleDataValidation(mode)).toBe(false)
  })

  it.each([
    ['row count', () => warning()],
    ['integrity', () => integrityWarning()],
  ])('refuses the %s warning for sample results', (_label, makeWarning) => {
    expect(sampleDataTroubleshootRefusal(makeWarning(), 'sample')).toBe(SAMPLE_DATA_TROUBLESHOOT_REFUSAL)
  })

  it.each(['complete', 'single_pass', null] as const)('allows the warning for %s results', (mode) => {
    expect(sampleDataTroubleshootRefusal(warning(), mode)).toBeNull()
    expect(sampleDataTroubleshootRefusal(integrityWarning(), mode)).toBeNull()
  })

  it('leaves an unrelated warning without a sample refusal', () => {
    expect(sampleDataTroubleshootRefusal(warning({ code: 'OTHER_WARNING' }), 'sample')).toBeNull()
  })
})

function integrityWarning(overrides: Partial<ValidationError> = {}): ValidationError {
  return {
    severity: 'warning',
    entity: 'orders',
    message: "2 foreign key value(s) not found in 'customers'",
    code: 'FK_DATA_INTEGRITY',
    metadata: {
      fk_index: 1,
      fk_signature: 'saved-signature',
      orphan_count: 2,
    },
    ...overrides,
  }
}

describe('integrity troubleshooter warning helper', () => {
  it.each(['inner', 'left', 'right', 'outer', null])('accepts a configured link with join type %s', (joinType) => {
    const metadata = { ...(integrityWarning().metadata ?? {}), join_type: joinType, link_pass: 'initial' }
    expect(isIntegrityTroubleshootCandidate(integrityWarning({ metadata }))).toBe(true)
  })

  it('accepts a duplicate remote entity because the index addresses the configured link', () => {
    const first = integrityWarning({ metadata: { fk_index: 0, fk_signature: 'first', remote_entity: 'customers' } })
    const second = integrityWarning({ metadata: { fk_index: 1, fk_signature: 'second', remote_entity: 'customers' } })

    expect(isIntegrityTroubleshootCandidate(first)).toBe(true)
    expect(isIntegrityTroubleshootCandidate(second)).toBe(true)
  })

  it.each(['0', 1.5, -1, null])('rejects a warning with fk_index %s', (fkIndex) => {
    const metadata = { ...(integrityWarning().metadata ?? {}), fk_index: fkIndex }
    expect(isIntegrityTroubleshootCandidate(integrityWarning({ metadata }))).toBe(false)
  })

  it('rejects a warning without a foreign-key index', () => {
    const metadata = { ...(integrityWarning().metadata ?? {}) }
    delete metadata.fk_index
    expect(isIntegrityTroubleshootCandidate(integrityWarning({ metadata }))).toBe(false)
  })

  it.each([1, null])('rejects a warning with a non-string fk_signature %s', (signature) => {
    const metadata = { ...(integrityWarning().metadata ?? {}), fk_signature: signature }
    expect(isIntegrityTroubleshootCandidate(integrityWarning({ metadata }))).toBe(false)
  })

  it('rejects a warning without a foreign-key signature', () => {
    const metadata = { ...(integrityWarning().metadata ?? {}) }
    delete metadata.fk_signature
    expect(isIntegrityTroubleshootCandidate(integrityWarning({ metadata }))).toBe(false)
  })

  it('rejects a warning without an entity', () => {
    expect(isIntegrityTroubleshootCandidate(integrityWarning({ entity: null }))).toBe(false)
    expect(isIntegrityTroubleshootCandidate(integrityWarning({ entity: '   ' }))).toBe(false)
  })

  it('rejects another warning code and does not make it a row-count candidate', () => {
    expect(isIntegrityTroubleshootCandidate(integrityWarning({ code: 'ROW_COUNT_MISMATCH' }))).toBe(false)
    expect(isIntegrityTroubleshootCandidate(integrityWarning({ code: 'OTHER_WARNING' }))).toBe(false)
  })

  it('builds a request without changing the warning metadata', () => {
    const message = integrityWarning()
    const before = structuredClone(message)

    expect(toIntegrityTroubleshootRequest(message)).toEqual({
      issue_type: 'FK_DATA_INTEGRITY',
      local_entity: 'orders',
      metadata: message.metadata,
    })
    expect(message).toEqual(before)
    expect(toIntegrityTroubleshootRequest(integrityWarning({ entity: null }))).toBeNull()
  })

  it('explains a locally unusable integrity warning', () => {
    const noEntity = integrityWarning({ entity: null })
    const noIndex = integrityWarning({ metadata: { fk_signature: 'saved-signature' } })
    const noSignature = integrityWarning({ metadata: { fk_index: 0 } })

    expect(integrityTroubleshootRefusal(integrityWarning())).toBeNull()
    expect(integrityTroubleshootRefusal(warning())).toBeNull()
    expect(integrityTroubleshootRefusal(noEntity)).toContain('does not identify which entity')
    expect(integrityTroubleshootRefusal(noIndex)).toContain('does not record which configured link')
    expect(integrityTroubleshootRefusal(noSignature)).toContain('does not record a configured-link signature')
  })
})
