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
}

export interface DependencyGraph {
  nodes: DependencyNode[]
  edges: [string, string][]
  has_cycles: boolean
  cycles: string[][]
  topological_order: string[] | null
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
