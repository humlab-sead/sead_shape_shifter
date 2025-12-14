/**
 * Query execution types for the Shape Shifter Configuration Editor.
 */

export interface QueryResult {
  rows: Record<string, any>[];
  columns: string[];
  row_count: number;
  execution_time_ms: number;
  is_truncated: boolean;
  total_rows: number | null;
}

export interface QueryValidation {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  statement_type: string | null;
  tables: string[];
}

export interface QueryPlan {
  plan_text: string;
  estimated_cost: number | null;
  estimated_rows: number | null;
}

export interface QueryExecution {
  query: string;
  limit?: number;
  timeout?: number;
}
