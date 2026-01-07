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
  columns?: string[] // Additional columns for display/matching
}

export interface ReconciliationMapping {
  source_value: any // Single value instead of array
  sead_id: number
  confidence?: number
  notes?: string
  created_at?: string
  created_by?: string
  will_not_match?: boolean
}

export interface EntityReconciliationSpec {
  source?: string | ReconciliationSource | null // Entity name, custom query, or null for default
  property_mappings: Record<string, string> // property_id -> source_column
  remote: ReconciliationRemote
  auto_accept_threshold: number
  review_threshold: number
  mapping: ReconciliationMapping[]
}

export interface ReconciliationConfig {
  version: string // Format version (e.g., "2.0")
  service_url: string
  entities: Record<string, Record<string, EntityReconciliationSpec>> // entity_name -> target_field -> spec
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

// Specification management types

export interface SpecificationListItem {
  entity_name: string
  target_field: string
  source?: string | ReconciliationSource | null
  property_mappings: Record<string, string>
  remote: ReconciliationRemote
  auto_accept_threshold: number
  review_threshold: number
  mapping_count: number
  property_mapping_count: number
}

export interface SpecificationCreateRequest {
  entity_name: string
  target_field: string
  spec: EntityReconciliationSpec
}

export interface SpecificationUpdateRequest {
  source?: string | ReconciliationSource | null
  property_mappings: Record<string, string>
  remote: ReconciliationRemote
  auto_accept_threshold: number
  review_threshold: number
}
