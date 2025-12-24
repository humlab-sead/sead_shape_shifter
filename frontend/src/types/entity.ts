/**
 * TypeScript types for entity configuration.
 */

export type Cardinality = 'one_to_one' | 'many_to_one' | 'one_to_many' | 'many_to_many'
export type JoinType = 'left' | 'inner' | 'outer' | 'right' | 'cross'
export type EntityType = 'data' | 'sql' | 'fixed'

export interface ForeignKeyConstraints {
  cardinality?: Cardinality | null
  allow_unmatched_left?: boolean | null
  allow_unmatched_right?: boolean | null
  allow_row_decrease?: boolean | null
  require_unique_left?: boolean
  require_unique_right?: boolean
  allow_null_keys?: boolean
}

export interface ForeignKeyConfig {
  entity: string
  local_keys: string[]
  remote_keys: string[]
  how: JoinType
  extra_columns?: Record<string, string> | string[] | string | null
  drop_remote_id?: boolean
  constraints?: ForeignKeyConstraints | null
}

export interface UnnestConfig {
  id_vars: string[]
  value_vars: string[]
  var_name: string
  value_name: string
}

export interface FilterConfig {
  type: string
  entity?: string | null
  column?: string | null
  remote_column?: string | null
}

export interface AppendConfig {
  type: 'fixed' | 'sql'
  values?: any[][] | null
  data_source?: string | null
  query?: string | null
}

export interface Entity {
  name: string
  type?: EntityType | null
  source?: string | null
  data_source?: string | null
  query?: string | null
  surrogate_id?: string | null
  keys?: string[]
  columns?: string[]
  extra_columns?: Record<string, any>
  foreign_keys?: ForeignKeyConfig[]
  unnest?: UnnestConfig | null
  filters?: FilterConfig[]
  append?: AppendConfig[]
  depends_on?: string[]
  drop_duplicates?: boolean | string[]
  drop_empty_rows?: boolean | string[]
  check_column_names?: boolean
  values?: any[][] | null
}

// Helper type for entity creation (all optional except name)
export type EntityCreate = Pick<Entity, 'name'> & Partial<Omit<Entity, 'name'>>

// Helper type for entity update (all optional)
export type EntityUpdate = Partial<Entity>
