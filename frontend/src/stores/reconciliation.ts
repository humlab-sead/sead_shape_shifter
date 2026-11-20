/**
 * Pinia store for entity reconciliation state management.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  EntityResolutionCatalog,
  DeleteSpecificationResult,
  ReconciliationCandidate,
  AutoReconcileResult,
  ExportToMappingResult,
  ReconciliationPreviewRow,
  EntityResolutionListItem,
  EntityResolutionCatalogCreateRequest,
  EntityResolutionCatalogUpdateRequest,
  DecisionUpdateRequest,
  MappingEntityResponse,
  MappingEntryDeleteResponse,
  DecisionBatchRequest,
  DecisionBatchResult,
  DecisionBatchIssue,
  DecisionDraftRequest,
  DecisionState,
  SelectionBrowseResult,
  SelectionCapabilities,
  SelectionSearchRequest,
  SelectionSearchResult,
  WorkspaceDraft,
  WorkspaceDraftStatus,
} from '@/types/reconciliation'
import { apiClient } from '@/api/client'
import { reconciliationSpecApi, reconciliationServiceApi } from '@/api/reconciliation'
// import { load } from 'js-yaml'

type PreviewDataByProject = Record<string, Record<string, Record<string, ReconciliationPreviewRow[]>>>
type PreviewErrorsByProject = Record<string, Record<string, Record<string, string>>>
type MappingDataByProject = Record<string, Record<string, MappingEntityResponse>>

const WORKSPACE_DRAFT_STORAGE_KEY = 'shapeshifter.reconciliation.workspace'
const WORKSPACE_DRAFT_VERSION = 1

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response
    const detail = response?.data?.detail
    if (typeof detail === 'string') return detail
    if (isRecord(detail) && typeof detail.message === 'string') return detail.message
  }
  return fallback
}

/** Read the row-level issues a rejected batch decision save reported. */
function getDecisionBatchIssues(error: unknown): DecisionBatchIssue[] {
  if (typeof error !== 'object' || error === null || !('response' in error)) return []
  const response = (error as { response?: { data?: { detail?: unknown } } }).response
  const detail = response?.data?.detail
  if (!isRecord(detail) || !Array.isArray(detail.issues)) return []
  return detail.issues.filter(
    (issue): issue is DecisionBatchIssue =>
      isRecord(issue) && typeof issue.code === 'string' && typeof issue.message === 'string'
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * Return browser storage, or null when the browser blocks it.
 *
 * Storage can be unavailable in private modes or when the origin is opaque, so
 * draft persistence must fail visibly instead of throwing during review.
 */
function browserStorage(): Storage | null {
  try {
    return typeof globalThis.localStorage === 'undefined' ? null : globalThis.localStorage
  } catch {
    return null
  }
}

function workspaceScopeId(projectName: string, entityName: string, targetField: string): string {
  return JSON.stringify([projectName, entityName, targetField])
}

function isStagedDecision(value: unknown): boolean {
  if (!isRecord(value)) return false
  if (value.status === 'local-only') return true
  return (
    value.status === 'accepted' &&
    typeof value.id === 'string' &&
    value.id.length > 0 &&
    Number.isInteger(value.target_id) &&
    (value.target_id as number) > 0 &&
    typeof value.name === 'string'
  )
}

function isValidWorkspaceDraft(value: unknown): value is WorkspaceDraft {
  if (!isRecord(value)) return false
  if (value.focusedKey !== null && typeof value.focusedKey !== 'string') return false
  if (value.mode !== 'search' && value.mode !== 'browse') return false
  if (typeof value.searchQuery !== 'string' || typeof value.browseText !== 'string') return false
  if (!isRecord(value.browseFieldFilters)) return false
  if (Object.values(value.browseFieldFilters).some((entry) => typeof entry !== 'string')) return false
  if (typeof value.sortField !== 'string') return false
  if (value.sortDirection !== 'asc' && value.sortDirection !== 'desc') return false
  if (!isRecord(value.rows)) return false

  return Object.values(value.rows).every((row) => {
    if (!isRecord(row)) return false
    if (typeof row.query !== 'string' || typeof row.notes !== 'string') return false
    if (row.decision !== null && !isStagedDecision(row.decision)) return false
    return isRecord(row.displayedValues)
  })
}

export const useReconciliationStore = defineStore('reconciliation', () => {
  // State
  const reconciliationConfig = ref<EntityResolutionCatalog | null>(null)
  const previewData = ref<PreviewDataByProject>({})
  const previewErrors = ref<PreviewErrorsByProject>({})
  const mappingData = ref<MappingDataByProject>({})
  const mappingErrors = ref<Record<string, Record<string, string>>>({})
  const mappingLoading = ref<Record<string, Record<string, boolean>>>({})
  const previewRequestVersions = new Map<string, number>()
  const mappingRequestVersions = new Map<string, number>()
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedTarget = ref<string | null>(null) // Currently selected target field

  // Specification management state
  const specifications = ref<EntityResolutionListItem[]>([])
  const selectedSpec = ref<EntityResolutionListItem | null>(null)
  const loadingSpecs = ref(false)
  const specsError = ref<string | null>(null)

  // Getters
  const reconcilableEntities = computed(() => {
    if (!reconciliationConfig.value) return []
    return Object.keys(reconciliationConfig.value.entities).filter((entityName) => {
      const targetFields = reconciliationConfig.value!.entities[entityName]
      if (!targetFields) return false
      // Entity is reconcilable if it has at least one target with a service_type
      return Object.values(targetFields).some((spec) => spec?.remote?.service_type != null)
    })
  })

  // Get available targets for a specific entity
  const getEntityTargets = computed(() => {
    return (entityName: string): string[] => {
      if (!reconciliationConfig.value || !reconciliationConfig.value.entities[entityName]) {
        return []
      }
      return Object.keys(reconciliationConfig.value.entities[entityName])
    }
  })

  const hasConfig = computed(() => reconciliationConfig.value !== null)

  // Actions
  async function loadEntityResolutionCatalog(projectName: string) {
    loading.value = true
    error.value = null
    try {
      console.log(`[Reconciliation Store] Loading config for project: ${projectName}`)
      const response = await apiClient.get(`/projects/${projectName}/reconciliation`)
      console.log('[Reconciliation Store] Config loaded:', response.data)
      reconciliationConfig.value = response.data
      console.log('[Reconciliation Store] Reconcilable entities:', reconcilableEntities.value)
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to load reconciliation config'
      console.error('[Reconciliation Store] Failed to load reconciliation config:', e)
      console.error('[Reconciliation Store] Error details:', e.response)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function saveEntityResolutionCatalog(projectName: string) {
    if (!reconciliationConfig.value) {
      throw new Error('No config to save')
    }

    loading.value = true
    error.value = null
    try {
      const response = await apiClient.put(`/projects/${projectName}/reconciliation`, reconciliationConfig.value)
      reconciliationConfig.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to save reconciliation config'
      console.error('Failed to save reconciliation config:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function saveEntityResolutionCatalogRaw(projectName: string, yamlContent: string) {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.put(`/projects/${projectName}/reconciliation/raw`, yamlContent, {
        headers: { 'Content-Type': 'text/plain' },
      })
      reconciliationConfig.value = response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to save reconciliation config'
      console.error('Failed to save reconciliation config:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function autoReconcile(
    projectName: string,
    entityName: string,
    targetField: string,
    threshold: number = 0.95,
    reviewThreshold?: number
  ): Promise<AutoReconcileResult> {
    loading.value = true
    error.value = null
    try {
      const result = await reconciliationServiceApi.autoReconcile(
        projectName,
        entityName,
        targetField,
        threshold,
        reviewThreshold
      )

      // Reload config to get updated mappings
      await loadEntityResolutionCatalog(projectName)

      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Auto-reconciliation failed'
      console.error('Auto-reconciliation failed:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function autoReconcileAsync(
    projectName: string,
    entityName: string,
    targetField: string,
    threshold: number = 0.95,
    reviewThreshold?: number
  ): Promise<{ operation_id: string; message: string }> {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post(
        `/projects/${projectName}/reconciliation/${entityName}/${targetField}/auto-reconcile`,
        null,
        { params: { threshold, review_threshold: reviewThreshold } }
      )

      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to start reconciliation'
      console.error('Failed to start reconciliation:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateMapping(
    projectName: string,
    entityName: string,
    targetField: string,
    request: DecisionUpdateRequest,
    notes?: string
  ) {
    loading.value = true
    error.value = null
    try {
      const decision = notes === undefined ? request : { ...request, notes }
      reconciliationConfig.value = await reconciliationServiceApi.updateDecision(
        projectName,
        entityName,
        targetField,
        decision
      )
      await Promise.all([
        loadEntityResolutionCatalog(projectName),
        loadPreviewData(projectName, entityName, targetField),
      ])
    } catch (e: any) {
      error.value = getErrorMessage(e, 'Failed to update mapping')
      console.error('Failed to update mapping:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteMapping(projectName: string, entityName: string, targetField: string, localKeyValue: string) {
    loading.value = true
    error.value = null
    try {
      reconciliationConfig.value = await reconciliationServiceApi.deleteDecision(
        projectName,
        entityName,
        targetField,
        localKeyValue
      )
      await Promise.all([
        loadEntityResolutionCatalog(projectName),
        loadPreviewData(projectName, entityName, targetField),
      ])
    } catch (e: any) {
      error.value = getErrorMessage(e, 'Failed to delete mapping')
      console.error('Failed to delete mapping:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteReviewDecision(
    projectName: string,
    entityName: string,
    targetField: string,
    localKeyValue: string
  ) {
    try {
      return await reconciliationServiceApi.deleteDecision(projectName, entityName, targetField, localKeyValue)
    } catch (e: any) {
      error.value = getErrorMessage(e, 'Failed to clear review decision')
      throw e
    }
  }

  async function suggestEntities(
    projectName: string,
    entityName: string,
    targetField: string,
    query: string
  ): Promise<ReconciliationCandidate[]> {
    if (query.length < 2) {
      return []
    }

    try {
      return await reconciliationServiceApi.suggestEntities(projectName, entityName, targetField, query)
    } catch (e: any) {
      error.value = getErrorMessage(e, 'Failed to get suggestions')
      console.error('Failed to get entity suggestions:', e)
      throw e
    }
  }

  function setPreviewError(projectName: string, entityName: string, targetField: string, message: string | null) {
    const projectErrors = previewErrors.value[projectName] ?? {}
    const entityErrors = { ...(projectErrors[entityName] ?? {}) }
    if (message === null) {
      delete entityErrors[targetField]
    } else {
      entityErrors[targetField] = message
    }
    previewErrors.value = {
      ...previewErrors.value,
      [projectName]: { ...projectErrors, [entityName]: entityErrors },
    }
  }

  async function loadPreviewData(
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<ReconciliationPreviewRow[]> {
    const requestKey = JSON.stringify([projectName, entityName, targetField])
    const requestVersion = (previewRequestVersions.get(requestKey) ?? 0) + 1
    previewRequestVersions.set(requestKey, requestVersion)
    setPreviewError(projectName, entityName, targetField, null)
    try {
      const rows = await reconciliationServiceApi.getPreview(projectName, entityName, targetField)
      if (previewRequestVersions.get(requestKey) === requestVersion) {
        const projectData = previewData.value[projectName] ?? {}
        const entityData = projectData[entityName] ?? {}
        previewData.value = {
          ...previewData.value,
          [projectName]: { ...projectData, [entityName]: { ...entityData, [targetField]: rows } },
        }
      }
      return rows
    } catch (e: any) {
      const message = getErrorMessage(e, 'Failed to load reconciliation preview')
      if (previewRequestVersions.get(requestKey) === requestVersion) {
        setPreviewError(projectName, entityName, targetField, message)
      }
      console.error('[Reconciliation Store] Failed to load preview data:', e)
      throw e
    }
  }

  async function loadMappingData(
    projectName: string,
    entityName: string,
    targetField?: string
  ): Promise<MappingEntityResponse> {
    const requestKey = JSON.stringify([projectName, entityName])
    const requestVersion = (mappingRequestVersions.get(requestKey) ?? 0) + 1
    mappingRequestVersions.set(requestKey, requestVersion)
    const projectLoading = mappingLoading.value[projectName] ?? {}
    mappingLoading.value = { ...mappingLoading.value, [projectName]: { ...projectLoading, [entityName]: true } }
    const projectErrors = { ...(mappingErrors.value[projectName] ?? {}) }
    delete projectErrors[entityName]
    mappingErrors.value = { ...mappingErrors.value, [projectName]: projectErrors }

    try {
      const result = targetField
        ? await reconciliationServiceApi.getEntityMapping(projectName, entityName, targetField)
        : await reconciliationServiceApi.getEntityMapping(projectName, entityName)
      if (mappingRequestVersions.get(requestKey) === requestVersion) {
        const projectMappings = mappingData.value[projectName] ?? {}
        mappingData.value = { ...mappingData.value, [projectName]: { ...projectMappings, [entityName]: result } }
      }
      return result
    } catch (e: any) {
      const message = getErrorMessage(e, 'Failed to load mapping sidecar')
      if (mappingRequestVersions.get(requestKey) === requestVersion) {
        mappingErrors.value = {
          ...mappingErrors.value,
          [projectName]: { ...(mappingErrors.value[projectName] ?? {}), [entityName]: message },
        }
      }
      console.error('Failed to load mapping sidecar:', e)
      throw e
    } finally {
      if (mappingRequestVersions.get(requestKey) === requestVersion) {
        mappingLoading.value = {
          ...mappingLoading.value,
          [projectName]: { ...(mappingLoading.value[projectName] ?? {}), [entityName]: false },
        }
      }
    }
  }

  async function deleteMappingEntry(
    projectName: string,
    entityName: string,
    localKeyValue: string,
    targetField: string,
    confirmProtected: boolean
  ): Promise<MappingEntryDeleteResponse> {
    try {
      return await reconciliationServiceApi.deleteMappingEntry(
        projectName,
        entityName,
        localKeyValue,
        targetField,
        confirmProtected
      )
    } catch (e: any) {
      error.value = getErrorMessage(e, 'Failed to delete mapping sidecar entry')
      throw e
    }
  }

  async function putManualMapping(
    projectName: string,
    entityName: string,
    localKeyValue: string,
    targetId: number,
    notes?: string,
    targetField?: string
  ) {
    try {
      const result = await reconciliationServiceApi.putManualMapping(projectName, entityName, localKeyValue, {
        target_id: targetId,
        notes,
      })
      try {
        await loadMappingData(projectName, entityName, targetField)
      } catch (e: unknown) {
        throw new Error(
          `Manual link was saved, but its sidecar could not be reloaded: ${getErrorMessage(e, 'request failed')}`
        )
      }
      return result
    } catch (e: any) {
      const message = getErrorMessage(e, 'Failed to save manual mapping link')
      mappingErrors.value = {
        ...mappingErrors.value,
        [projectName]: { ...(mappingErrors.value[projectName] ?? {}), [entityName]: message },
      }
      console.error('Failed to save manual mapping link:', e)
      throw e
    }
  }

  function clearError() {
    error.value = null
  }

  async function checkServiceHealth() {
    try {
      return await reconciliationServiceApi.checkHealth()
    } catch (e: any) {
      console.error('Failed to check reconciliation service health:', e)
      throw e
    }
  }

  async function getServiceManifest(): Promise<unknown> {
    try {
      return await reconciliationServiceApi.getManifest()
    } catch (e: any) {
      console.error('Failed to get reconciliation service manifest:', e)
      throw e
    }
  }

  async function exportToMapping(
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<ExportToMappingResult> {
    loading.value = true
    error.value = null
    try {
      const result = await reconciliationServiceApi.exportToMapping(projectName, entityName, targetField)
      const requestKey = JSON.stringify([projectName, entityName])
      mappingRequestVersions.set(requestKey, (mappingRequestVersions.get(requestKey) ?? 0) + 1)
      const projectMappings = { ...(mappingData.value[projectName] ?? {}) }
      delete projectMappings[entityName]
      mappingData.value = { ...mappingData.value, [projectName]: projectMappings }
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to export reconciliation links to mapping'
      console.error('Failed to export reconciliation links to mapping:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  // Record selection and batch decision actions

  async function loadSelectionCapabilities(
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<SelectionCapabilities> {
    return await reconciliationServiceApi.getSelectionCapabilities(projectName, entityName, targetField)
  }

  async function searchSelection(
    projectName: string,
    entityName: string,
    targetField: string,
    request: SelectionSearchRequest
  ): Promise<SelectionSearchResult> {
    return await reconciliationServiceApi.searchSelection(projectName, entityName, targetField, request)
  }

  async function browseSelection(
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<SelectionBrowseResult> {
    return await reconciliationServiceApi.browseSelection(projectName, entityName, targetField)
  }

  /**
   * Read the saved decisions that the server currently holds for one specification.
   *
   * This is a plain catalog read used for the advisory pre-save comparison. It does
   * not replace the in-memory catalog, so unsaved view state stays stable.
   */
  async function fetchSavedDecisionStates(
    projectName: string,
    entityName: string,
    targetField: string
  ): Promise<Record<string, DecisionState>> {
    const response = await apiClient.get<EntityResolutionCatalog>(`/projects/${projectName}/reconciliation`)
    return decisionStatesFromCatalog(response.data, entityName, targetField)
  }

  /** Build saved-decision state per encoded key from a catalog payload. */
  function decisionStatesFromCatalog(
    catalog: EntityResolutionCatalog | null,
    entityName: string,
    targetField: string
  ): Record<string, DecisionState> {
    const states: Record<string, DecisionState> = {}
    const mapping = catalog?.entities?.[entityName]?.[targetField]?.mapping ?? []
    for (const decision of mapping) {
      states[decision.local_key_value] = {
        status: decision.status,
        target_id: decision.target_id ?? null,
        candidate_id: decision.candidate_id ?? null,
        notes: decision.notes ?? null,
      }
    }
    return states
  }

  /** Build saved-decision state per encoded key from the loaded preview rows. */
  function decisionStatesFromPreview(rows: ReconciliationPreviewRow[]): Record<string, DecisionState> {
    const states: Record<string, DecisionState> = {}
    for (const row of rows) {
      const key = row.local_key_value
      if (!key || row.status === null || row.status === undefined) continue
      states[key] = {
        status: row.status,
        target_id: row.target_id ?? null,
        candidate_id: row.candidate_id ?? null,
        notes: row.notes ?? null,
      }
    }
    return states
  }

  /** Return the drafted keys whose saved decision differs from the loaded state. */
  function changedDecisionKeys(
    loaded: Record<string, DecisionState>,
    current: Record<string, DecisionState>,
    draftedKeys: string[]
  ): string[] {
    return draftedKeys.filter((key) => {
      const before = loaded[key]
      const after = current[key]
      if (!before && !after) return false
      if (!before || !after) return true
      return (
        before.status !== after.status ||
        before.target_id !== after.target_id ||
        before.candidate_id !== after.candidate_id ||
        before.notes !== after.notes
      )
    })
  }

  /**
   * Save every staged decision in one batch and patch only the rows it returned.
   *
   * A failed batch leaves the preview and the saved-decision baseline untouched so
   * the reviewer can correct the reported rows and retry deliberately.
   */
  async function saveDecisionBatch(
    projectName: string,
    entityName: string,
    targetField: string,
    drafts: DecisionDraftRequest[]
  ): Promise<DecisionBatchResult> {
    const request: DecisionBatchRequest = { drafts }
    try {
      const result = await reconciliationServiceApi.saveDecisionBatch(projectName, entityName, targetField, request)
      patchSavedDecisions(projectName, entityName, targetField, result)
      return result
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to save reconciliation decisions')
      throw e
    }
  }

  /** Patch the preview rows a successful batch confirmed, without reloading the preview. */
  function patchSavedDecisions(
    projectName: string,
    entityName: string,
    targetField: string,
    result: DecisionBatchResult
  ) {
    const rows = previewData.value[projectName]?.[entityName]?.[targetField]
    if (!rows || !result.saved.length) return

    const savedByKey = new Map(result.saved.map((saved) => [saved.local_key_value, saved]))
    const patched = rows.map((row) => {
      const saved = row.local_key_value ? savedByKey.get(row.local_key_value) : undefined
      if (!saved) return row
      return {
        ...row,
        status: saved.status,
        target_id: saved.target_id ?? null,
        candidate_id: saved.candidate_id ?? null,
        notes: saved.notes ?? '',
        // The saved decision was validated against the current source row, so
        // earlier reconciliation messages for this row are stale.
        errors: [],
      } as ReconciliationPreviewRow
    })

    previewData.value = {
      ...previewData.value,
      [projectName]: {
        ...(previewData.value[projectName] ?? {}),
        [entityName]: { ...(previewData.value[projectName]?.[entityName] ?? {}), [targetField]: patched },
      },
    }
  }

  /**
   * Restore the browser draft stored for one specification.
   *
   * Drafts are versioned and scoped by project, entity, and target field. A
   * malformed or outdated entry is cleared and reported instead of applied, so one
   * scope never inherits another scope's work.
   */
  function loadWorkspaceDraft(
    projectName: string,
    entityName: string,
    targetField: string
  ): { status: WorkspaceDraftStatus; draft: WorkspaceDraft | null } {
    const scopeId = workspaceScopeId(projectName, entityName, targetField)
    const storage = browserStorage()
    if (!storage) return { status: 'empty', draft: null }

    let scopes: Record<string, unknown>
    try {
      const raw = storage.getItem(WORKSPACE_DRAFT_STORAGE_KEY)
      if (!raw) return { status: 'empty', draft: null }
      const parsed: unknown = JSON.parse(raw)
      if (!isRecord(parsed) || parsed.version !== WORKSPACE_DRAFT_VERSION || !isRecord(parsed.scopes)) {
        storage.removeItem(WORKSPACE_DRAFT_STORAGE_KEY)
        return { status: 'invalid', draft: null }
      }
      scopes = parsed.scopes
    } catch {
      return { status: 'invalid', draft: null }
    }

    if (!(scopeId in scopes)) return { status: 'empty', draft: null }

    const entry = scopes[scopeId]
    if (!isValidWorkspaceDraft(entry)) {
      clearWorkspaceDraft(projectName, entityName, targetField)
      return { status: 'invalid', draft: null }
    }
    return { status: 'restored', draft: entry }
  }

  /** Store the browser draft for one specification; false means it was not persisted. */
  function saveWorkspaceDraft(
    projectName: string,
    entityName: string,
    targetField: string,
    draft: WorkspaceDraft
  ): boolean {
    const scopeId = workspaceScopeId(projectName, entityName, targetField)
    const storage = browserStorage()
    if (!storage) return false
    try {
      const raw = storage.getItem(WORKSPACE_DRAFT_STORAGE_KEY)
      const parsed: unknown = raw ? JSON.parse(raw) : null
      const scopes =
        isRecord(parsed) && parsed.version === WORKSPACE_DRAFT_VERSION && isRecord(parsed.scopes)
          ? { ...parsed.scopes }
          : {}
      scopes[scopeId] = draft
      storage.setItem(WORKSPACE_DRAFT_STORAGE_KEY, JSON.stringify({ version: WORKSPACE_DRAFT_VERSION, scopes }))
      return true
    } catch {
      return false
    }
  }

  /** Remove the browser draft for one specification. */
  function clearWorkspaceDraft(projectName: string, entityName: string, targetField: string) {
    const scopeId = workspaceScopeId(projectName, entityName, targetField)
    const storage = browserStorage()
    if (!storage) return
    try {
      const raw = storage.getItem(WORKSPACE_DRAFT_STORAGE_KEY)
      if (!raw) return
      const parsed: unknown = JSON.parse(raw)
      if (!isRecord(parsed) || !isRecord(parsed.scopes) || !(scopeId in parsed.scopes)) {
        storage.removeItem(WORKSPACE_DRAFT_STORAGE_KEY)
        return
      }
      const scopes = { ...parsed.scopes }
      delete scopes[scopeId]
      storage.setItem(WORKSPACE_DRAFT_STORAGE_KEY, JSON.stringify({ version: WORKSPACE_DRAFT_VERSION, scopes }))
    } catch {
      // A storage failure must not break the review workspace.
    }
  }

  function $reset() {
    reconciliationConfig.value = null
    previewData.value = {}
    previewErrors.value = {}
    mappingData.value = {}
    mappingErrors.value = {}
    mappingLoading.value = {}
    previewRequestVersions.clear()
    mappingRequestVersions.clear()
    loading.value = false
    error.value = null
    selectedTarget.value = null
    specifications.value = []
    selectedSpec.value = null
    loadingSpecs.value = false
    specsError.value = null
  }

  // Specification management actions

  async function loadSpecifications(projectName: string) {
    loadingSpecs.value = true
    specsError.value = null
    try {
      specifications.value = await reconciliationSpecApi.listSpecifications(projectName)
    } catch (e: any) {
      specsError.value = e.response?.data?.detail || 'Failed to load specifications'
      console.error('Failed to load specifications:', e)
      throw e
    } finally {
      loadingSpecs.value = false
    }
  }

  async function createSpecification(projectName: string, request: EntityResolutionCatalogCreateRequest) {
    loadingSpecs.value = true
    specsError.value = null
    try {
      const updatedConfig = await reconciliationSpecApi.createSpecification(projectName, request)
      reconciliationConfig.value = updatedConfig
      // Reload specifications list
      await loadSpecifications(projectName)
    } catch (e: any) {
      specsError.value = e.response?.data?.detail || 'Failed to create specification'
      console.error('Failed to create specification:', e)
      throw e
    } finally {
      loadingSpecs.value = false
    }
  }

  async function updateSpecification(
    projectName: string,
    entityName: string,
    targetField: string,
    request: EntityResolutionCatalogUpdateRequest
  ) {
    loadingSpecs.value = true
    specsError.value = null
    try {
      const updatedConfig = await reconciliationSpecApi.updateSpecification(
        projectName,
        entityName,
        targetField,
        request
      )
      reconciliationConfig.value = updatedConfig
      // Reload specifications list
      await loadSpecifications(projectName)
    } catch (e: any) {
      specsError.value = e.response?.data?.detail || 'Failed to update specification'
      console.error('Failed to update specification:', e)
      throw e
    } finally {
      loadingSpecs.value = false
    }
  }

  async function deleteSpecification(
    projectName: string,
    entityName: string,
    targetField: string,
    force: boolean = false
  ): Promise<{ removedOwnedLinks: number; removedOwnedApprovals: number }> {
    loadingSpecs.value = true
    specsError.value = null
    try {
      const result: DeleteSpecificationResult = await reconciliationSpecApi.deleteSpecification(
        projectName,
        entityName,
        targetField,
        force
      )
      const {
        removed_owned_links: removedOwnedLinks,
        removed_owned_approvals: removedOwnedApprovals,
        ...updatedConfig
      } = result
      reconciliationConfig.value = updatedConfig
      // Reload specifications list
      await loadSpecifications(projectName)
      // Clear selected spec if it was deleted
      if (selectedSpec.value?.entity_name === entityName && selectedSpec.value?.target_field === targetField) {
        selectedSpec.value = null
      }
      return { removedOwnedLinks, removedOwnedApprovals }
    } catch (e: any) {
      specsError.value = e.response?.data?.detail || 'Failed to delete specification'
      console.error('Failed to delete specification:', e)
      throw e
    } finally {
      loadingSpecs.value = false
    }
  }

  async function getAvailableFields(projectName: string, entityName: string): Promise<string[]> {
    try {
      return await reconciliationSpecApi.getAvailableFields(projectName, entityName)
    } catch (e: any) {
      console.error('Failed to get available fields:', e)
      throw e
    }
  }

  async function getMappingCount(projectName: string, entityName: string, targetField: string): Promise<number> {
    try {
      return await reconciliationSpecApi.getMappingCount(projectName, entityName, targetField)
    } catch (e: any) {
      console.error('Failed to get mapping count:', e)
      throw e
    }
  }

  return {
    // State
    reconciliationConfig,
    previewData,
    previewErrors,
    mappingData,
    mappingErrors,
    mappingLoading,
    loading,
    error,
    selectedTarget,
    specifications,
    selectedSpec,
    loadingSpecs,
    specsError,

    // Getters
    reconcilableEntities,
    getEntityTargets,
    hasConfig,

    // Actions
    loadEntityResolutionCatalog,
    saveEntityResolutionCatalog,
    saveEntityResolutionCatalogRaw,
    autoReconcile,
    autoReconcileAsync,
    updateMapping,
    deleteMapping,
    deleteReviewDecision,
    deleteMappingEntry,
    suggestEntities,
    loadPreviewData,
    loadMappingData,
    putManualMapping,
    checkServiceHealth,
    getServiceManifest,
    exportToMapping,
    clearError,
    $reset,

    // Record selection and batch decision actions
    loadSelectionCapabilities,
    searchSelection,
    browseSelection,
    fetchSavedDecisionStates,
    decisionStatesFromCatalog,
    decisionStatesFromPreview,
    changedDecisionKeys,
    saveDecisionBatch,
    patchSavedDecisions,
    loadWorkspaceDraft,
    saveWorkspaceDraft,
    clearWorkspaceDraft,
    getDecisionBatchIssues,

    // Specification management actions
    loadSpecifications,
    createSpecification,
    updateSpecification,
    deleteSpecification,
    getAvailableFields,
    getMappingCount,
  }
})
