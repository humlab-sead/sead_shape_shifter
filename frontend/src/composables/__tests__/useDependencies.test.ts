import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick } from 'vue'
import { useDependencies } from '../useDependencies'
import { useValidationStore } from '@/stores'
import type { DependencyGraph, DependencyNode } from '@/types'

// Mock console methods
const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

describe('useDependencies', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    consoleError.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('initialization', () => {
    it('should initialize with default options', () => {
      const { loading, error, dependencyGraph } = useDependencies()

      expect(loading.value).toBe(false)
      expect(error.value).toBeNull()
      expect(dependencyGraph.value).toBeNull()
    })

    it('should accept projectName option', () => {
      const { lastFetchedProject } = useDependencies({ projectName: 'test-project' })

      expect(lastFetchedProject.value).toBeNull()
    })

    it('should accept autoFetch option', () => {
      const store = useValidationStore()
      vi.spyOn(store, 'fetchDependencies')

      useDependencies({ autoFetch: false })

      expect(store.fetchDependencies).not.toHaveBeenCalled()
    })

    it('should accept checkCycles option', () => {
      const store = useValidationStore()
      vi.spyOn(store, 'checkCircularDependencies')

      useDependencies({ checkCycles: false })

      expect(store.checkCircularDependencies).not.toHaveBeenCalled()
    })
  })

  describe('computed state', () => {
    it('should expose dependencyGraph from store', () => {
      const store = useValidationStore()
      const { dependencyGraph } = useDependencies()

      const mockGraph: DependencyGraph = {
        nodes: [
          { name: 'entity1', depends_on: [], depth: 0 },
          { name: 'entity2', depends_on: ['entity1'], depth: 1 },
        ],
        edges: [['entity2', 'entity1']],
        has_cycles: false,
        cycles: [],
        topological_order: ['entity1', 'entity2'],
      }

      store.$patch({ dependencyGraph: mockGraph })

      expect(dependencyGraph.value).toEqual(mockGraph)
    })

    it('should expose circularDependencyCheck from store', () => {
      const store = useValidationStore()
      const { circularDependencyCheck } = useDependencies()

      const mockCheck = {
        has_cycles: true,
        cycles: [['entity1', 'entity2', 'entity1']],
      }

      store.$patch({ circularDependencyCheck: mockCheck })

      expect(circularDependencyCheck.value).toEqual(mockCheck)
    })

    it('should expose loading state from store', () => {
      const store = useValidationStore()
      const { loading } = useDependencies()

      store.$patch({ loading: true })
      expect(loading.value).toBe(true)

      store.$patch({ loading: false })
      expect(loading.value).toBe(false)
    })

    it('should expose error state from store', () => {
      const store = useValidationStore()
      const { error } = useDependencies()

      store.$patch({ error: 'Test error' })
      expect(error.value).toBe('Test error')

      store.$patch({ error: null })
      expect(error.value).toBeNull()
    })
  })

  describe('computed getters', () => {
    it('should compute hasCircularDependencies correctly', () => {
      const store = useValidationStore()
      const { hasCircularDependencies } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [],
          edges: [],
          has_cycles: true,
          cycles: [['entity1', 'entity2', 'entity1']],
          topological_order: null,
        },
      })

      expect(hasCircularDependencies.value).toBe(true)
    })

    it('should expose cycles from store', () => {
      const store = useValidationStore()
      const { cycles } = useDependencies()

      const mockCycles = [['entity1', 'entity2', 'entity1']]

      store.$patch({
        dependencyGraph: {
          nodes: [],
          edges: [],
          has_cycles: true,
          cycles: mockCycles,
          topological_order: null,
        },
      })

      expect(cycles.value).toEqual(mockCycles)
    })

    it('should compute cycleCount correctly', () => {
      const store = useValidationStore()
      const { cycleCount } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [],
          edges: [],
          has_cycles: true,
          cycles: [
            ['entity1', 'entity2', 'entity1'],
            ['entity3', 'entity4', 'entity3'],
          ],
          topological_order: null,
        },
      })

      expect(cycleCount.value).toBe(2)
    })

    it('should expose topologicalOrder from store', () => {
      const store = useValidationStore()
      const { topologicalOrder } = useDependencies()

      const mockOrder = ['entity1', 'entity2', 'entity3']

      store.$patch({
        dependencyGraph: {
          nodes: [],
          edges: [],
          has_cycles: false,
          cycles: [],
          topological_order: mockOrder,
        },
      })

      expect(topologicalOrder.value).toEqual(mockOrder)
    })
  })

  describe('fetch action', () => {
    it('should fetch dependencies successfully', async () => {
      const store = useValidationStore()
      const mockGraph: DependencyGraph = {
        nodes: [{ name: 'entity1', depends_on: [], depth: 0 }],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: ['entity1'],
      }

      vi.spyOn(store, 'fetchDependencies').mockResolvedValue(mockGraph)

      const { fetch, lastFetchedProject } = useDependencies()
      const result = await fetch('test-project')

      expect(store.fetchDependencies).toHaveBeenCalledWith('test-project')
      expect(result).toEqual(mockGraph)
      expect(lastFetchedProject.value).toBe('test-project')
    })

    it('should handle fetch errors', async () => {
      const store = useValidationStore()
      const error = new Error('Fetch failed')
      vi.spyOn(store, 'fetchDependencies').mockRejectedValue(error)

      const { fetch } = useDependencies()

      await expect(fetch('test-project')).rejects.toThrow('Fetch failed')
    })
  })

  describe('checkCircularDependencies action', () => {
    it('should check for circular dependencies', async () => {
      const store = useValidationStore()
      const mockCheck = {
        has_cycles: true,
        cycles: [['entity1', 'entity2', 'entity1']],
      }

      vi.spyOn(store, 'checkCircularDependencies').mockResolvedValue(mockCheck)

      const { checkCircularDependencies } = useDependencies()
      const result = await checkCircularDependencies('test-project')

      expect(store.checkCircularDependencies).toHaveBeenCalledWith('test-project')
      expect(result).toEqual(mockCheck)
    })

    it('should handle check errors', async () => {
      const store = useValidationStore()
      const error = new Error('Check failed')
      vi.spyOn(store, 'checkCircularDependencies').mockRejectedValue(error)

      const { checkCircularDependencies } = useDependencies()

      await expect(checkCircularDependencies('test-project')).rejects.toThrow('Check failed')
    })
  })

  describe('graphData transformation', () => {
    it('should transform dependency graph to graph data', () => {
      const store = useValidationStore()
      const { graphData } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [
            { name: 'entity1', depends_on: [], depth: 0 },
            { name: 'entity2', depends_on: ['entity1'], depth: 1 },
          ],
          edges: [['entity2', 'entity1']],
          has_cycles: false,
          cycles: [],
          topological_order: ['entity1', 'entity2'],
        },
      })

      expect(graphData.value).toBeDefined()
      expect(graphData.value?.nodes).toHaveLength(2)
      expect(graphData.value?.edges).toHaveLength(1)
      expect(graphData.value?.has_cycles).toBe(false)
    })

    it('should handle null dependency graph', () => {
      const { graphData } = useDependencies()

      expect(graphData.value).toBeNull()
    })

    it('should include topological order in node data', () => {
      const store = useValidationStore()
      const { graphData } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [
            { name: 'entity1', depends_on: [], depth: 0 },
            { name: 'entity2', depends_on: ['entity1'], depth: 1 },
          ],
          edges: [['entity2', 'entity1']],
          has_cycles: false,
          cycles: [],
          topological_order: ['entity1', 'entity2'],
        },
      })

      const entity1Node = graphData.value?.nodes.find((n) => n.id === 'entity1')
      const entity2Node = graphData.value?.nodes.find((n) => n.id === 'entity2')

      expect(entity1Node?.topological_order).toBe(0)
      expect(entity2Node?.topological_order).toBe(1)
    })
  })

  describe('helper methods', () => {
    it('should get node by name', () => {
      const store = useValidationStore()
      const { getNode } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [
            { name: 'entity1', depends_on: [], depth: 0 },
            { name: 'entity2', depends_on: ['entity1'], depth: 1 },
          ],
          edges: [['entity2', 'entity1']],
          has_cycles: false,
          cycles: [],
          topological_order: ['entity1', 'entity2'],
        },
      })

      const node = getNode('entity1')

      expect(node).toEqual({ name: 'entity1', depends_on: [], depth: 0 })
    })

    it('should get dependencies of a node', () => {
      const store = useValidationStore()
      const { getDependenciesOf } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [
            { name: 'entity1', depends_on: [], depth: 0 },
            { name: 'entity2', depends_on: ['entity1'], depth: 1 },
          ],
          edges: [['entity2', 'entity1']],
          has_cycles: false,
          cycles: [],
          topological_order: ['entity1', 'entity2'],
        },
      })

      const deps = getDependenciesOf('entity2')

      expect(deps).toEqual(['entity1'])
    })

    it('should get dependents of a node', () => {
      const store = useValidationStore()
      const { getDependentsOf } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [
            { name: 'entity1', depends_on: [], depth: 0 },
            { name: 'entity2', depends_on: ['entity1'], depth: 1 },
          ],
          edges: [['entity2', 'entity1']],
          has_cycles: false,
          cycles: [],
          topological_order: ['entity1', 'entity2'],
        },
      })

      const dependents = getDependentsOf('entity1')

      expect(dependents).toEqual(['entity2'])
    })

    it('should check if node is in a cycle', () => {
      const store = useValidationStore()
      const { isInCycle } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [],
          edges: [],
          has_cycles: true,
          cycles: [['entity1', 'entity2', 'entity1']],
          topological_order: null,
        },
      })

      expect(isInCycle('entity1')).toBe(true)
      expect(isInCycle('entity3')).toBe(false)
    })

    it('should get cycle containing a node', () => {
      const store = useValidationStore()
      const { getCycleContaining } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [],
          edges: [],
          has_cycles: true,
          cycles: [
            ['entity1', 'entity2', 'entity1'],
            ['entity3', 'entity4', 'entity3'],
          ],
          topological_order: null,
        },
      })

      const cycle = getCycleContaining('entity1')

      expect(cycle).toEqual(['entity1', 'entity2', 'entity1'])
    })
  })

  describe('clearDependencies action', () => {
    it('should clear dependencies state', async () => {
      const store = useValidationStore()
      vi.spyOn(store, 'clearDependencies')
      vi.spyOn(store, 'fetchDependencies').mockResolvedValue({
        nodes: [],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: [],
      })

      const { clearDependencies, lastFetchedProject, fetch } = useDependencies()

      await fetch('test-project')
      expect(lastFetchedProject.value).toBe('test-project')

      clearDependencies()

      expect(store.clearDependencies).toHaveBeenCalled()
      expect(lastFetchedProject.value).toBeNull()
    })
  })

  describe('clearError action', () => {
    it('should clear error state', () => {
      const store = useValidationStore()
      vi.spyOn(store, 'clearError')

      const { clearError } = useDependencies()
      clearError()

      expect(store.clearError).toHaveBeenCalled()
    })
  })

  describe('statistics', () => {
    it('should compute dependency statistics', () => {
      const store = useValidationStore()
      const { statistics } = useDependencies()

      store.$patch({
        dependencyGraph: {
          nodes: [
            { name: 'entity1', depends_on: [], depth: 0 },
            { name: 'entity2', depends_on: ['entity1'], depth: 1 },
            { name: 'entity3', depends_on: ['entity2'], depth: 2 },
          ],
          edges: [
            ['entity2', 'entity1'],
            ['entity3', 'entity2'],
          ],
          has_cycles: false,
          cycles: [],
          topological_order: ['entity1', 'entity2', 'entity3'],
        },
      })

      expect(statistics.value.nodeCount).toBe(3)
      expect(statistics.value.edgeCount).toBe(2)
      expect(statistics.value.cycleCount).toBe(0)
      expect(statistics.value.maxDepth).toBe(2)
      expect(statistics.value.rootCount).toBe(1)
    })

    it('should handle empty graph statistics', () => {
      const { statistics } = useDependencies()

      expect(statistics.value.nodeCount).toBe(0)
      expect(statistics.value.edgeCount).toBe(0)
      expect(statistics.value.cycleCount).toBe(0)
      expect(statistics.value.maxDepth).toBe(0)
      expect(statistics.value.rootCount).toBe(0)
    })
  })

  describe('stale state tracking', () => {
    it('should track if data is stale', async () => {
      const store = useValidationStore()
      vi.spyOn(store, 'fetchDependencies').mockResolvedValue({
        nodes: [],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: [],
      })

      const { isStale, fetch } = useDependencies({ projectName: 'project1' })

      expect(isStale.value).toBe(true)

      await fetch('project1')
      expect(isStale.value).toBe(false)
    })

    it('should detect stale state when project changes', async () => {
      const store = useValidationStore()
      vi.spyOn(store, 'fetchDependencies').mockResolvedValue({
        nodes: [],
        edges: [],
        has_cycles: false,
        cycles: [],
        topological_order: [],
      })

      const { isStale, fetch } = useDependencies({ projectName: 'project2' })

      await fetch('project1')
      expect(isStale.value).toBe(true)
    })

    it('should not be stale when no project is specified', () => {
      const { isStale } = useDependencies()

      expect(isStale.value).toBe(false)
    })
  })
})
