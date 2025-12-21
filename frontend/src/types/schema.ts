/**
 * Schema Types
 * 
 * TypeScript interfaces for database schema introspection.
 * These mirror the Pydantic models in backend/app/models/data_source.py
 */

/**
 * Metadata about a database table
 */
export interface TableMetadata {
  name: string;
  schema_name?: string | null;
  row_count?: number | null;
  comment?: string | null;
}

/**
 * Metadata about a table column
 */
export interface ColumnMetadata {
  name: string;
  data_type: string;
  nullable: boolean;
  default?: string | null;
  is_primary_key: boolean;
  max_length?: number | null;
  comment?: string | null;
}

/**
 * Foreign key relationship metadata
 */
export interface ForeignKeyMetadata {
  name?: string | null;
  column: string;
  referenced_table: string;
  referenced_column: string;
  referenced_schema?: string | null;
}

/**
 * Index metadata
 */
export interface IndexMetadata {
  name: string;
  columns: string[];
  is_unique: boolean;
  is_primary: boolean;
}

/**
 * Complete table schema including columns, keys, and indexes
 */
export interface TableSchema {
  table_name: string;
  schema?: string | null;
  columns: ColumnMetadata[];
  primary_keys: string[];
  foreign_keys?: ForeignKeyMetadata[];
  indexes?: IndexMetadata[];
  row_count?: number | null;
  comment?: string | null;
}

/**
 * Table data preview response
 */
export interface PreviewData {
  columns: string[];
  rows: Record<string, any>[];
  total_rows: number;
  limit: number;
  offset: number;
}
/**
 * Type mapping suggestion for a column
 */
export interface TypeMapping {
  sql_type: string;
  suggested_type: string;
  confidence: number;  // 0.0 to 1.0
  reason: string;
  alternatives: string[];
}
/**
 * Query parameters for listing tables
 */
export interface ListTablesParams {
  schema?: string;
}

/**
 * Query parameters for getting table schema
 */
export interface GetTableSchemaParams {
  schema?: string;
}

/**
 * Query parameters for previewing table data
 */
export interface PreviewTableDataParams {
  schema?: string;
  limit?: number;
  offset?: number;
}

/**
 * Helper function to format data type display
 */
export function formatDataType(column: ColumnMetadata): string {
  let type = column.data_type;
  
  if (column.max_length !== null && column.max_length !== undefined) {
    type += `(${column.max_length})`;
  }
  
  if (!column.nullable) {
    type += ' NOT NULL';
  }
  
  return type;
}

/**
 * Helper function to get column icon based on properties
 */
export function getColumnIcon(column: ColumnMetadata): string {
  if (column.is_primary_key) {
    return 'mdi-key';
  }
  
  // Map common data types to icons
  const lowerType = column.data_type.toLowerCase();
  
  if (lowerType.includes('int') || lowerType.includes('numeric') || 
      lowerType.includes('decimal') || lowerType.includes('float') ||
      lowerType.includes('double') || lowerType.includes('real')) {
    return 'mdi-numeric';
  }
  
  if (lowerType.includes('char') || lowerType.includes('text') || 
      lowerType.includes('varchar') || lowerType.includes('string')) {
    return 'mdi-format-text';
  }
  
  if (lowerType.includes('date') || lowerType.includes('time') || 
      lowerType.includes('timestamp')) {
    return 'mdi-calendar-clock';
  }
  
  if (lowerType.includes('bool')) {
    return 'mdi-checkbox-marked-outline';
  }
  
  if (lowerType.includes('json') || lowerType.includes('jsonb')) {
    return 'mdi-code-json';
  }
  
  if (lowerType.includes('uuid')) {
    return 'mdi-identifier';
  }
  
  if (lowerType.includes('array')) {
    return 'mdi-code-brackets';
  }
  
  return 'mdi-database-outline';
}

/**
 * Helper function to get column color based on properties
 */
export function getColumnColor(column: ColumnMetadata): string {
  if (column.is_primary_key) {
    return 'amber';
  }
  
  if (!column.nullable) {
    return 'blue';
  }
  
  return 'grey';
}

/**
 * Helper function to format row count for display
 */
export function formatRowCount(count: number | null | undefined): string {
  if (count === null || count === undefined) {
    return 'Unknown';
  }
  
  if (count < 1000) {
    return count.toString();
  }
  
  if (count < 1000000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  
  return `${(count / 1000000).toFixed(1)}M`;
}

/**
 * Helper function to get table icon
 */
export function getTableIcon(): string {
  // Could be extended with table type detection
  return 'mdi-table';
}

/**
 * Helper function to validate table name
 */
export function isValidTableName(name: string): boolean {
  return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
}

/**
 * Helper function to escape SQL identifier
 */
export function escapeSqlIdentifier(identifier: string): string {
  return `"${identifier.replace(/"/g, '""')}"`;
}
