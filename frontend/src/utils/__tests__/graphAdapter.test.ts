/**
 * Unit tests for graph adapter utilities
 */
import { describe, it, expect } from 'vitest'
import { toCytoscapeElements, getLayoutConfig, getNodeInfo } from '../graphAdapter'
import type { DependencyGraph } from '@/types'

describe('graphAdapter', () => {
  describe('toCytoscapeElements', () => {
    it('should handle null graph', () => {
      const elements = toCytoscapeElements(null)
      expect(elements).toEqual([])
    })

    it('should convert empty graph', () => {
      const graph: DependencyGraph = {
        nodes: [],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: null,
      }

      const elements = toCytoscapeElements(graph)
      expect(elements).toEqual([])
    })

    it('should convert nodes without edges', () => {
      const graph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: [], depth: 0 },
          { name: 'entity2', depends_on: [], depth: 0 },
        ],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: ['entity1', 'entity2'],
      }

      const elements = toCytoscapeElements(graph)
      expect(elements).toHaveLength(2)

      // Check node structure
      expect(elements[0]).toHaveProperty('data')
      expect(elements[0]?.data).toMatchObject({
        id: 'entity1',
        label: 'entity1',
        depth: 0,
        dependencies: 0,
        dependsOn: [],
      })
    })

    it('should convert nodes and edges', () => {
      const graph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: [], depth: 0 },
          { name: 'entity2', depends_on: ['entity1'], depth: 1 },
          { name: 'entity3', depends_on: ['entity2'], depth: 2 },
        ],
        edges: [
          ['entity1', 'entity2'],
          ['entity2', 'entity3'],
        ],
        has_cycles: false,
        cycles: [],
        topological_order: ['entity1', 'entity2', 'entity3'],
      }

      const elements = toCytoscapeElements(graph)
      expect(elements).toHaveLength(5) // 3 nodes + 2 edges

      // Nodes come first
      expect(elements[0]?.data.id).toBe('entity1')
      expect(elements[1]?.data.id).toBe('entity2')
      expect(elements[2]?.data.id).toBe('entity3')

      // Edges come after
      expect(elements[3]?.data).toMatchObject({
        source: 'entity1',
        target: 'entity2',
      })
      expect(elements[4]?.data).toMatchObject({
        source: 'entity2',
        target: 'entity3',
      })
    })

    it('should hide labels when showLabels is false', () => {
      const graph: DependencyGraph = {
        nodes: [{ name: 'entity1', depends_on: [], depth: 0 }],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: null,
      }

      const elements = toCytoscapeElements(graph, { showLabels: false })
      expect(elements[0]?.classes).toContain('hide-label')
    })

    it('should show labels when showLabels is true', () => {
      const graph: DependencyGraph = {
        nodes: [{ name: 'entity1', depends_on: [], depth: 0 }],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: null,
      }

      const elements = toCytoscapeElements(graph, { showLabels: true })
      expect(elements[0]?.classes).not.toContain('hide-label')
    })

    it('should highlight cycle nodes when highlightCycles is true', () => {
      const graph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: ['entity2'], depth: 0 },
          { name: 'entity2', depends_on: ['entity1'], depth: 1 },
        ],
        edges: [
          ['entity1', 'entity2'],
          ['entity2', 'entity1'],
        ],
        has_cycles: true,
        cycles: [['entity1', 'entity2']],
        topological_order: null,
      }

      const elements = toCytoscapeElements(graph, {
        highlightCycles: true,
        cycles: [['entity1', 'entity2']],
      })

      // Both nodes should be marked as in-cycle
      expect(elements[0]?.classes).toContain('in-cycle')
      expect(elements[1]?.classes).toContain('in-cycle')
    })

    it('should not highlight cycle nodes when highlightCycles is false', () => {
      const graph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: ['entity2'], depth: 0 },
          { name: 'entity2', depends_on: ['entity1'], depth: 1 },
        ],
        edges: [
          ['entity1', 'entity2'],
          ['entity2', 'entity1'],
        ],
        has_cycles: true,
        cycles: [['entity1', 'entity2']],
        topological_order: null,
      }

      const elements = toCytoscapeElements(graph, {
        highlightCycles: false,
        cycles: [['entity1', 'entity2']],
      })

      // Nodes should not be marked as in-cycle
      expect(elements[0]?.classes).not.toContain('in-cycle')
      expect(elements[1]?.classes).not.toContain('in-cycle')
    })

    it('should highlight cycle edges when highlightCycles is true', () => {
      const graph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: ['entity2'], depth: 0 },
          { name: 'entity2', depends_on: ['entity1'], depth: 1 },
        ],
        edges: [
          ['entity1', 'entity2'],
          ['entity2', 'entity1'],
        ],
        has_cycles: true,
        cycles: [['entity1', 'entity2']],
        topological_order: null,
      }

      const elements = toCytoscapeElements(graph, {
        highlightCycles: true,
        cycles: [['entity1', 'entity2']],
      })

      // Both edges should be marked as cycle-edge
      const edges = elements.filter((e) => e.data.source !== undefined)
      expect(edges[0]?.classes).toContain('cycle-edge')
      expect(edges[1]?.classes).toContain('cycle-edge')
    })

    it('should handle complex cycles', () => {
      const graph: DependencyGraph = {
        nodes: [
          { name: 'A', depends_on: ['B'], depth: 0 },
          { name: 'B', depends_on: ['C'], depth: 1 },
          { name: 'C', depends_on: ['A'], depth: 2 },
          { name: 'D', depends_on: [], depth: 0 },
        ],
        edges: [
          ['A', 'B'],
          ['B', 'C'],
          ['C', 'A'],
        ],
        has_cycles: true,
        cycles: [['A', 'B', 'C']],
        topological_order: null,
      }

      const elements = toCytoscapeElements(graph, {
        highlightCycles: true,
        cycles: [['A', 'B', 'C']],
      })

      // A, B, C should be in cycle, D should not
      const nodeA = elements.find((e) => e.data.id === 'A')
      const nodeB = elements.find((e) => e.data.id === 'B')
      const nodeC = elements.find((e) => e.data.id === 'C')
      const nodeD = elements.find((e) => e.data.id === 'D')

      expect(nodeA?.classes).toContain('in-cycle')
      expect(nodeB?.classes).toContain('in-cycle')
      expect(nodeC?.classes).toContain('in-cycle')
      expect(nodeD?.classes).not.toContain('in-cycle')
    })

    it('should track node dependencies count', () => {
      const graph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: [], depth: 0 },
          { name: 'entity2', depends_on: ['entity1'], depth: 1 },
          { name: 'entity3', depends_on: ['entity1', 'entity2'], depth: 2 },
        ],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: null,
      }

      const elements = toCytoscapeElements(graph)

      expect(elements[0]?.data.dependencies).toBe(0)
      expect(elements[1]?.data.dependencies).toBe(1)
      expect(elements[2]?.data.dependencies).toBe(2)
    })

    it('should create unique edge IDs', () => {
      const graph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: [], depth: 0 },
          { name: 'entity2', depends_on: ['entity1'], depth: 1 },
        ],
        edges: [
          ['entity1', 'entity2'],
          ['entity1', 'entity2'], // Duplicate edge
        ],
        has_cycles: false,
        cycles: [],
        topological_order: null,
      }

      const elements = toCytoscapeElements(graph)
      const edges = elements.filter((e) => e.data.source !== undefined)

      // Should have unique IDs
      expect(edges[0]?.data.id).toBe('edge-entity1-entity2-0')
      expect(edges[1]?.data.id).toBe('edge-entity1-entity2-1')
    })
  })

  describe('getLayoutConfig', () => {
    it('should return hierarchical layout config', () => {
      const config = getLayoutConfig('hierarchical', true)

      expect(config).toMatchObject({
        name: 'dagre',
        rankDir: 'TB',
        animate: true,
        fit: true,
        padding: 50,
      })
      expect(config.nodeSep).toBeGreaterThan(0)
      expect(config.rankSep).toBeGreaterThan(0)
    })

    it('should return force-directed layout config', () => {
      const config = getLayoutConfig('force', true)

      expect(config).toMatchObject({
        name: 'cose-bilkent',
        quality: 'default',
        animate: true,
        fit: true,
        padding: 50,
      })
      expect(config.idealEdgeLength).toBeDefined()
      expect(config.nodeRepulsion).toBeGreaterThan(0)
    })

    it('should support animation toggle', () => {
      const withAnimation = getLayoutConfig('hierarchical', true)
      const withoutAnimation = getLayoutConfig('hierarchical', false)

      expect(withAnimation.animate).toBe(true)
      expect(withoutAnimation.animate).toBe(false)
    })

    it('should have longer animation for force layout', () => {
      const hierarchical = getLayoutConfig('hierarchical', true)
      const force = getLayoutConfig('force', true)

      expect(force.animationDuration).toBeGreaterThan(hierarchical.animationDuration!)
    })
  })

  describe('getNodeInfo', () => {
    const mockGraph: DependencyGraph = {
      nodes: [
        { name: 'entity1', depends_on: [], depth: 0 },
        { name: 'entity2', depends_on: ['entity1'], depth: 1 },
        { name: 'entity3', depends_on: ['entity1', 'entity2'], depth: 2 },
      ],
      edges: [
        ['entity1', 'entity2'],
        ['entity1', 'entity3'],
        ['entity2', 'entity3'],
      ],
      has_cycles: false,
      cycles: [],
      topological_order: ['entity1', 'entity2', 'entity3'],
    }

    it('should return null for null graph', () => {
      const info = getNodeInfo('entity1', null)
      expect(info).toBeNull()
    })

    it('should return null for non-existent node', () => {
      const info = getNodeInfo('nonexistent', mockGraph)
      expect(info).toBeNull()
    })

    it('should return node info with all fields', () => {
      const info = getNodeInfo('entity2', mockGraph)

      expect(info).toMatchObject({
        id: 'entity2',
        label: 'entity2',
        depth: 1,
        dependencies: ['entity1'],
        topologicalOrder: 2, // 1-based index
      })
    })

    it('should calculate dependents correctly', () => {
      const info = getNodeInfo('entity1', mockGraph)

      expect(info?.dependents).toHaveLength(2)
      expect(info?.dependents).toContain('entity2')
      expect(info?.dependents).toContain('entity3')
    })

    it('should handle nodes with no dependencies', () => {
      const info = getNodeInfo('entity1', mockGraph)

      expect(info?.dependencies).toEqual([])
    })

    it('should handle nodes with no dependents', () => {
      const info = getNodeInfo('entity3', mockGraph)

      expect(info?.dependents).toEqual([])
    })

    it('should handle graph without topological order', () => {
      const graphWithoutOrder: DependencyGraph = {
        ...mockGraph,
        topological_order: null,
      }

      const info = getNodeInfo('entity2', graphWithoutOrder)

      expect(info?.topologicalOrder).toBeNull()
    })

    it('should return 1-based topological order', () => {
      const info1 = getNodeInfo('entity1', mockGraph)
      const info2 = getNodeInfo('entity2', mockGraph)
      const info3 = getNodeInfo('entity3', mockGraph)

      expect(info1?.topologicalOrder).toBe(1)
      expect(info2?.topologicalOrder).toBe(2)
      expect(info3?.topologicalOrder).toBe(3)
    })

    it('should handle complex dependency relationships', () => {
      const complexGraph: DependencyGraph = {
        nodes: [
          { name: 'A', depends_on: [], depth: 0 },
          { name: 'B', depends_on: ['A'], depth: 1 },
          { name: 'C', depends_on: ['A'], depth: 1 },
          { name: 'D', depends_on: ['B', 'C'], depth: 2 },
        ],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: ['A', 'B', 'C', 'D'],
      }

      const infoA = getNodeInfo('A', complexGraph)
      const infoD = getNodeInfo('D', complexGraph)

      expect(infoA?.dependents).toHaveLength(2) // B and C depend on A directly
      expect(infoA?.dependents).toContain('B')
      expect(infoA?.dependents).toContain('C')
      expect(infoD?.dependencies).toEqual(['B', 'C'])
    })
  })
})
