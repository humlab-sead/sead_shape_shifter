import type { ValidationMetadataValue } from '@/types'

/**
 * Types for the read-only foreign-key integrity troubleshooter.
 *
 * These mirror the separate backend contract. They are intentionally kept apart
 * from the row-count trial types so an integrity inspection can never be sent
 * through, or rendered as, a join-key trial.
 */

export type IntegrityTroubleshootStatus = 'reproduced' | 'not_reproduced' | 'ineligible'
export type IntegritySelectionStatus = 'selected' | 'unavailable'

export interface IntegrityTroubleshootRequest {
  issue_type: string
  local_entity: string
  metadata: Record<string, ValidationMetadataValue>
  selected_value_token?: string | null
}

export interface IntegrityTroubleshootPageRequest {
  selected_value_token?: string | null
}

export interface IntegrityTroubleshootKeys {
  local_keys: string[]
  remote_keys: string[]
}

export interface IntegrityTroubleshootRelationship {
  local_entity: string
  remote_entity: string | null
  fk_index: number | null
  join_type: string | null
  constraints: Record<string, unknown>
}

export interface IntegrityTroubleshootValue {
  key_values: unknown[]
  local_row_count: number
  token: string
}

export interface IntegrityTroubleshootValuePage {
  distinct_value_count: number
  values: IntegrityTroubleshootValue[]
}

export interface IntegrityTroubleshootRows {
  status: IntegritySelectionStatus
  reason: string | null
  message: string | null
  key_values: unknown[] | null
  total_row_count: number | null
  columns: string[]
  columns_truncated: boolean
  rows: Record<string, unknown>[]
}

export interface IntegrityTroubleshootResponse {
  status: IntegrityTroubleshootStatus
  reason: string
  message: string
  source: string
  context_id: string | null
  expires_at: string | null
  relationship: IntegrityTroubleshootRelationship | null
  configured_keys: IntegrityTroubleshootKeys | null
  recorded_orphan_count: number | null
  current_orphan_count: number | null
  values: IntegrityTroubleshootValuePage | null
  selected: IntegrityTroubleshootRows | null
}
