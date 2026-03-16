/**
 * Query execution API client.
 */

import { apiClient } from './client'
import type { QueryResult, QueryValidation, QueryExecution } from '@/types/query'

export const queryApi = {
  /**
   * Execute a SQL query against a data source.
   */
  async executeQuery(dataSourceName: string, execution: QueryExecution): Promise<QueryResult> {
    const response = await apiClient.post<QueryResult>(`/data-sources/${dataSourceName}/query/execute`, execution)
    return response.data
  },

  /**
   * Validate a SQL query without executing it.
   */
  async validateQuery(dataSourceName: string, execution: QueryExecution): Promise<QueryValidation> {
    const response = await apiClient.post<QueryValidation>(`/data-sources/${dataSourceName}/query/validate`, execution)
    return response.data
  },

  /**
   * Introspect column names from a SQL query.
   */
  async introspectQueryColumns(dataSourceName: string, query: string): Promise<string[]> {
    const response = await apiClient.post<{ columns: string[] }>(
      `/data-sources/${dataSourceName}/query/columns`,
      { query }
    )
    return response.data.columns
  },

}
