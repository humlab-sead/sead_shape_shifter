/**
 * Session management store for multi-user configuration editing.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sessionsApi } from '@/api/sessions'
import type { SessionInfo, SessionCreateRequest } from '@/types/session'

export const useSessionStore = defineStore('session', () => {
  // State
  const currentSession = ref<SessionInfo | null>(null)
  const activeSessions = ref<SessionInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const hasActiveSession = computed(() => currentSession.value !== null)

  const sessionId = computed(() => currentSession.value?.session_id || null)

  const projectName = computed(() => currentSession.value?.project_name || null)

  const version = computed(() => currentSession.value?.version || 1)

  const isModified = computed(() => currentSession.value?.modified || false)

  const hasConcurrentEdits = computed(() => {
    return (currentSession.value?.concurrent_sessions || 0) > 1
  })

  const otherActiveSessions = computed(() => {
    if (!currentSession.value) return []
    return activeSessions.value.filter((s) => s.session_id !== currentSession.value?.session_id)
  })

  // Actions

  /**
   * Create a new editing session.
   */
  async function createSession(request: SessionCreateRequest): Promise<SessionInfo> {
    loading.value = true
    error.value = null

    try {
      const session = await sessionsApi.create(request)
      currentSession.value = session

      // Load active sessions to detect concurrent editing
      await refreshActiveSessions()

      return session
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create session'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Get current session info and refresh state.
   */
  async function refreshSession(): Promise<SessionInfo | null> {
    if (!hasActiveSession.value) return null

    loading.value = true
    error.value = null

    try {
      const session = await sessionsApi.getCurrent()
      currentSession.value = session
      return session
    } catch (err) {
      // Session may have expired
      if ((err as any)?.response?.status === 404) {
        currentSession.value = null
        error.value = 'Session expired or not found'
      } else {
        error.value = err instanceof Error ? err.message : 'Failed to refresh session'
      }
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Close the current session.
   */
  async function closeSession(): Promise<void> {
    if (!hasActiveSession.value) return

    loading.value = true
    error.value = null

    try {
      await sessionsApi.close()
      currentSession.value = null
      activeSessions.value = []
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to close session'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Refresh list of active sessions for current config.
   */
  async function refreshActiveSessions(): Promise<void> {
    if (!currentSession.value) return

    try {
      activeSessions.value = await sessionsApi.listActive(currentSession.value.project_name)

      // Update concurrent sessions count
      if (currentSession.value) {
        currentSession.value.concurrent_sessions = activeSessions.value.length
      }
    } catch (err) {
      console.error('Failed to refresh active sessions:', err)
      // Don't throw - this is a background operation
    }
  }

  /**
   * Mark session as modified.
   */
  function markModified(): void {
    if (currentSession.value) {
      currentSession.value.modified = true
    }
  }

  /**
   * Update session version (after successful save).
   */
  function incrementVersion(): void {
    if (currentSession.value) {
      currentSession.value.version += 1
      currentSession.value.modified = false
    }
  }

  /**
   * Check if there's a version conflict.
   */
  function checkVersionConflict(serverVersion: number): boolean {
    if (!currentSession.value) return false
    return currentSession.value.version !== serverVersion
  }

  /**
   * Reset store state.
   */
  function $reset(): void {
    currentSession.value = null
    activeSessions.value = []
    loading.value = false
    error.value = null
  }

  // Auto-refresh active sessions periodically when session is active
  let refreshInterval: number | null = null

  function startAutoRefresh(intervalMs: number = 30000): void {
    stopAutoRefresh()
    refreshInterval = window.setInterval(() => {
      if (hasActiveSession.value) {
        refreshActiveSessions()
      }
    }, intervalMs)
  }

  function stopAutoRefresh(): void {
    if (refreshInterval !== null) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  return {
    // State
    currentSession,
    activeSessions,
    loading,
    error,

    // Getters
    hasActiveSession,
    sessionId,
    projectName: projectName,
    version,
    isModified,
    hasConcurrentEdits,
    otherActiveSessions,

    // Actions
    createSession,
    refreshSession,
    closeSession,
    refreshActiveSessions,
    markModified,
    incrementVersion,
    checkVersionConflict,
    startAutoRefresh,
    stopAutoRefresh,
    $reset,
  }
})
