/**
 * Schema API Client
 * 
 * API client for database schema introspection endpoints.
 * Provides methods to list tables, get schema details, and preview data.
 */

import { apiClient } from './client';
import type {
  TableMetadata,
  TableSchema,
  PreviewData,
  TypeMapping,
  ListTablesParams,
  GetTableSchemaParams,
  PreviewTableDataParams,
} from '@/types/schema';

/**
 * Schema API endpoints
 */
export const schemaApi = {
  /**
   * List all tables in a data source
   * 
   * @param dataSourceName - Name of the data source
   * @param params - Optional query parameters (schema filter for PostgreSQL)
   * @returns Promise with array of table metadata
   */
  async listTables(
    dataSourceName: string,
    params?: ListTablesParams
  ): Promise<TableMetadata[]> {
    const response = await apiClient.get<TableMetadata[]>(
      `/data-sources/${encodeURIComponent(dataSourceName)}/tables`,
      { params }
    );
    return response.data;
  },

  /**
   * Get detailed schema for a specific table
   * 
   * @param dataSourceName - Name of the data source
   * @param tableName - Name of the table
   * @param params - Optional query parameters (schema filter for PostgreSQL)
   * @returns Promise with table schema details
   */
  async getTableSchema(
    dataSourceName: string,
    tableName: string,
    params?: GetTableSchemaParams
  ): Promise<TableSchema> {
    const response = await apiClient.get<TableSchema>(
      `/data-sources/${encodeURIComponent(dataSourceName)}/tables/${encodeURIComponent(tableName)}/schema`,
      { params }
    );
    return response.data;
  },

  /**
   * Preview table data with pagination
   * 
   * @param dataSourceName - Name of the data source
   * @param tableName - Name of the table
   * @param params - Optional query parameters (schema, limit, offset)
   * @returns Promise with preview data
   */
  async previewTableData(
    dataSourceName: string,
    tableName: string,
    params?: PreviewTableDataParams
  ): Promise<PreviewData> {
    const response = await apiClient.get<PreviewData>(
      `/data-sources/${encodeURIComponent(dataSourceName)}/tables/${encodeURIComponent(tableName)}/preview`,
      { params }
    );
    return response.data;
  },

  /**
   * Invalidate cached schema data for a data source
   * 
   * @param dataSourceName - Name of the data source
   * @returns Promise that resolves when cache is invalidated
   */
  async invalidateCache(dataSourceName: string): Promise<void> {
    await apiClient.post(
      `/data-sources/${encodeURIComponent(dataSourceName)}/cache/invalidate`
    );
  },

  /**
   * Get type mapping suggestions for all columns in a table
   * 
   * @param dataSourceName - Name of the data source
   * @param tableName - Name of the table
   * @param params - Optional query parameters (schema filter for PostgreSQL)
   * @returns Promise with dictionary of column name -> type mapping
   */
  async getTypeMappings(
    dataSourceName: string,
    tableName: string,
    params?: GetTableSchemaParams
  ): Promise<Record<string, TypeMapping>> {
    const response = await apiClient.get<Record<string, TypeMapping>>(
      `/data-sources/${encodeURIComponent(dataSourceName)}/tables/${encodeURIComponent(tableName)}/type-mappings`,
      { params }
    );
    return response.data;
  },
};

export default schemaApi;
