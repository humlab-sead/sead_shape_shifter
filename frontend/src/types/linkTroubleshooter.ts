import type { ValidationError, ValidationMetadataValue } from '@/types'

export type LinkTroubleshootStatus = 'reproduced' | 'not_reproduced' | 'ineligible'
export type LinkTroubleshootTrialStatus = 'complete' | 'failed' | 'incomplete'
export type LinkTroubleshootDiagnosticStatus = 'complete' | 'failed' | 'incomplete' | 'not_run'
export type LinkTroubleshootSettingSource = 'inherited' | 'explicit'
export type LinkTroubleshootJoinType = 'inner' | 'left'

export interface LinkExperimentContextRequest {
  issue_type: string
  local_entity: string
  metadata: Record<string, ValidationMetadataValue>
}

export interface LinkExperimentTrialRequest {
  local_keys: string[]
  remote_keys: string[]
  how?: LinkTroubleshootJoinType | null
  allow_null_keys?: boolean | null
  null_keys_equal?: boolean | null
}

export interface LinkTroubleshootKeys {
  local_keys: string[]
  remote_keys: string[]
}

export interface LinkTroubleshootRelationship {
  local_entity: string
  remote_entity: string | null
  fk_index: number | null
  join_type: string | null
  link_pass: string | null
  constraints: Record<string, unknown>
}

export interface LinkTroubleshootKeyOptions {
  local: string[]
  remote: string[]
}

export interface LinkTroubleshootTotals {
  input_a_rows: number
  output_rows: number
  unmatched_a_rows: number
  multiply_matched_a_rows: number
}

export interface LinkTroubleshootJoinTypeSetting {
  requested: LinkTroubleshootJoinType | null
  source: LinkTroubleshootSettingSource
  effective: LinkTroubleshootJoinType
}

export interface LinkTroubleshootRequestedSetting {
  requested: boolean | null
  source: LinkTroubleshootSettingSource
}

export interface LinkTroubleshootResolvedNullPolicy {
  enforce_strict_null_keys: boolean
  prevent_null_key_matches: boolean
}

export interface LinkTroubleshootTrialSettings {
  join_type: LinkTroubleshootJoinTypeSetting
  allow_null_keys: LinkTroubleshootRequestedSetting
  null_keys_equal: LinkTroubleshootRequestedSetting
  resolved_null_policy: LinkTroubleshootResolvedNullPolicy
}

export interface LinkTroubleshootKeyValue {
  value: unknown
  truncated: boolean
  original_length: number | null
}

export interface LinkTroubleshootExceptionRow {
  input_position: number
  key_values: LinkTroubleshootKeyValue[]
  remote_match_count: number
  output_row_contribution: number
}

export interface LinkTroubleshootExceptionGroup {
  total_count: number
  returned_count: number
  row_cap: number
  row_cap_reached: boolean
  budget_exhausted: boolean
  rows: LinkTroubleshootExceptionRow[]
}

export interface LinkTroubleshootFindings {
  total_count: number
  returned_count: number
  truncated: boolean
  issues: ValidationError[]
}

export interface LinkTroubleshootDetail {
  detail_truncated: boolean
  findings: LinkTroubleshootFindings
  unmatched: LinkTroubleshootExceptionGroup | null
  multiply_matched: LinkTroubleshootExceptionGroup | null
}

export interface LinkTroubleshootBaseline {
  input_a_rows: number | null
  output_rows: number | null
  unmatched_a_rows: number | null
  multiply_matched_a_rows: number | null
  diagnostic_status: LinkTroubleshootDiagnosticStatus
  diagnostic_reason: string | null
  diagnostic_message: string | null
  issues: ValidationError[]
  settings: LinkTroubleshootTrialSettings | null
  detail: LinkTroubleshootDetail | null
}

export interface LinkTroubleshootComparison {
  status: LinkTroubleshootTrialStatus
  reason: string
  message: string
  settings: LinkTroubleshootTrialSettings | null
  totals: LinkTroubleshootTotals | null
  detail: LinkTroubleshootDetail | null
}

export interface LinkExperimentContextResponse {
  context_id: string | null
  status: LinkTroubleshootStatus
  reason: string
  message: string
  expires_at: string | null
  relationship: LinkTroubleshootRelationship | null
  key_options: LinkTroubleshootKeyOptions | null
  configured_keys: LinkTroubleshootKeys | null
  baseline: LinkTroubleshootBaseline | null
}

export interface LinkExperimentTrialResponse {
  context_id: string
  expires_at: string
  local_keys: string[]
  remote_keys: string[]
  baseline: LinkTroubleshootBaseline | null
  trial: LinkTroubleshootComparison
}
