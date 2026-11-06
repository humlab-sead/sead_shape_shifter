import type { DataValidationMode, IntegrityTroubleshootRequest, LinkTroubleshootRequest, ValidationError } from '@/types'

const supportedLinkPasses = ['initial', 'after_unnest', 'deferred_retry'] as const
const supportedJoinTypes = ['inner', 'left'] as const

export const INTEGRITY_ISSUE_CODE = 'FK_DATA_INTEGRITY'

export const SAMPLE_DATA_TROUBLESHOOT_REFUSAL =
  'Link troubleshooting is turned off for sample data validation results. The troubleshooter replays the saved link on complete data, so it cannot confirm a warning raised from a sample of at most 1000 rows per entity. Run complete data validation to troubleshoot this link.'

export function isLinkTroubleshootCandidate(message: ValidationError): boolean {
  const metadata = message.metadata
  const linkPass = metadata?.link_pass
  const joinType = metadata?.join_type
  return (
    message.code === 'ROW_COUNT_MISMATCH' &&
    typeof message.entity === 'string' &&
    message.entity.trim().length > 0 &&
    typeof metadata?.fk_index === 'number' &&
    typeof metadata.fk_signature === 'string' &&
    typeof linkPass === 'string' &&
    (linkPass === supportedLinkPasses[0] ||
      linkPass === supportedLinkPasses[1] ||
      linkPass === supportedLinkPasses[2]) &&
    typeof joinType === 'string' &&
    (joinType === supportedJoinTypes[0] || joinType === supportedJoinTypes[1])
  )
}

export function toLinkTroubleshootRequest(message: ValidationError): LinkTroubleshootRequest | null {
  if (!isLinkTroubleshootCandidate(message) || !message.entity) {
    return null
  }

  return {
    issue_type: 'row_count_mismatch',
    local_entity: message.entity,
    metadata: message.metadata ?? {},
  }
}

/**
 * Check whether an integrity warning carries the local identity needed to
 * address one saved link.
 *
 * This is a structural check only. It does not decide whether the saved link
 * still exists or still matches its recorded signature; only the backend can
 * establish that, so a candidate can still be refused as ineligible.
 */
export function isIntegrityTroubleshootCandidate(message: ValidationError): boolean {
  const metadata = message.metadata
  return (
    message.code === INTEGRITY_ISSUE_CODE &&
    typeof message.entity === 'string' &&
    message.entity.trim().length > 0 &&
    typeof metadata?.fk_index === 'number' &&
    Number.isInteger(metadata.fk_index) &&
    metadata.fk_index >= 0 &&
    typeof metadata.fk_signature === 'string'
  )
}

/**
 * Build the opening integrity inspection request for a candidate warning.
 *
 * The warning metadata is forwarded unchanged; no join pass or join type is
 * required because every saved link can be inspected for unmatched values.
 */
export function toIntegrityTroubleshootRequest(message: ValidationError): IntegrityTroubleshootRequest | null {
  if (!isIntegrityTroubleshootCandidate(message) || !message.entity) {
    return null
  }

  return {
    issue_type: INTEGRITY_ISSUE_CODE,
    local_entity: message.entity,
    metadata: message.metadata ?? {},
  }
}

/**
 * Check whether a validation result was produced from truncated sample data.
 *
 * Sample runs read at most 1000 rows per entity, so a missing parent value or a
 * changed row count can come from the truncation rather than from the data.
 */
export function isSampleDataValidation(validationMode: DataValidationMode | null | undefined): boolean {
  return validationMode === 'sample'
}

/**
 * Explain why a sample-data result offers no troubleshooting action.
 *
 * Returns null for other validation modes and for warnings that could not be
 * troubleshot on complete data either.
 */
export function sampleDataTroubleshootRefusal(
  message: ValidationError,
  validationMode: DataValidationMode | null | undefined
): string | null {
  if (!isSampleDataValidation(validationMode)) {
    return null
  }

  if (!isLinkTroubleshootCandidate(message) && !isIntegrityTroubleshootCandidate(message)) {
    return null
  }

  return SAMPLE_DATA_TROUBLESHOOT_REFUSAL
}

/**
 * Explain why an integrity warning offers no inspection action.
 *
 * Returns null for other warning codes and for usable integrity warnings.
 */
export function integrityTroubleshootRefusal(message: ValidationError): string | null {
  if (message.code !== INTEGRITY_ISSUE_CODE || isIntegrityTroubleshootCandidate(message)) {
    return null
  }

  if (typeof message.entity !== 'string' || message.entity.trim().length === 0) {
    return 'This warning does not name the entity that owns the saved link, so no saved link can be inspected.'
  }

  const metadata = message.metadata
  const fkIndex = metadata?.fk_index
  if (typeof fkIndex !== 'number' || !Number.isInteger(fkIndex) || fkIndex < 0) {
    return 'This warning does not record which saved link raised it, so there is no link to inspect.'
  }

  if (typeof metadata?.fk_signature !== 'string') {
    return 'This warning does not record a saved-link signature, so an edited or removed link cannot be ruled out.'
  }

  return 'This warning cannot be inspected.'
}
