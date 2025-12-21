/**
 * Session management API client.
 */

import { apiClient } from './client'
import type { SessionCreateRequest, SessionResponse } from '@/types/session'

/**
 * Create a new editing session for a configuration file.
 */
export async function createSession(
  request: SessionCreateRequest
): Promise<SessionResponse> {
  const response = await apiClient.post<SessionResponse>('/sessions', request)
  return response.data
}

/**
 * Get information about the current session.
 */
export async function getCurrentSession(): Promise<SessionResponse> {
  const response = await apiClient.get<SessionResponse>('/sessions/current')
  return response.data
}

/**
 * Close the current editing session.
 */
export async function closeSession(): Promise<void> {
  await apiClient.delete('/sessions/current')
}

/**
 * List all active sessions for a configuration file.
 */
export async function listActiveSessions(
  configName: string
): Promise<SessionResponse[]> {
  const response = await apiClient.get<SessionResponse[]>(
    `/sessions/${configName}/active`
  )
  return response.data
}

export const sessionsApi = {
  create: createSession,
  getCurrent: getCurrentSession,
  close: closeSession,
  listActive: listActiveSessions,
}
