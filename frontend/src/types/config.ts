/**
 * TypeScript types for configuration.
 */

import type { Entity } from './entity'

export interface ConfigMetadata {
  name: string
  file_path?: string | null
  entity_count: number
  created_at?: string | null
  modified_at?: string | null
  is_valid?: boolean
}

export interface Configuration {
  entities: Record<string, Entity>
  options?: Record<string, any>
  metadata?: ConfigMetadata | null
}

// Helper types for API operations
export interface ConfigurationListItem {
  name: string
  entity_count: number
  modified_at?: string | null
  is_valid?: boolean
}

export interface ConfigurationCreateRequest {
  name: string
  entities?: Record<string, Entity>
  options?: Record<string, any>
}

export interface ConfigurationLoadRequest {
  file_path: string
}

export interface ConfigurationSaveRequest {
  file_path?: string
  create_backup?: boolean
}
