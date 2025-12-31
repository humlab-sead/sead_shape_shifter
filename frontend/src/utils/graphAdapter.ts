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
  showLabels?: boolean

  /**
   * Whether to highlight cycle nodes and edges
   */
  highlightCycles?: boolean
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
 * Convert backend DependencyGraph to Cytoscape ElementDefinition array
 */
export function toCytoscapeElements(
  graph: DependencyGraph | null,
  options: GraphAdapterOptions = {}
): ElementDefinition[] {
  if (!graph) return []

  const { cycles = [], showLabels = true, highlightCycles = false } = options

  // Convert nodes
  const nodes: ElementDefinition[] = graph.nodes.map((node) => {
    const classes: string[] = []

    if (!showLabels) {
      classes.push('hide-label')
    }

    if (highlightCycles && isNodeInCycle(node.name, cycles)) {
      classes.push('in-cycle')
    }

    return {
      data: {
        id: node.name,
        label: node.name,
        depth: node.depth,
        dependencies: node.depends_on.length,
        dependsOn: node.depends_on,
      },
      classes,
    }
  })

  // Convert edges
  const edges: ElementDefinition[] = graph.edges.map(([source, target], index) => {
    const classes: string[] = []

    if (highlightCycles && isEdgeInCycle(source, target, cycles)) {
      classes.push('cycle-edge')
    }

    return {
      data: {
        id: `edge-${source}-${target}-${index}`,
        source,
        target,
      },
      classes,
    }
  })

  return [...nodes, ...edges]
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
