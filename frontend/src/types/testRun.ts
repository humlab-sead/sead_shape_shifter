/**
 * Test Run Types
 *
 * TypeScript types matching the backend test run models.
 */

export enum TestRunStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum OutputFormat {
  PREVIEW = 'preview',
  CSV = 'csv',
  JSON = 'json',
}

export interface TestRunOptions {
  entities?: string[]
  max_rows_per_entity: number
  output_format: OutputFormat
  validate_foreign_keys: boolean
  validate_constraints: boolean
  stop_on_error: boolean
}

export interface ValidationIssue {
  severity: 'error' | 'warning' | 'info'
  entity: string
  issue_type: string
  message: string
  details?: Record<string, any>
}

export interface EntityTestResult {
  entity_name: string
  status: 'success' | 'failed' | 'skipped'
  rows_in: number
  rows_out: number
  execution_time_ms: number
  error_message: string | null
  warnings: string[]
  validation_issues: ValidationIssue[]
  preview_rows: Record<string, any>[] | null
}

export interface TestRunResult {
  run_id: string
  project_name: string
  status: TestRunStatus
  started_at: string
  completed_at: string | null
  total_time_ms: number
  entities_processed: EntityTestResult[]
  entities_total: number
  entities_succeeded: number
  entities_failed: number
  entities_skipped: number
  validation_issues: ValidationIssue[]
  error_message: string | null
  options: TestRunOptions
  current_entity: string | null
  entities_completed: number
}

export interface TestProgress {
  run_id: string
  status: TestRunStatus
  current_entity: string | null
  entities_total: number
  entities_completed: number
  entities_succeeded: number
  entities_failed: number
  entities_skipped: number
  started_at: string
  elapsed_time_ms: number
}

export interface TestRunRequest {
  project_name: string
  options: Partial<TestRunOptions>
}

// Default test run options
export const DEFAULT_TEST_RUN_OPTIONS: TestRunOptions = {
  max_rows_per_entity: 100,
  output_format: OutputFormat.PREVIEW,
  validate_foreign_keys: true,
  validate_constraints: true,
  stop_on_error: false,
}
