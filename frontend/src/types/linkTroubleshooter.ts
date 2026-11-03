import type { ValidationError, ValidationMetadataValue } from '@/types'

export type LinkTroubleshootStatus = 'reproduced' | 'not_reproduced' | 'ineligible'
export type LinkTroubleshootTrialStatus = 'complete' | 'failed' | 'incomplete'
export type LinkTroubleshootDiagnosticStatus = 'complete' | 'failed' | 'incomplete' | 'not_run'
export type LinkTroubleshootRowFilter = 'all' | 'unmatched' | 'multiply_matched'

export interface LinkTroubleshootRequest {
  issue_type: string
  local_entity: string
  metadata: Record<string, ValidationMetadataValue>
  local_keys?: string[] | null
  remote_keys?: string[] | null
  page?: number
  page_size?: number
  row_filter?: LinkTroubleshootRowFilter
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

export interface LinkTroubleshootBaseline {
  input_a_rows: number | null
  output_rows: number | null
  unmatched_a_rows: number | null
  multiply_matched_a_rows: number | null
  diagnostic_status: LinkTroubleshootDiagnosticStatus
  diagnostic_reason: string | null
  diagnostic_message: string | null
  issues: ValidationError[]
}

export interface LinkTroubleshootRow {
  input_position: number
  key_values: unknown[]
  matched: boolean
  remote_match_count: number
  output_row_contribution: number
}

export interface LinkTroubleshootPagination {
  page: number
  page_size: number
  filtered_row_count: number
  returned_row_count: number
  has_next: boolean
}

export interface LinkTroubleshootTrial {
  status: LinkTroubleshootTrialStatus
  reason: string
  message: string
  local_keys: string[]
  remote_keys: string[]
  totals: LinkTroubleshootTotals | null
  issues: ValidationError[]
  rows: LinkTroubleshootRow[]
  pagination: LinkTroubleshootPagination | null
}

export interface LinkTroubleshootResponse {
  status: LinkTroubleshootStatus
  reason: string
  message: string
  relationship: LinkTroubleshootRelationship | null
  key_options: LinkTroubleshootKeyOptions | null
  configured_keys: LinkTroubleshootKeys | null
  baseline: LinkTroubleshootBaseline | null
  trial: LinkTroubleshootTrial | null
}
