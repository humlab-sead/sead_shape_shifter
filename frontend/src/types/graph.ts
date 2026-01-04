/**
 * TypeScript type definitions for dependency graph.
 */

export interface GraphNode {
  id: string
  label: string
  type?: 'data' | 'sql' | 'fixed'
  status?: 'valid' | 'warning' | 'error'
  topological_order?: number
  data?: any
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type?: 'dependency' | 'foreign_key'
  label?: string
  data?: any
}

// Backend API types
export interface DependencyNode {
  name: string
  depends_on: string[]
  depth: number
  type?: 'data' | 'sql' | 'fixed'
}

export interface DependencyEdge {
  source: string
  target: string
  local_keys?: string[]
  remote_keys?: string[]
  label?: string
}

export interface DependencyGraph {
  nodes: DependencyNode[]
  edges: DependencyEdge[]
  has_cycles: boolean
  cycles: string[][]
  topological_order: string[] | null
  source_nodes?: SourceNode[]
  source_edges?: DependencyEdge[]
}

export interface SourceNode {
  name: string
  source_type: string
  type: 'datasource' | 'table' | 'file'
  metadata?: Record<string, any>
}

export interface CircularDependencyCheck {
  has_cycles: boolean
  cycles: string[][]
  cycle_count: number
}

// UI-specific types
export interface CircularDependency {
  cycle: string[]
  message: string
}

export interface DependencyCheckResult {
  has_cycles: boolean
  cycles: CircularDependency[]
}
