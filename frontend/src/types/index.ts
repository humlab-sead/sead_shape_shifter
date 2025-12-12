/**
 * Common TypeScript type exports.
 */

// Re-export all types for convenient imports
export * from './entity'
export * from './config'
export * from './validation'
export * from './graph'

// Common utility types
export interface ApiResponse<T = any> {
  data: T
  message?: string
  timestamp: string
}

export interface ApiError {
  detail: string
  status_code: number
  timestamp: string
}

export interface PaginationParams {
  page?: number
  per_page?: number
  sort?: string
  order?: 'asc' | 'desc'
}

export interface PaginatedResponse<T = any> {
  items: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}
