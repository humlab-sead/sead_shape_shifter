/**
 * TypeScript types for entity reconciliation.
 */

export interface ReconciliationSource {
  data_source: string
  type: string
  query: string
}

export interface ReconciliationTypeOption {
  id: string
  name: string
  disabled?: boolean
}

export interface ReconciliationManifest {
  supportedTypes: ReconciliationTypeOption[]
  propertiesByType: Record<string, string[]>
  /** Versioned record-selection extension; null when the service does not publish a valid one. */
  selection: ReconciliationSelectionDescriptor | null
}

/**
 * Same-service record-selection discovery metadata advertised by the Authority Service.
 */
export interface ReconciliationSelectionDescriptor {
  version: number
  typesPath: string
}

export type ReconciliationManifestResult =
  | { status: 'valid'; manifest: ReconciliationManifest }
  | { status: 'error'; error: string }

export interface ReconciliationCompatibility {
  status: 'supported' | 'unsupported' | 'unknown' | 'disabled'
  canMatch: boolean
  message: string | null
}

export interface ReconciliationRemote {
  service_type?: string | null // Must match reconciliation.supportedTypes
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
  exported_local_only_approvals: number
  removed_local_only_approvals: number
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
  removed_owned_approvals: number
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
  protected?: boolean | null
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
  local_only_approvals?: Record<string, MappingLocalOnlyApproval>
  protection_target_field?: string | null
}

export interface MappingLocalOnlyApproval {
  owner: MappingLinkOwner
  committed_at?: string | null
  protected?: boolean | null
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

export interface MappingEntryDeleteResponse {
  entity_name: string
  local_key_value: string
  deleted_link: boolean
  deleted_local_only_approval: boolean
}

// Specification management types

export interface EntityResolutionListItem {
  entity_name: string
  has_business_keys: boolean
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

// Record selection types: capabilities, search, browse, and workspace drafts.

export interface SelectionDisplayField {
  name: string
  source: 'record' | 'fields'
  label: string
  value_type: 'string' | 'integer' | 'number' | 'boolean'
  display: boolean
}

export interface SelectionFieldFilter {
  field: string
  operator: 'contains_ci' | 'equals'
}

/** Independent capability flags and limits advertised for one record type. */
export interface SelectionTypeCapabilities {
  type: string
  search_supported: boolean
  identifier_search_supported: boolean
  browse_supported: boolean
  details_supported: boolean
  export_verification_supported: boolean
  id_base: string | null
  id_path: string
  browse_max_rows: number | null
  browse_max_bytes: number | null
  interactive_search_max_results: number | null
  display_fields: SelectionDisplayField[]
  text_filter_fields: string[]
  sort_fields: string[]
  field_filters: SelectionFieldFilter[]
}

/** Versioned capabilities for the specification's own record type. */
export interface SelectionCapabilities {
  version: number
  type: SelectionTypeCapabilities
}

/** One selectable target record shared by ranked search and browse. */
export interface SelectionRecord {
  id: string
  target_id: number | null
  type: string
  name: string
  description?: string | null
  fields: Record<string, unknown>
  /** Ranked search score in the OpenRefine 0-100 scale; null for browse records. */
  score?: number | null
}

export interface SelectionSearchRequest {
  query: string
  limit?: number
  context?: Record<string, string>
}

export interface SelectionSearchResult {
  mode: 'ranked' | 'exact'
  items: SelectionRecord[]
}

export interface SelectionBrowseResult {
  items: SelectionRecord[]
  completeness: 'complete'
}

export type SelectionMode = 'search' | 'browse'

/** A decision staged in the browser but not yet saved. */
export type StagedDecision =
  | { status: 'accepted'; id: string; target_id: number; name: string }
  | { status: 'local-only' }

export interface DecisionDraftRequest {
  local_key_value: string
  displayed_values: Record<string, unknown>
  status: 'accepted' | 'local-only'
  target_id?: number | null
  candidate_id?: string | null
  notes?: string | null
}

export interface DecisionBatchRequest {
  drafts: DecisionDraftRequest[]
}

export interface SavedDecision {
  local_key_value: string
  status: 'accepted' | 'local-only'
  target_id?: number | null
  candidate_id?: string | null
  notes?: string | null
  last_modified?: string | null
}

export interface SpecificationDecisionCounts {
  accepted: number
  local_only: number
  proposed: number
  rejected: number
  total: number
}

export interface DecisionBatchCounts {
  saved: number
  accepted: number
  local_only: number
  specification: SpecificationDecisionCounts
}

export interface DecisionBatchResult {
  saved: SavedDecision[]
  counts: DecisionBatchCounts
}

export interface DecisionBatchIssue {
  row_index?: number | null
  local_key_value?: string | null
  field?: string | null
  code: string
  message: string
}

/** Saved decision state used for the advisory stale-view comparison. */
export interface DecisionState {
  status: ReconciliationDecisionStatus | null
  target_id: number | null
  candidate_id: string | null
  notes: string | null
}

/** One row's unsaved workspace state. */
export interface WorkspaceRowDraft {
  query: string
  notes: string
  decision: StagedDecision | null
  displayedValues: Record<string, unknown>
}

/** Scoped, versioned browser draft for one specification. */
export interface WorkspaceDraft {
  focusedKey: string | null
  mode: SelectionMode
  searchQuery: string
  browseText: string
  browseFieldFilters: Record<string, string>
  sortField: string
  sortDirection: 'asc' | 'desc'
  rows: Record<string, WorkspaceRowDraft>
}

export type WorkspaceDraftStatus = 'restored' | 'empty' | 'invalid'
