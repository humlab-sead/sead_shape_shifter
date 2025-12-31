/**
 * Session management types for multi-user configuration editing.
 */

export interface SessionCreateRequest {
  project_name: string
  user_id?: string | null
}

export interface SessionResponse {
  session_id: string
  project_name: string
  user_id: string | null
  loaded_at: string
  last_accessed: string
  modified: boolean
  version: number
  concurrent_sessions: number
}

export interface SessionInfo extends SessionResponse {
  // Computed fields
  isStale?: boolean
  hasConflict?: boolean
}

export interface SessionConflictError extends Error {
  expected_version: number
  current_version: number
  project_name: string
}
