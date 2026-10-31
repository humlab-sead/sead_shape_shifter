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
  local_key_value: string
  source_value: unknown
  status: ReconciliationDecisionStatus
  target_id: number | null
  candidate_id?: string | null
  confidence?: number | null
  notes?: string | null
  candidates: ReconciliationCandidate[]
  created_at?: string | null
  created_by?: string | null
  last_modified?: string | null
}

export type ReconciliationDecisionStatus = 'proposed' | 'accepted' | 'rejected' | 'local-only'

export interface DecisionUpdateRequest {
  local_key_value: string
  status: Exclude<ReconciliationDecisionStatus, 'proposed'>
  target_id?: number
  candidate_id?: string
  notes?: string
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
  version: '3.0'
  service_url: string
  entities: Record<string, Record<string, EntityResolutionSet>> // entity_name -> target_field -> spec
}

export interface ReconciliationCandidate {
  id: string
  name: string
  score?: number | null
  match?: boolean
  type: { id: string; name: string }[]
  description?: string
}

export interface AutoReconcileResult {
  proposed: number
  unmatched: number
  total: number
  candidates: Record<string, ReconciliationCandidate[]>
  errors: ReconciliationRowError[]
}

export interface ReconciliationRowError {
  row_index: number
  local_key_value?: string | null
  message: string
}

export interface ExportToMappingResult {
  exported: number
  removed: number
  skipped_manual: number
  entity: string
  field: string
  outcomes: ExportToMappingOutcome[]
}

export interface ExportToMappingOutcome {
  local_key_value: string
  outcome: 'verified' | 'not_found' | 'invalid_candidate' | 'unverified'
  reason?: string | null
}

export interface DeleteSpecificationResult extends EntityResolutionCatalog {
  removed_owned_links: number
}

export interface ReconciliationPreviewRow {
  [key: string]: unknown // Dynamic entity columns
  local_key_value?: string | null
  status?: ReconciliationDecisionStatus | null
  target_id?: number | null
  candidate_id?: string | null
  confidence?: number | null
  notes?: string | null
  candidates?: ReconciliationCandidate[]
  errors?: string[]
}

export interface MappingLink {
  target_id: number | null
  source: 'manual' | 'reconciliation' | 'import'
  confidence?: number | null
  created_at: string
  committed_at?: string | null
  owner?: MappingLinkOwner | null
  verified_at?: string | null
  notes?: string | null
  created_by: string
  reviewed_by?: string | null
}

export interface MappingLinkOwner {
  entity_name: string
  target_field: string
}

export interface MappingEntityResponse {
  entity_name: string
  local_key: string | string[]
  public_id: string
  entity_type: string
  description?: string | null
  links: Record<string, MappingLink>
}

export interface MappingLinkRecordResponse {
  entity_name: string
  local_key_value: string
  local_key: string | string[]
  public_id: string
  link: MappingLink
}

export interface MappingLinkUpsertRequest {
  target_id: number
  notes?: string
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
