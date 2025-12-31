/**
 * Session management composable for easy integration in components.
 */

import { computed, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useSessionStore } from '@/stores/session'
import { useProjectStore } from '@/stores/project'
import type { SessionCreateRequest } from '@/types/session'

export function useSession() {
  const sessionStore = useSessionStore()
  const configStore = useProjectStore()

  const {
    currentSession,
    activeSessions,
    loading,
    error,
    hasActiveSession,
    sessionId,
    projectName: configName,
    version,
    isModified,
    hasConcurrentEdits,
    otherActiveSessions,
  } = storeToRefs(sessionStore)

  /**
   * Start a new editing session for a configuration.
   */
  async function startSession(configName: string, userId?: string) {
    const request: SessionCreateRequest = {
      project_name: configName,
      user_id: userId,
    }

    try {
      await sessionStore.createSession(request)
      
      // Start auto-refresh to detect concurrent edits
      sessionStore.startAutoRefresh(30000) // 30 seconds

      return currentSession.value
    } catch (err) {
      console.error('Failed to start session:', err)
      throw err
    }
  }

  /**
   * End the current editing session.
   */
  async function endSession() {
    try {
      await sessionStore.closeSession()
      sessionStore.stopAutoRefresh()
    } catch (err) {
      console.error('Failed to end session:', err)
      throw err
    }
  }

  /**
   * Save configuration with version check.
   */
  async function saveWithVersionCheck() {
    if (!hasActiveSession.value) {
      throw new Error('No active session')
    }

    const currentVersion = version.value

    try {
      // Save through config store (will include version in request)
      await configStore.saveConfiguration()

      // Increment version on successful save
      sessionStore.incrementVersion()

      return true
    } catch (err: any) {
      // Check for conflict error (409)
      if (err?.response?.status === 409) {
        // Version conflict detected
        const serverVersion = err.response.data?.current_version
        
        if (serverVersion && sessionStore.checkVersionConflict(serverVersion)) {
          throw new Error(
            `Project was modified by another user. ` +
            `Expected version ${currentVersion}, current version ${serverVersion}. ` +
            `Please reload and merge changes.`
          )
        }
      }
      throw err
    }
  }

  /**
   * Mark configuration as modified.
   */
  function markAsModified() {
    sessionStore.markModified()
    configStore.hasUnsavedChanges = true
  }

  /**
   * Check for concurrent editors.
   */
  function checkConcurrentEditors() {
    return {
      hasConcurrent: hasConcurrentEdits.value,
      count: otherActiveSessions.value.length,
      sessions: otherActiveSessions.value,
    }
  }

  /**
   * Show warning if there are concurrent editors.
   */
  const concurrentEditWarning = computed(() => {
    if (!hasConcurrentEdits.value) return null

    const count = otherActiveSessions.value.length
    return `${count} other user${count > 1 ? 's are' : ' is'} currently editing this configuration`
  })

  /**
   * Auto-cleanup on component unmount.
   */
  onUnmounted(() => {
    sessionStore.stopAutoRefresh()
  })

  /**
   * Watch for configuration changes and mark as modified.
   */
  function watchConfigChanges(callback?: () => void) {
    return watch(
      () => configStore.selectedConfig,
      () => {
        if (hasActiveSession.value) {
          markAsModified()
          callback?.()
        }
      },
      { deep: true }
    )
  }

  return {
    // State
    currentSession,
    activeSessions,
    loading,
    error,

    // Computed
    hasActiveSession,
    sessionId,
    configName,
    version,
    isModified,
    hasConcurrentEdits,
    otherActiveSessions,
    concurrentEditWarning,

    // Actions
    startSession,
    endSession,
    saveWithVersionCheck,
    markAsModified,
    checkConcurrentEditors,
    watchConfigChanges,
  }
}
