/**
 * TypeScript types for data source configuration.
 */

export type DataSourceType = 'postgresql' | 'postgres' | 'access' | 'ucanaccess' | 'sqlite' | 'csv'

export interface DataSourceConfig {
  name: string
  driver: DataSourceType
  host?: string | null
  port?: number | null
  database?: string | null
  dbname?: string | null
  username?: string | null
  password?: string | null
  filename?: string | null
  file_path?: string | null
  connection_string?: string | null
  options?: Record<string, unknown> | null
  description?: string | null
}

export interface DataSourceTestResult {
  success: boolean
  message: string
  connection_time_ms: number
  metadata?: Record<string, unknown> | null
}

export interface DataSourceStatus {
  name: string
  is_connected: boolean
  last_test_result: DataSourceTestResult | null
  in_use_by_entities: string[]
}

export interface TableMetadata {
  name: string
  schema_name?: string | null
  row_count?: number | null
  comment?: string | null
}

export interface ColumnMetadata {
  name: string
  data_type: string
  nullable: boolean
  default?: string | null
  is_primary_key: boolean
  max_length?: number | null
}

export interface TableSchema {
  table_name: string
  columns: ColumnMetadata[]
  primary_keys: string[]
  indexes?: string[] | null
  row_count?: number | null
}

export interface ForeignKeyMetadata {
  column: string
  referenced_table: string
  referenced_column: string
  constraint_name?: string | null
}

/**
 * Form data for creating/editing data sources
 */
export interface DataSourceFormData {
  name: string
  driver: DataSourceType
  host: string
  port: number
  database: string
  username: string
  password: string
  filename: string
  description: string
  options: Record<string, unknown>
}

/**
 * Helper to get default form values
 */
export function getDefaultDataSourceForm(): DataSourceFormData {
  return {
    name: '',
    driver: 'postgresql',
    host: 'localhost',
    port: 5432,
    database: '',
    username: '',
    password: '',
    filename: '',
    description: '',
    options: {},
  }
}

/**
 * Check if data source is a database type
 */
export function isDatabaseSource(driver: DataSourceType): boolean {
  return ['postgresql', 'postgres', 'access', 'ucanaccess', 'sqlite'].includes(driver)
}

/**
 * Check if data source is a file type
 */
export function isFileSource(driver: DataSourceType): boolean {
  return driver === 'csv'
}

/**
 * Get friendly name for driver
 */
export function getDriverDisplayName(driver: DataSourceType): string {
  const names: Record<DataSourceType, string> = {
    postgresql: 'PostgreSQL',
    postgres: 'PostgreSQL',
    access: 'MS Access',
    ucanaccess: 'MS Access',
    sqlite: 'SQLite',
    csv: 'CSV File',
  }
  return names[driver] || driver
}

/**
 * Get icon for driver type
 */
export function getDriverIcon(driver: DataSourceType): string {
  const icons: Record<string, string> = {
    postgresql: 'mdi-database',
    postgres: 'mdi-database',
    access: 'mdi-microsoft-access',
    ucanaccess: 'mdi-microsoft-access',
    sqlite: 'mdi-database',
    csv: 'mdi-file-delimited',
  }
  return icons[driver] || 'mdi-database'
}
