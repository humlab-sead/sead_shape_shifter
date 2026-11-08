import { computed, ref, watch } from 'vue'
import type {
  FormattedError,
  LinkExceptionGroupName,
  LinkExceptionRowSide,
  LinkExperimentContextRequest,
  LinkExperimentContextResponse,
  LinkExperimentTrialRequest,
  LinkTroubleshootComparison,
  LinkTroubleshootExceptionRow,
  LinkTroubleshootJoinType,
  LinkTroubleshootTrialSettings,
} from '@/types'
import { EXCEPTION_ROW_PAGE_SIZE } from '@/types'
import { linkTroubleshooterApi } from '@/api/linkTroubleshooter'
import { formatErrorMessage } from '@/utils/errors'

/** Which bounded exception group the dialog currently shows. */
export type { LinkExceptionGroupName, LinkExceptionRowSide }

export type LinkExceptionSide = LinkExceptionRowSide

interface TrialControls {
  localKeys: string[]
  remoteKeys: string[]
  how: LinkTroubleshootJoinType | null
  allowNullKeys: boolean | null
  nullKeysEqual: boolean | null
}

const DEFAULT_PAGE_SIZE = EXCEPTION_ROW_PAGE_SIZE
const DEFAULT_GROUP: LinkExceptionGroupName = 'unmatched'
const DEFAULT_SIDE: LinkExceptionSide = 'baseline'

function emptyControls(): TrialControls {
  return { localKeys: [], remoteKeys: [], how: null, allowNullKeys: null, nullKeysEqual: null }
}

function cloneControls(controls: TrialControls): TrialControls {
  return {
    localKeys: [...controls.localKeys],
    remoteKeys: [...controls.remoteKeys],
    how: controls.how,
    allowNullKeys: controls.allowNullKeys,
    nullKeysEqual: controls.nullKeysEqual,
  }
}

function controlsSignature(controls: TrialControls): string {
  return JSON.stringify([
    controls.localKeys,
    controls.remoteKeys,
    controls.how,
    controls.allowNullKeys,
    controls.nullKeysEqual,
  ])
}

function explicitConstraint(constraints: Record<string, unknown>, key: string): boolean | null {
  const value = constraints[key]
  return typeof value === 'boolean' ? value : null
}

function normalizeJoinType(value: string | null | undefined): LinkTroubleshootJoinType | null {
  return value === 'inner' || value === 'left' ? value : null
}

/**
 * Build the controls that reproduce the retained snapshot's configured link.
 *
 * Complete baselines carry a resolved settings report. An incomplete baseline
 * can have no report, so the configured relationship and its explicit constraint
 * entries are used instead. An absent constraint entry means "inherit the
 * configured link" rather than an explicit false.
 */
function controlsFromContext(response: LinkExperimentContextResponse): TrialControls {
  const settings: LinkTroubleshootTrialSettings | null = response.baseline?.settings ?? null
  const configured = response.configured_keys
  const constraints = response.relationship?.constraints ?? {}
  return {
    localKeys: configured ? [...configured.local_keys] : [],
    remoteKeys: configured ? [...configured.remote_keys] : [],
    how: settings
      ? (settings.join_type.requested ?? settings.join_type.effective)
      : normalizeJoinType(response.relationship?.join_type),
    allowNullKeys: settings ? settings.allow_null_keys.requested : explicitConstraint(constraints, 'allow_null_keys'),
    nullKeysEqual: settings ? settings.null_keys_equal.requested : explicitConstraint(constraints, 'null_keys_equal'),
  }
}

function isContextExpired(caughtError: unknown): boolean {
  const response = (caughtError as { response?: { status?: number; data?: unknown } } | null)?.response
  if (!response || response.status !== 410) {
    return false
  }

  const detail = (response.data as { detail?: { error_type?: unknown; reason?: unknown } } | null)?.detail
  return detail?.reason === 'context_expired' || detail?.error_type === 'LinkExperimentContextExpired'
}

