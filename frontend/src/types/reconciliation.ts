/**
 * TypeScript types for entity reconciliation.
 */

export interface ReconciliationSource {
  data_source: string
  type: string
  query: string
}

export interface ReconciliationRemote {
  service_type?: string | null // e.g., 'site', 'taxon' - must match service defaultTypes
}

export interface ReconciliationMapping {
  source_values: any[]
  sead_id: number
  confidence?: number
  notes?: string
  created_at?: string
  created_by?: string
}

export interface EntityReconciliationSpec {
  source?: string | ReconciliationSource | null // Entity name, custom query, or null for default
  keys: string[] // Primary key fields for building query string
  property_mappings: Record<string, string> // property_id -> source_column
  remote: ReconciliationRemote
  auto_accept_threshold: number
  review_threshold: number
  mapping: ReconciliationMapping[]
}

export interface ReconciliationConfig {
  service_url: string
  entities: Record<string, EntityReconciliationSpec>
}

export interface ReconciliationCandidate {
  id: string
  name: string
  score?: number
  match?: boolean
  type: { id: string; name: string }[]
  description?: string
}

export interface AutoReconcileResult {
  auto_accepted: number
  needs_review: number
  unmatched: number
  total: number
  candidates: Record<string, ReconciliationCandidate[]>
}

export interface ReconciliationPreviewRow {
  [key: string]: any // Dynamic keys and columns
  sead_id?: number | null
  confidence?: number | null
  notes?: string
  candidates?: ReconciliationCandidate[]
  match_status?: 'auto-matched' | 'needs-review' | 'unmatched'
  will_not_match?: boolean
}
