import { describe, expect, it } from 'vitest'
import { isLinkTroubleshootCandidate, toLinkTroubleshootRequest } from '../linkTroubleshooter'
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
