import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '../session'
import * as sessionsApi from '@/api/sessions'
import type { SessionInfo, SessionCreateRequest } from '@/types/session'

// Mock the sessions API
vi.mock('@/api/sessions', () => ({
  sessionsApi: {
    create: vi.fn(),
    getCurrent: vi.fn(),
    close: vi.fn(),
    listActive: vi.fn(),
  },
}))

const mockSessionsApi = sessionsApi.sessionsApi as any

describe('useSessionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('initial state', () => {
    it('should initialize with null session', () => {
      const store = useSessionStore()

      expect(store.currentSession).toBeNull()
      expect(store.activeSessions).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should have computed properties returning default values', () => {
      const store = useSessionStore()

      expect(store.hasActiveSession).toBe(false)
      expect(store.sessionId).toBeNull()
      expect(store.projectName).toBeNull()
      expect(store.version).toBe(1)
      expect(store.isModified).toBe(false)
      expect(store.hasConcurrentEdits).toBe(false)
      expect(store.otherActiveSessions).toEqual([])
    })
  })

  describe('createSession', () => {
    it('should create a session successfully', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      const request: SessionCreateRequest = {
        project_name: 'test-project',
      }

      mockSessionsApi.create.mockResolvedValue(mockSession)
      mockSessionsApi.listActive.mockResolvedValue([mockSession])

      const result = await store.createSession(request)

      expect(result).toEqual(mockSession)
      expect(store.currentSession).toEqual(mockSession)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(mockSessionsApi.create).toHaveBeenCalledWith(request)
      expect(mockSessionsApi.listActive).toHaveBeenCalledWith('test-project')
    })

    it('should set loading state during creation', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      let loadingDuringCall = false
      mockSessionsApi.create.mockImplementation(async () => {
        loadingDuringCall = store.loading
        return mockSession
      })
      mockSessionsApi.listActive.mockResolvedValue([mockSession])

      await store.createSession({ project_name: 'test-project' })

      expect(loadingDuringCall).toBe(true)
      expect(store.loading).toBe(false)
    })

    it('should handle creation errors', async () => {
      const store = useSessionStore()
      const error = new Error('Session creation failed')

      mockSessionsApi.create.mockRejectedValue(error)

      await expect(store.createSession({ project_name: 'test-project' })).rejects.toThrow(
        'Session creation failed'
      )

      expect(store.error).toBe('Session creation failed')
      expect(store.currentSession).toBeNull()
      expect(store.loading).toBe(false)
    })

    it('should handle non-Error creation failures', async () => {
      const store = useSessionStore()

      mockSessionsApi.create.mockRejectedValue('Unknown error')

      await expect(store.createSession({ project_name: 'test-project' })).rejects.toBe('Unknown error')

      expect(store.error).toBe('Failed to create session')
      expect(store.loading).toBe(false)
    })

    it('should refresh active sessions after creation', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      const otherSession: SessionInfo = {
        session_id: 'session-456',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 2,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      mockSessionsApi.create.mockResolvedValue(mockSession)
      mockSessionsApi.listActive.mockResolvedValue([mockSession, otherSession])

      await store.createSession({ project_name: 'test-project' })

      expect(store.activeSessions).toEqual([mockSession, otherSession])
      expect(store.currentSession?.concurrent_sessions).toBe(2)
    })
  })

  describe('refreshSession', () => {
    it('should refresh current session', async () => {
      const store = useSessionStore()
      const initialSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      const updatedSession: SessionInfo = {
        ...initialSession,
        version: 2,
        modified: true,
      }

      store.$patch({ currentSession: initialSession })

      mockSessionsApi.getCurrent.mockResolvedValue(updatedSession)

      const result = await store.refreshSession()

      expect(result).toEqual(updatedSession)
      expect(store.currentSession).toEqual(updatedSession)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should return null if no active session', async () => {
      const store = useSessionStore()

      const result = await store.refreshSession()

      expect(result).toBeNull()
      expect(mockSessionsApi.getCurrent).not.toHaveBeenCalled()
    })

    it('should handle session not found (404)', async () => {
      const store = useSessionStore()
      const initialSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: initialSession })

      const error = {
        response: { status: 404 },
        message: 'Session not found',
      }

      mockSessionsApi.getCurrent.mockRejectedValue(error)

      await expect(store.refreshSession()).rejects.toEqual(error)

      expect(store.currentSession).toBeNull()
      expect(store.error).toBe('Session expired or not found')
      expect(store.loading).toBe(false)
    })

    it('should handle other refresh errors', async () => {
      const store = useSessionStore()
      const initialSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: initialSession })

      const error = new Error('Network error')

      mockSessionsApi.getCurrent.mockRejectedValue(error)

      await expect(store.refreshSession()).rejects.toThrow('Network error')

      expect(store.error).toBe('Network error')
      expect(store.loading).toBe(false)
    })
  })

  describe('closeSession', () => {
    it('should close the current session', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({
        currentSession: mockSession,
        activeSessions: [mockSession],
      })

      mockSessionsApi.close.mockResolvedValue(undefined)

      await store.closeSession()

      expect(store.currentSession).toBeNull()
      expect(store.activeSessions).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(mockSessionsApi.close).toHaveBeenCalled()
    })

    it('should do nothing if no active session', async () => {
      const store = useSessionStore()

      await store.closeSession()

      expect(mockSessionsApi.close).not.toHaveBeenCalled()
      expect(store.loading).toBe(false)
    })

    it('should handle close errors', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: mockSession })

      const error = new Error('Failed to close')

      mockSessionsApi.close.mockRejectedValue(error)

      await expect(store.closeSession()).rejects.toThrow('Failed to close')

      expect(store.error).toBe('Failed to close')
      expect(store.loading).toBe(false)
    })
  })

  describe('refreshActiveSessions', () => {
    it('should refresh active sessions list', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: mockSession })

      const activeSessions = [mockSession]

      mockSessionsApi.listActive.mockResolvedValue(activeSessions)

      await store.refreshActiveSessions()

      expect(store.activeSessions).toEqual(activeSessions)
      expect(mockSessionsApi.listActive).toHaveBeenCalledWith('test-project')
    })

    it('should update concurrent sessions count', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      const otherSession: SessionInfo = {
        session_id: 'session-456',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 2,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: mockSession })

      mockSessionsApi.listActive.mockResolvedValue([mockSession, otherSession])

      await store.refreshActiveSessions()

      expect(store.currentSession?.concurrent_sessions).toBe(2)
    })

    it('should do nothing if no current session', async () => {
      const store = useSessionStore()

      await store.refreshActiveSessions()

      expect(mockSessionsApi.listActive).not.toHaveBeenCalled()
    })

    it('should handle errors silently', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: mockSession })

      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

      mockSessionsApi.listActive.mockRejectedValue(new Error('Network error'))

      await store.refreshActiveSessions()

      expect(consoleError).toHaveBeenCalledWith(
        'Failed to refresh active sessions:',
        expect.any(Error)
      )
      consoleError.mockRestore()
    })
  })

  describe('session modification tracking', () => {
    it('should mark session as modified', () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: mockSession })

      store.markModified()

      expect(store.currentSession?.modified).toBe(true)
      expect(store.isModified).toBe(true)
    })

    it('should handle markModified when no session', () => {
      const store = useSessionStore()

      store.markModified()

      expect(store.currentSession).toBeNull()
    })

    it('should increment version and clear modified flag', () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: true,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: mockSession })

      store.incrementVersion()

      expect(store.currentSession?.version).toBe(2)
      expect(store.currentSession?.modified).toBe(false)
      expect(store.version).toBe(2)
    })

    it('should handle incrementVersion when no session', () => {
      const store = useSessionStore()

      store.incrementVersion()

      expect(store.currentSession).toBeNull()
    })
  })

  describe('version conflict detection', () => {
    it('should detect version conflict', () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: mockSession })

      expect(store.checkVersionConflict(2)).toBe(true)
      expect(store.checkVersionConflict(1)).toBe(false)
    })

    it('should return false when no session', () => {
      const store = useSessionStore()

      expect(store.checkVersionConflict(1)).toBe(false)
    })
  })

  describe('computed properties', () => {
    it('should compute hasActiveSession correctly', () => {
      const store = useSessionStore()

      expect(store.hasActiveSession).toBe(false)

      store.$patch({
        currentSession: {
          session_id: 'session-123',
          project_name: 'test-project',
          version: 1,
          modified: false,
          concurrent_sessions: 1,
          created_at: new Date().toISOString(),
          last_modified: new Date().toISOString(),
        },
      })

      expect(store.hasActiveSession).toBe(true)
    })

    it('should compute hasConcurrentEdits correctly', () => {
      const store = useSessionStore()

      expect(store.hasConcurrentEdits).toBe(false)

      store.$patch({
        currentSession: {
          session_id: 'session-123',
          project_name: 'test-project',
          version: 1,
          modified: false,
          concurrent_sessions: 2,
          created_at: new Date().toISOString(),
          last_modified: new Date().toISOString(),
        },
      })

      expect(store.hasConcurrentEdits).toBe(true)
    })

    it('should compute otherActiveSessions correctly', () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 2,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      const otherSession: SessionInfo = {
        session_id: 'session-456',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 2,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({
        currentSession: mockSession,
        activeSessions: [mockSession, otherSession],
      })

      expect(store.otherActiveSessions).toEqual([otherSession])
    })
  })

  describe('auto-refresh', () => {
    it('should start auto-refresh interval', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: mockSession })
      mockSessionsApi.listActive.mockResolvedValue([mockSession])

      store.startAutoRefresh(1000)

      // Fast-forward time
      await vi.advanceTimersByTimeAsync(1000)

      expect(mockSessionsApi.listActive).toHaveBeenCalledWith('test-project')
    })

    it('should stop auto-refresh interval', () => {
      const store = useSessionStore()

      store.startAutoRefresh(1000)
      store.stopAutoRefresh()

      // Fast-forward time
      vi.advanceTimersByTime(2000)

      expect(mockSessionsApi.listActive).not.toHaveBeenCalled()
    })

    it('should not refresh if no active session', async () => {
      const store = useSessionStore()

      store.startAutoRefresh(1000)

      await vi.advanceTimersByTimeAsync(1000)

      expect(mockSessionsApi.listActive).not.toHaveBeenCalled()
    })

    it('should stop previous interval when starting new one', async () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({ currentSession: mockSession })
      mockSessionsApi.listActive.mockResolvedValue([mockSession])

      store.startAutoRefresh(1000)
      store.startAutoRefresh(2000)

      await vi.advanceTimersByTimeAsync(1000)

      // Should not have been called yet (new interval is 2000ms)
      expect(mockSessionsApi.listActive).not.toHaveBeenCalled()

      await vi.advanceTimersByTimeAsync(1000)

      // Now it should be called
      expect(mockSessionsApi.listActive).toHaveBeenCalledWith('test-project')
    })
  })

  describe('$reset', () => {
    it('should reset all state', () => {
      const store = useSessionStore()
      const mockSession: SessionInfo = {
        session_id: 'session-123',
        project_name: 'test-project',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        created_at: new Date().toISOString(),
        last_modified: new Date().toISOString(),
      }

      store.$patch({
        currentSession: mockSession,
        activeSessions: [mockSession],
        loading: true,
        error: 'Some error',
      })

      store.$reset()

      expect(store.currentSession).toBeNull()
      expect(store.activeSessions).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })
})
