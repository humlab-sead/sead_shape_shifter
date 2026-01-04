/**
 * Graph data adapter - transforms backend DependencyGraph format to Cytoscape elements
 */

import type { ElementDefinition } from 'cytoscape'
import type { DependencyGraph } from '@/types'

export interface GraphAdapterOptions {
  /**
   * Cycles to highlight
   */
  cycles?: string[][]

  /**
   * Whether to show node labels
   */
  showNodeLabels?: boolean

  /**
   * Whether to show edge labels
   */
  showEdgeLabels?: boolean

  /**
   * Whether to highlight cycle nodes and edges
   */
  highlightCycles?: boolean

  /**
   * Whether to show source nodes (data sources, tables)
   */
  showSourceNodes?: boolean
}

/**
 * Check if an edge is part of any cycle
 */
function isEdgeInCycle(source: string, target: string, cycles: string[][]): boolean {
  return cycles.some((cycle) => {
    const sourceIndex = cycle.indexOf(source)
    const targetIndex = cycle.indexOf(target)

    if (sourceIndex === -1 || targetIndex === -1) return false

    // Check if edge connects consecutive nodes in the cycle
    return targetIndex === sourceIndex + 1 || (sourceIndex === cycle.length - 1 && targetIndex === 0)
  })
}

/**
 * Check if a node is part of any cycle
 */
function isNodeInCycle(nodeId: string, cycles: string[][]): boolean {
  return cycles.some((cycle) => cycle.includes(nodeId))
}

/**
 * Extract label from source node name (e.g., "source:my_db" -> "my_db")
 */
function extractSourceLabel(name: string): string {
  const parts = name.split(':')
  return parts[parts.length - 1] || name
}

/**
 * Convert backend DependencyGraph to Cytoscape ElementDefinition array
 */
export function toCytoscapeElements(
  graph: DependencyGraph | null,
  options: GraphAdapterOptions = {}
): ElementDefinition[] {
  if (!graph) return []

  const { cycles = [], showNodeLabels = true, showEdgeLabels = true, highlightCycles = false, showSourceNodes = false } = options

  // Convert entity nodes
  const nodes: ElementDefinition[] = graph.nodes.map((node) => {
    const classes: string[] = []

    if (!showNodeLabels) {
      classes.push('hide-label')
    }

    if (highlightCycles && isNodeInCycle(node.name, cycles)) {
      classes.push('in-cycle')
    }

    return {
      data: {
        id: node.name,
        label: node.name,
        type: node.type,
        depth: node.depth,
        dependencies: node.depends_on.length,
        dependsOn: node.depends_on,
        nodeCategory: 'entity',
      },
      classes,
    }
  })

  // Convert source nodes (conditionally)
  const sourceNodes: ElementDefinition[] = showSourceNodes && graph.source_nodes
    ? graph.source_nodes.map((sourceNode) => {
        const classes = ['source-node', `source-${sourceNode.type}`]

        if (!showNodeLabels) {
          classes.push('hide-label')
        }

        return {
          data: {
            id: sourceNode.name,
            label: extractSourceLabel(sourceNode.name),
            nodeCategory: 'source',
            sourceType: sourceNode.type,
            sourceCategory: sourceNode.source_type,
            metadata: sourceNode.metadata,
          },
          classes,
        }
      })
    : []

  // Convert edges
  const edges: ElementDefinition[] = graph.edges.map((edge, index) => {
    const classes: string[] = []

    if (!showEdgeLabels) {
      classes.push('hide-label')
    }

    if (highlightCycles && isEdgeInCycle(edge.source, edge.target, cycles)) {
      classes.push('cycle-edge')
    }

    return {
      data: {
        id: `edge-${edge.source}-${edge.target}-${index}`,
        source: edge.source,
        target: edge.target,
        label: edge.label || '',
      },
      classes,
    }
  })

  // Convert source edges (conditionally)
  const sourceEdges: ElementDefinition[] = showSourceNodes && graph.source_edges
    ? graph.source_edges.map((edge, index) => {
        const classes = ['source-edge']

        if (!showEdgeLabels) {
          classes.push('hide-label')
        }

        return {
          data: {
            id: `source-edge-${edge.source}-${edge.target}-${index}`,
            source: edge.source,
            target: edge.target,
            label: edge.label || '',
          },
          classes,
        }
      })
    : []

  return [...nodes, ...sourceNodes, ...edges, ...sourceEdges]
}

/**
 * Get layout configuration for Cytoscape
 */
export function getLayoutConfig(layoutType: 'hierarchical' | 'force', animate: boolean = true) {
  if (layoutType === 'hierarchical') {
    return {
      name: 'dagre',
      rankDir: 'TB', // Top to bottom
      nodeSep: 60,
      rankSep: 120,
      animate,
      animationDuration: 500,
      fit: true,
      padding: 50,
    }
  } else {
    return {
      name: 'cose-bilkent',
      quality: 'default',
      nodeDimensionsIncludeLabels: true,
      randomize: false,
      animate,
      animationDuration: 1000,
      fit: true,
      padding: 50,
      idealEdgeLength: 100,
      nodeRepulsion: 4500,
      edgeElasticity: 0.45,
      gravity: 0.25,
      gravityRange: 3.8,
    }
  }
}

/**
 * Extract node information for details panel
 */
export function getNodeInfo(nodeId: string, graph: DependencyGraph | null) {
  if (!graph) return null

  const node = graph.nodes.find((n) => n.name === nodeId)
  if (!node) return null

  // Find topological order
  const topologicalOrder = graph.topological_order?.indexOf(nodeId) ?? null

  // Find dependents (nodes that depend on this node)
  const dependents = graph.nodes.filter((n) => n.depends_on.includes(nodeId)).map((n) => n.name)

  return {
    id: nodeId,
    label: nodeId,
    depth: node.depth,
    dependencies: node.depends_on,
    dependents,
    topologicalOrder: topologicalOrder !== null ? topologicalOrder + 1 : null,
  }
}
