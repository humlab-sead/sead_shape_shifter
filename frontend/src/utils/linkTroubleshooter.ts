import type { LinkTroubleshootRequest, ValidationError } from '@/types'

const supportedLinkPasses = ['initial', 'after_unnest', 'deferred_retry'] as const
const supportedJoinTypes = ['inner', 'left'] as const

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
