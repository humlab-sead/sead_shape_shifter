/**
 * TypeScript types for project.
 */

import type { Entity } from './entity'

export interface ProjectMetadata {
  name: string
  description?: string | null
  version?: string | null
  file_path?: string | null
  entity_count: number
  created_at?: string | null
  modified_at?: string | null
  is_valid?: boolean
  default_entity?: string | null
}

export interface Project {
  entities: Record<string, Entity>
  options?: Record<string, any>
  metadata?: ProjectMetadata | null
}

// Helper types for API operations
export interface ProjectListItem {
  name: string
  entity_count: number
  modified_at?: string | null
  is_valid?: boolean
}

export interface ProjectCreateRequest {
  name: string
  entities?: Record<string, Entity>
  options?: Record<string, any>
}

export interface ProjectLoadRequest {
  file_path: string
}

export interface ProjectSaveRequest {
  file_path?: string
  create_backup?: boolean
}
