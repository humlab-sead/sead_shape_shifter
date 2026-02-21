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

export interface ResolvedEntityPair {
  source_value: any // Single value instead of array
  target_id: number
  confidence?: number
  notes?: string
  created_at?: string
  created_by?: string
  will_not_match?: boolean
}

export interface EntityResolutionSet {
  source?: string | ReconciliationSource | null // Entity name, custom query, or null for default
  property_mappings: Record<string, string> // property_id -> source_column
  remote: ReconciliationRemote
  auto_accept_threshold: number
  review_threshold: number
  mapping: ResolvedEntityPair[]
}

export interface EntityResolutionCatalog {
  version: string // Format version (e.g., "2.0")
  service_url: string
  entities: Record<string, Record<string, EntityResolutionSet>> // entity_name -> target_field -> spec
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
  target_id?: number | null
  confidence?: number | null
  notes?: string
  candidates?: ReconciliationCandidate[]
  match_status?: 'auto-matched' | 'needs-review' | 'unmatched'
  will_not_match?: boolean
}

// Specification management types

export interface EntityResolutionListItem {
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

export interface EntityResolutionCatalogCreateRequest {
  entity_name: string
  target_field: string
  spec: EntityResolutionSet
}

export interface EntityResolutionCatalogUpdateRequest {
  source?: string | ReconciliationSource | null
  property_mappings: Record<string, string>
  remote: ReconciliationRemote
  auto_accept_threshold: number
  review_threshold: number
}