export function useLinkTroubleshooter(projectName: string) {
  const loading = ref(false)
  const error = ref<FormattedError | null>(null)
  /** The latest received retained baseline, including an incomplete one. */
  const context = ref<LinkExperimentContextResponse | null>(null)
  /** The latest accepted trial for this context, which may use older controls. */
  const trial = ref<LinkTroubleshootComparison | null>(null)
  /** Trial key names reported with the accepted trial response. */
  const trialLocalKeys = ref<string[]>([])
  const trialRemoteKeys = ref<string[]>([])
  /** True when the displayed trial was run with different controls. */
  const trialStale = ref(false)
  /** True when the original inputs were reopened after the context expired. */
  const refreshed = ref(false)

  const localKeys = ref<string[]>([])
  const remoteKeys = ref<string[]>([])
  const how = ref<LinkTroubleshootJoinType | null>(null)
  const allowNullKeys = ref<boolean | null>(null)
  const nullKeysEqual = ref<boolean | null>(null)

  const page = ref(1)
  const pageSize = ref(DEFAULT_PAGE_SIZE)
  const group = ref<LinkExceptionGroupName>(DEFAULT_GROUP)
  const side = ref<LinkExceptionSide>(DEFAULT_SIDE)

  /** Rows on the current browse page, loaded from the bounded row route. */
  const rows = ref<LinkTroubleshootExceptionRow[]>([])
  /** Full affected-row count for the selected group and side. */
  const rowTotalCount = ref(0)
  /** Affected-row browse cap reported by the backend. */
  const rowBrowseCap = ref(0)
  /** True when the full count exceeds the browse cap. */
  const rowBrowseCapReached = ref(false)
  /** Backend explanation when rows cannot be browsed for this selection. */
  const rowStatusMessage = ref<string | null>(null)
  const rowsLoading = ref(false)
  const rowsError = ref<FormattedError | null>(null)

  let identity: LinkExperimentContextRequest | null = null
  let originalControls: TrialControls = emptyControls()
  let acceptedTrialSignature: string | null = null
  /** Controls that produced the displayed trial, sent when browsing trial rows. */
  let acceptedTrialRequest: LinkExperimentTrialRequest | null = null
  let requestVersion = 0
  let rowsVersion = 0
  let applyingControls = false
  /** Prevent a repeated expiry while reopening after a row-browse failure. */
  let reopeningRows = false

  const canRunTrial = computed(
    () =>
      Boolean(context.value?.context_id) &&
      localKeys.value.length > 0 &&
      localKeys.value.length === remoteKeys.value.length &&
      localKeys.value.every((key, index) => key.trim().length > 0 && (remoteKeys.value[index] ?? '').trim().length > 0)
  )

  watch(
    () => {
      const controls: TrialControls = {
        localKeys: localKeys.value,
        remoteKeys: remoteKeys.value,
        how: how.value,
        allowNullKeys: allowNullKeys.value,
        nullKeysEqual: nullKeysEqual.value,
      }
      return controlsSignature(controls)
    },
    (signature) => {
      if (applyingControls) {
        return
      }
      // Edits invalidate in-flight responses but keep the last trial visible as
      // a clearly marked comparison until a new trial succeeds.
      requestVersion += 1
      loading.value = false
      trialStale.value = trial.value !== null && acceptedTrialSignature !== signature
      error.value = null
    },
    { flush: 'sync' }
  )

  function snapshotControls(): TrialControls {
    return {
      localKeys: [...localKeys.value],
      remoteKeys: [...remoteKeys.value],
      how: how.value,
      allowNullKeys: allowNullKeys.value,
      nullKeysEqual: nullKeysEqual.value,
    }
  }

  function applyControls(controls: TrialControls): void {
    applyingControls = true
    try {
      localKeys.value = [...controls.localKeys]
      remoteKeys.value = [...controls.remoteKeys]
      how.value = controls.how
      allowNullKeys.value = controls.allowNullKeys
      nullKeysEqual.value = controls.nullKeysEqual
    } finally {
      applyingControls = false
    }
  }

  function resetBrowsing(): void {
    page.value = 1
    pageSize.value = DEFAULT_PAGE_SIZE
    group.value = DEFAULT_GROUP
    side.value = DEFAULT_SIDE
  }

  /** Drop every loaded row page and ignore any in-flight row response. */
  function clearRows(): void {
    rowsVersion += 1
    rows.value = []
    rowTotalCount.value = 0
    rowBrowseCap.value = 0
    rowBrowseCapReached.value = false
    rowStatusMessage.value = null
    rowsLoading.value = false
    rowsError.value = null
  }

  /** Read one bounded page of affected source rows for the current selection. */
  async function loadExceptionRows(): Promise<void> {
    const contextId = context.value?.context_id
    const version = ++rowsVersion
    rowsError.value = null

    if (!contextId) {
      rows.value = []
      rowTotalCount.value = 0
      rowBrowseCap.value = 0
      rowBrowseCapReached.value = false
      rowStatusMessage.value = null
      rowsLoading.value = false
      return
    }

    const trialRequest = side.value === 'trial' ? acceptedTrialRequest : null
    if (side.value === 'trial' && trialRequest === null) {
      rows.value = []
      rowTotalCount.value = 0
      rowBrowseCap.value = 0
      rowBrowseCapReached.value = false
      rowStatusMessage.value = 'Run a trial before browsing trial rows.'
      rowsLoading.value = false
      return
    }

    rowsLoading.value = true
    try {
      const response = await linkTroubleshooterApi.exceptionRows(projectName, contextId, {
        side: side.value,
        group: group.value,
        offset: (page.value - 1) * pageSize.value,
        limit: pageSize.value,
        trial: trialRequest,
      })
      if (version !== rowsVersion) {
        return
      }
      rows.value = response.rows
      rowTotalCount.value = response.total_count
      rowBrowseCap.value = response.browse_cap
      rowBrowseCapReached.value = response.browse_cap_reached
      rowStatusMessage.value = response.status === 'available' ? null : (response.message ?? response.reason)
    } catch (caughtError: unknown) {
      if (version !== rowsVersion) {
        return
      }
      if (isContextExpired(caughtError)) {
        // The retained inputs are gone, so reopen the original warning instead
        // of showing a stale row error over an expired context. A repeated
        // expiry inside the reopen keeps the error instead of looping.
        if (!reopeningRows) {
          reopeningRows = true
          try {
            await refreshOriginalInputs()
          } finally {
            reopeningRows = false
          }
          return
        }
        rowsVersion += 1
        rowsError.value = {
          message: 'The retained link inputs expired. Reopen the troubleshooter to try again.',
        }
        rowsLoading.value = false
        return
      }
      rows.value = []
      rowTotalCount.value = 0
      rowBrowseCap.value = 0
      rowBrowseCapReached.value = false
      rowStatusMessage.value = null
      rowsError.value = formatErrorMessage(caughtError)
      console.error('Link troubleshooter exception-row request failed:', caughtError)
    } finally {
      if (version === rowsVersion) {
        rowsLoading.value = false
      }
    }
  }

  watch([side, group, page, pageSize], () => {
    void loadExceptionRows()
  })

  function adoptContext(response: LinkExperimentContextResponse): void {
    context.value = response
    trial.value = null
    trialLocalKeys.value = []
    trialRemoteKeys.value = []
    trialStale.value = false
    acceptedTrialSignature = null
    acceptedTrialRequest = null
    const controls = controlsFromContext(response)
    originalControls = cloneControls(controls)
    applyControls(controls)
    resetBrowsing()
    void loadExceptionRows()
  }

  function closeSupersededContext(): void {
    const contextId = context.value?.context_id
    if (!contextId) {
      return
    }
    void linkTroubleshooterApi.close(projectName, contextId).catch((caughtError: unknown) => {
      console.error('Link troubleshooter context cleanup failed:', caughtError)
    })
  }

  async function open(request: LinkExperimentContextRequest): Promise<LinkExperimentContextResponse | null> {
    closeSupersededContext()
    identity = {
      issue_type: request.issue_type,
      local_entity: request.local_entity,
      metadata: { ...request.metadata },
    }
    const version = ++requestVersion
    loading.value = true
    error.value = null
    context.value = null
    trial.value = null
    trialLocalKeys.value = []
    trialRemoteKeys.value = []
    trialStale.value = false
    acceptedTrialSignature = null
    refreshed.value = false
    originalControls = emptyControls()
    acceptedTrialRequest = null
    clearRows()
    applyControls(emptyControls())
    resetBrowsing()

    try {
      const response = await linkTroubleshooterApi.open(projectName, identity)
      if (version !== requestVersion) {
        return null
      }
      adoptContext(response)
      return response
    } catch (caughtError: unknown) {
      if (version === requestVersion) {
        error.value = formatErrorMessage(caughtError)
        context.value = null
        trial.value = null
        trialLocalKeys.value = []
        trialRemoteKeys.value = []
        trialStale.value = false
        acceptedTrialSignature = null
        console.error('Link troubleshooter request failed:', caughtError)
      }
      return null
    } finally {
      if (version === requestVersion) {
        loading.value = false
      }
    }
  }

  function toTrialRequest(controls: TrialControls): LinkExperimentTrialRequest {
    return {
      local_keys: [...controls.localKeys],
      remote_keys: [...controls.remoteKeys],
      how: controls.how,
      allow_null_keys: controls.allowNullKeys,
      null_keys_equal: controls.nullKeysEqual,
    }
  }

  async function run(): Promise<LinkTroubleshootComparison | null> {
    const contextId = context.value?.context_id
    if (!contextId || !canRunTrial.value) {
      return null
    }

    const submitted = snapshotControls()
    const submittedSignature = controlsSignature(submitted)
    const version = ++requestVersion
    loading.value = true
    error.value = null

    try {
      const response = await linkTroubleshooterApi.trial(projectName, contextId, toTrialRequest(submitted))
      if (version !== requestVersion || context.value?.context_id !== contextId) {
        return null
      }
      if (controlsSignature(snapshotControls()) !== submittedSignature) {
        return null
      }
      trial.value = response.trial
      trialLocalKeys.value = [...response.local_keys]
      trialRemoteKeys.value = [...response.remote_keys]
      acceptedTrialSignature = submittedSignature
      acceptedTrialRequest = toTrialRequest(submitted)
      trialStale.value = false
      // A trial shown while the trial side is already selected needs a fresh
      // page; otherwise the side change loads it once.
      if (side.value === 'trial') {
        void loadExceptionRows()
      }
      return response.trial
    } catch (caughtError: unknown) {
      if (version !== requestVersion || context.value?.context_id !== contextId) {
        return null
      }
      if (isContextExpired(caughtError)) {
        await refreshOriginalInputs()
        return null
      }
      error.value = formatErrorMessage(caughtError)
      console.error('Link troubleshooter trial failed:', caughtError)
      return null
    } finally {
      if (version === requestVersion) {
        loading.value = false
      }
    }
  }

  /**
   * Reopen the retained warning after its context expired.
   *
   * The expired trial is discarded, the original warning request reproduces a
   * fresh baseline, and the user must run a new trial. A failure to reproduce
   * is shown through the new context response instead of a stale comparison.
   */
  async function refreshOriginalInputs(): Promise<void> {
    const request = identity
    const version = ++requestVersion
    loading.value = true
    error.value = null
    context.value = null
    trial.value = null
    trialLocalKeys.value = []
    trialRemoteKeys.value = []
    trialStale.value = false
    acceptedTrialSignature = null
    refreshed.value = false

    try {
      if (!request) {
        error.value = { message: 'The original warning is unavailable, so the link could not be reopened.' }
        return
      }
      const response = await linkTroubleshooterApi.open(projectName, request)
      if (version !== requestVersion) {
        return
      }
      adoptContext(response)
      refreshed.value = true
    } catch (caughtError: unknown) {
      if (version === requestVersion) {
        context.value = null
        trial.value = null
        trialStale.value = false
        acceptedTrialSignature = null
        error.value = formatErrorMessage(caughtError)
        console.error('Link troubleshooter refresh failed:', caughtError)
      }
    } finally {
      if (version === requestVersion) {
        loading.value = false
      }
    }
  }

  /** Restore the latest received baseline and its original controls without a request. */
  function reset(): void {
    requestVersion += 1
    loading.value = false
    error.value = null
    trial.value = null
    trialLocalKeys.value = []
    trialRemoteKeys.value = []
    trialStale.value = false
    acceptedTrialSignature = null
    acceptedTrialRequest = null
    refreshed.value = false
    applyControls(cloneControls(originalControls))
    resetBrowsing()
    void loadExceptionRows()
  }

  /** Clear the dialog and release its owned context with best-effort cleanup. */
  async function close(): Promise<void> {
    const contextId = context.value?.context_id ?? null
    const version = ++requestVersion
    loading.value = false
    error.value = null
    context.value = null
    trial.value = null
    trialLocalKeys.value = []
    trialRemoteKeys.value = []
    trialStale.value = false
    acceptedTrialSignature = null
    refreshed.value = false
    identity = null
    originalControls = emptyControls()
    acceptedTrialRequest = null
    clearRows()
    applyControls(emptyControls())
    resetBrowsing()

    if (!contextId) {
      return
    }

    try {
      await linkTroubleshooterApi.close(projectName, contextId)
    } catch (caughtError: unknown) {
      if (version === requestVersion) {
        error.value = formatErrorMessage(caughtError)
      }
      console.error('Link troubleshooter context cleanup failed:', caughtError)
    }
  }

  return {
    loading,
    error,
    context,
    trial,
    trialLocalKeys,
    trialRemoteKeys,
    trialStale,
    refreshed,
    localKeys,
    remoteKeys,
    how,
    allowNullKeys,
    nullKeysEqual,
    page,
    pageSize,
    group,
    side,
    rows,
    rowTotalCount,
    rowBrowseCap,
    rowBrowseCapReached,
    rowStatusMessage,
    rowsLoading,
    rowsError,
    canRunTrial,
    open,
    run,
    reset,
    close,
  }
}
