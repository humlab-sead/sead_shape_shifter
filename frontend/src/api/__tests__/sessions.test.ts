import { describe, it, expect, vi, beforeEach } from 'vitest'
import { sessionsApi, createSession, getCurrentSession, closeSession, listActiveSessions } from '../sessions'
import { apiClient } from '../client'
import type { SessionCreateRequest, SessionResponse } from '@/types/session'

// Mock the API client
vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockApiClient = apiClient as any

describe('sessions API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('createSession', () => {
    it('should create a new session', async () => {
      const request: SessionCreateRequest = {
        project_name: 'test-project',
      }

      const mockResponse: SessionResponse = {
        session_id: 'session-123',
        project_name: 'test-project',
        user_id: null,
        loaded_at: '2024-01-01T00:00:00Z',
        last_accessed: '2024-01-01T00:00:00Z',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
      }

      mockApiClient.post.mockResolvedValue({ data: mockResponse })

      const result = await createSession(request)

      expect(result).toEqual(mockResponse)
      expect(mockApiClient.post).toHaveBeenCalledWith('/sessions', request)
    })

    it('should handle creation errors', async () => {
      const request: SessionCreateRequest = {
        project_name: 'test-project',
      }

      const error = new Error('Session creation failed')

      mockApiClient.post.mockRejectedValue(error)

      await expect(createSession(request)).rejects.toThrow('Session creation failed')
    })

    it('should pass through all request properties', async () => {
      const request: SessionCreateRequest = {
        project_name: 'my-project',
      }

      const mockResponse: SessionResponse = {
        session_id: 'session-456',
        project_name: 'my-project',
        user_id: null,
        loaded_at: '2024-01-01T00:00:00Z',
        last_accessed: '2024-01-01T00:00:00Z',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
      }

      mockApiClient.post.mockResolvedValue({ data: mockResponse })

      await createSession(request)

      expect(mockApiClient.post).toHaveBeenCalledWith('/sessions', request)
    })
  })

  describe('getCurrentSession', () => {
    it('should get current session', async () => {
      const mockResponse: SessionResponse = {
        session_id: 'session-123',
        project_name: 'test-project',
        user_id: null,
        loaded_at: '2024-01-01T00:00:00Z',
        last_accessed: '2024-01-01T01:00:00Z',
        version: 2,
        modified: true,
        concurrent_sessions: 1,
      }

      mockApiClient.get.mockResolvedValue({ data: mockResponse })

      const result = await getCurrentSession()

      expect(result).toEqual(mockResponse)
      expect(mockApiClient.get).toHaveBeenCalledWith('/sessions/current')
    })

    it('should handle session not found (404)', async () => {
      const error = {
        response: { status: 404 },
        message: 'Session not found',
      }

      mockApiClient.get.mockRejectedValue(error)

      await expect(getCurrentSession()).rejects.toEqual(error)
    })

    it('should handle network errors', async () => {
      const error = new Error('Network error')

      mockApiClient.get.mockRejectedValue(error)

      await expect(getCurrentSession()).rejects.toThrow('Network error')
    })

    it('should return session with updated version', async () => {
      const mockResponse: SessionResponse = {
        session_id: 'session-123',
        project_name: 'test-project',
        user_id: null,
        loaded_at: '2024-01-01T00:00:00Z',
        last_accessed: '2024-01-01T02:00:00Z',
        version: 5,
        modified: false,
        concurrent_sessions: 2,
      }

      mockApiClient.get.mockResolvedValue({ data: mockResponse })

      const result = await getCurrentSession()

      expect(result.version).toBe(5)
      expect(result.concurrent_sessions).toBe(2)
    })
  })

  describe('closeSession', () => {
    it('should close current session', async () => {
      mockApiClient.delete.mockResolvedValue({ data: null })

      await closeSession()

      expect(mockApiClient.delete).toHaveBeenCalledWith('/sessions/current')
    })

    it('should not return a value', async () => {
      mockApiClient.delete.mockResolvedValue({ data: null })

      const result = await closeSession()

      expect(result).toBeUndefined()
    })

    it('should handle close errors', async () => {
      const error = new Error('Failed to close session')

      mockApiClient.delete.mockRejectedValue(error)

      await expect(closeSession()).rejects.toThrow('Failed to close session')
    })

    it('should handle session not found when closing', async () => {
      const error = {
        response: { status: 404 },
        message: 'Session not found',
      }

      mockApiClient.delete.mockRejectedValue(error)

      await expect(closeSession()).rejects.toEqual(error)
    })

    it('should handle unauthorized errors', async () => {
      const error = {
        response: { status: 401 },
        message: 'Unauthorized',
      }

      mockApiClient.delete.mockRejectedValue(error)

      await expect(closeSession()).rejects.toEqual(error)
    })
  })

  describe('listActiveSessions', () => {
    it('should list active sessions for a project', async () => {
      const mockSessions: SessionResponse[] = [
        {
          session_id: 'session-123',
          project_name: 'test-project',
          user_id: null,
          loaded_at: '2024-01-01T00:00:00Z',
          last_accessed: '2024-01-01T00:00:00Z',
          version: 1,
          modified: false,
          concurrent_sessions: 2,
        },
        {
          session_id: 'session-456',
          project_name: 'test-project',
          user_id: null,
          loaded_at: '2024-01-01T00:05:00Z',
          last_accessed: '2024-01-01T00:10:00Z',
          version: 1,
          modified: true,
          concurrent_sessions: 2,
        },
      ]

      mockApiClient.get.mockResolvedValue({ data: mockSessions })

      const result = await listActiveSessions('test-project')

      expect(result).toEqual(mockSessions)
      expect(mockApiClient.get).toHaveBeenCalledWith('/sessions/test-project/active')
    })

    it('should return empty array when no active sessions', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] })

      const result = await listActiveSessions('test-project')

      expect(result).toEqual([])
    })

    it('should handle project names with spaces', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] })

      await listActiveSessions('my project')

      expect(mockApiClient.get).toHaveBeenCalledWith('/sessions/my project/active')
    })

    it('should handle special characters in project names', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] })

      await listActiveSessions('project-with-dashes_and_underscores')

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/sessions/project-with-dashes_and_underscores/active'
      )
    })

    it('should handle errors when listing sessions', async () => {
      const error = new Error('Failed to list sessions')

      mockApiClient.get.mockRejectedValue(error)

      await expect(listActiveSessions('test-project')).rejects.toThrow('Failed to list sessions')
    })

    it('should handle 404 for non-existent project', async () => {
      const error = {
        response: { status: 404 },
        message: 'Project not found',
      }

      mockApiClient.get.mockRejectedValue(error)

      await expect(listActiveSessions('nonexistent')).rejects.toEqual(error)
    })
  })

  describe('sessionsApi object', () => {
    it('should export all functions via sessionsApi object', () => {
      expect(sessionsApi.create).toBe(createSession)
      expect(sessionsApi.getCurrent).toBe(getCurrentSession)
      expect(sessionsApi.close).toBe(closeSession)
      expect(sessionsApi.listActive).toBe(listActiveSessions)
    })

    it('should allow calling methods via sessionsApi', async () => {
      const mockResponse: SessionResponse = {
        session_id: 'session-123',
        project_name: 'test-project',
        user_id: null,
        loaded_at: '2024-01-01T00:00:00Z',
        last_accessed: '2024-01-01T00:00:00Z',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
      }

      mockApiClient.post.mockResolvedValue({ data: mockResponse })

      const result = await sessionsApi.create({ project_name: 'test-project' })

      expect(result).toEqual(mockResponse)
    })
  })

  describe('concurrent session scenarios', () => {
    it('should handle multiple concurrent sessions', async () => {
      const mockSessions: SessionResponse[] = [
        {
          session_id: 'session-1',
          project_name: 'test-project',
          user_id: null,
          loaded_at: '2024-01-01T00:00:00Z',
          last_accessed: '2024-01-01T00:00:00Z',
          version: 1,
          modified: false,
          concurrent_sessions: 3,
        },
        {
          session_id: 'session-2',
          project_name: 'test-project',
          user_id: null,
          loaded_at: '2024-01-01T00:01:00Z',
          last_accessed: '2024-01-01T00:05:00Z',
          version: 1,
          modified: true,
          concurrent_sessions: 3,
        },
        {
          session_id: 'session-3',
          project_name: 'test-project',
          user_id: null,
          loaded_at: '2024-01-01T00:02:00Z',
          last_accessed: '2024-01-01T00:06:00Z',
          version: 2,
          modified: false,
          concurrent_sessions: 3,
        },
      ]

      mockApiClient.get.mockResolvedValue({ data: mockSessions })

      const result = await listActiveSessions('test-project')

      expect(result.length).toBe(3)
      expect(result.every((s) => s.concurrent_sessions === 3)).toBe(true)
    })

    it('should handle session version conflicts', async () => {
      const mockSession: SessionResponse = {
        session_id: 'session-123',
        project_name: 'test-project',
        user_id: null,
        loaded_at: '2024-01-01T00:00:00Z',
        last_accessed: '2024-01-01T00:10:00Z',
        version: 5,
        modified: false,
        concurrent_sessions: 2,
      }

      mockApiClient.get.mockResolvedValue({ data: mockSession })

      const result = await getCurrentSession()

      expect(result.version).toBe(5)
      expect(result.concurrent_sessions).toBe(2)
    })
  })

  describe('error response handling', () => {
    it('should handle 400 bad request', async () => {
      const error = {
        response: {
          status: 400,
          data: { detail: 'Invalid project name' },
        },
        message: 'Bad request',
      }

      mockApiClient.post.mockRejectedValue(error)

      await expect(createSession({ project_name: '' })).rejects.toEqual(error)
    })

    it('should handle 409 conflict', async () => {
      const error = {
        response: {
          status: 409,
          data: { detail: 'Session already exists' },
        },
        message: 'Conflict',
      }

      mockApiClient.post.mockRejectedValue(error)

      await expect(createSession({ project_name: 'test-project' })).rejects.toEqual(error)
    })

    it('should handle 500 internal server error', async () => {
      const error = {
        response: { status: 500 },
        message: 'Internal server error',
      }

      mockApiClient.get.mockRejectedValue(error)

      await expect(getCurrentSession()).rejects.toEqual(error)
    })

    it('should handle timeout errors', async () => {
      const error = {
        code: 'ECONNABORTED',
        message: 'Request timeout',
      }

      mockApiClient.delete.mockRejectedValue(error)

      await expect(closeSession()).rejects.toEqual(error)
    })
  })

  describe('edge cases', () => {
    it('should handle empty project name', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] })

      await listActiveSessions('')

      expect(mockApiClient.get).toHaveBeenCalledWith('/sessions//active')
    })

    it('should handle very long project names', async () => {
      const longName = 'a'.repeat(200)

      mockApiClient.get.mockResolvedValue({ data: [] })

      await listActiveSessions(longName)

      expect(mockApiClient.get).toHaveBeenCalledWith(`/sessions/${longName}/active`)
    })

    it('should handle Unicode project names', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] })

      await listActiveSessions('プロジェクト')

      expect(mockApiClient.get).toHaveBeenCalledWith('/sessions/プロジェクト/active')
    })

    it('should handle session response with extra fields', async () => {
      const mockResponse: any = {
        session_id: 'session-123',
        project_name: 'test-project',
        user_id: null,
        loaded_at: '2024-01-01T00:00:00Z',
        last_accessed: '2024-01-01T00:00:00Z',
        version: 1,
        modified: false,
        concurrent_sessions: 1,
        extra_field: 'should be ignored',
      }

      mockApiClient.get.mockResolvedValue({ data: mockResponse })

      const result = await getCurrentSession()

      expect(result).toEqual(mockResponse)
    })
  })
})
