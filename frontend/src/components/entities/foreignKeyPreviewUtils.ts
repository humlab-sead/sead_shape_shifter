import type { ForeignKeyConfig } from '@/types'

import { normalizeForeignKeyKeys } from './foreignKeyEditorUtils'

export interface KeyPairRow {
  index: number
  local: string
  remote: string
}

export function getKeyPairRows(fk: Pick<ForeignKeyConfig, 'local_keys' | 'remote_keys'>): KeyPairRow[] {
  const localKeys = normalizeForeignKeyKeys(fk.local_keys)
  const remoteKeys = normalizeForeignKeyKeys(fk.remote_keys)
  const pairCount = Math.max(localKeys.length, remoteKeys.length)

  return Array.from({ length: pairCount }, (_, index) => ({
    index: index + 1,
    local: localKeys[index] || '',
    remote: remoteKeys[index] || '',
  }))
}

export function hasKeyCountMismatch(fk: Pick<ForeignKeyConfig, 'local_keys' | 'remote_keys'>): boolean {
  const localKeys = normalizeForeignKeyKeys(fk.local_keys)
  const remoteKeys = normalizeForeignKeyKeys(fk.remote_keys)
  return localKeys.length !== remoteKeys.length
}

export function hasSuspiciousKeyReorder(fk: Pick<ForeignKeyConfig, 'local_keys' | 'remote_keys'>): boolean {
  const localKeys = normalizeForeignKeyKeys(fk.local_keys)
  const remoteKeys = normalizeForeignKeyKeys(fk.remote_keys)

  if (localKeys.length < 2 || localKeys.length !== remoteKeys.length) {
    return false
  }

  const sortedLocal = [...localKeys].sort()
  const sortedRemote = [...remoteKeys].sort()

  return sortedLocal.every((key, index) => key === sortedRemote[index]) && localKeys.some((key, index) => key !== remoteKeys[index])
}

export function buildForeignKeySummary(fk: Pick<ForeignKeyConfig, 'local_keys' | 'remote_keys'>, entity: string): string {
  const pairs = getKeyPairRows(fk)

  if (pairs.length === 0) {
    return `${entity}: ?`
  }

  const summary = pairs
    .slice(0, 2)
    .map((pair) => `${pair.index}:${pair.local || '?'}→${pair.remote || '?'}`)
    .join(', ')

  const overflow = pairs.length > 2 ? ` +${pairs.length - 2} more` : ''
  return `${entity}: ${summary}${overflow}`
}