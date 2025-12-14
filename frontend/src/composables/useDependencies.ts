/**
 * Composable for dependency graph analysis
 * Wraps dependency features from validation store and formats for visualization
 */

import { computed, ref, watch } from 'vue'
import { useValidationStore } from '@/stores'
import type { GraphNode, GraphEdge } from '@/types'

export interface UseDependenciesOptions {
  configName?: string
  autoFetch?: boolean
  checkCycles?: boolean
}

export function useDependencies(options: UseDependenciesOptions = {}) {
  const { configName, autoFetch = false, checkCycles = false } = options
  const store = useValidationStore()
  const lastFetchedConfig = ref<string | null>(null)

  // Computed state from store
  const dependencyGraph = computed(() => store.dependencyGraph)
  const circularDependencyCheck = computed(() => store.circularDependencyCheck)
  const loading = computed(() => store.loading)
  const error = computed(() => store.error)

  // Computed getters
  const hasCircularDependencies = computed(() => store.hasCircularDependencies)
  const cycles = computed(() => store.cycles)
  const cycleCount = computed(() => store.cycleCount)
  const topologicalOrder = computed(() => store.topologicalOrder)

  // Actions
  async function fetch(name: string) {
    try {
      const result = await store.fetchDependencies(name)
      lastFetchedConfig.value = name
      return result
    } catch (err) {
      console.error(`Failed to fetch dependencies for "${name}":`, err)
      throw err
    }
  }

  async function checkCircularDependencies(name: string) {
    try {
      return await store.checkCircularDependencies(name)
    } catch (err) {
      console.error(`Failed to check circular dependencies for "${name}":`, err)
      throw err
    }
  }

  function clearDependencies() {
    store.clearDependencies()
    lastFetchedConfig.value = null
  }

  function clearError() {
    store.clearError()
  }

  // Format graph data for D3.js visualization
  const graphData = computed(() => {
    if (!dependencyGraph.value) return null

    const nodes: GraphNode[] = dependencyGraph.value.nodes.map((node, index) => ({
      id: node.name,
      label: node.name,
      topological_order: dependencyGraph.value?.topological_order?.indexOf(node.name) ?? index,
      data: {
        depends_on: node.depends_on,
        depth: node.depth,
      },
    }))

    const edges: GraphEdge[] = dependencyGraph.value.edges.map(([source, target]) => ({
      id: `${source}-${target}`,
      source,
      target,
      type: 'dependency' as const,
      data: {},
    }))

    return {
      nodes,
      edges,
      has_cycles: dependencyGraph.value.has_cycles,
      cycles: dependencyGraph.value.cycles,
      topological_order: dependencyGraph.value.topological_order,
    }
  })

  // Helper: Get node by name
  const getNode = (name: string) => {
    return dependencyGraph.value?.nodes.find((n) => n.name === name)
  }

  // Helper: Get dependencies of a node
  const getDependenciesOf = (name: string) => {
    return dependencyGraph.value?.nodes.find((n) => n.name === name)?.depends_on ?? []
  }

  // Helper: Get dependents (reverse dependencies)
  const getDependentsOf = (name: string) => {
    return (
      dependencyGraph.value?.nodes
        .filter((n) => n.depends_on.includes(name))
        .map((n) => n.name) ?? []
    )
  }

  // Helper: Check if node is in a cycle
  const isInCycle = (name: string) => {
    return cycles.value.some((cycle) => cycle.includes(name))
  }

  // Helper: Get cycle containing node
  const getCycleContaining = (name: string) => {
    return cycles.value.find((cycle) => cycle.includes(name))
  }

  // Helper: Check if graph is stale
  const isStale = computed(() => {
    return configName ? lastFetchedConfig.value !== configName : false
  })

  // Statistics
  const statistics = computed(() => ({
    nodeCount: dependencyGraph.value?.nodes.length ?? 0,
    edgeCount: dependencyGraph.value?.edges.length ?? 0,
    cycleCount: cycleCount.value,
    maxDepth: Math.max(...(dependencyGraph.value?.nodes.map((n) => n.depth) ?? [0])),
    rootCount: dependencyGraph.value?.nodes.filter((n) => n.depends_on.length === 0).length ?? 0,
  }))

  // Auto-fetch on mount if enabled
  if (autoFetch && configName) {
    fetch(configName)
  }

  // Auto-check cycles if enabled
  if (checkCycles && configName) {
    checkCircularDependencies(configName)
  }

  // Watch for config changes
  watch(
    () => configName,
    async (newName, oldName) => {
      if (newName && newName !== oldName) {
        if (autoFetch) {
          await fetch(newName)
        }
        if (checkCycles) {
          await checkCircularDependencies(newName)
        }
      }
    }
  )

  return {
    // State
    dependencyGraph,
    circularDependencyCheck,
    loading,
    error,
    lastFetchedConfig,
    // Computed
    hasCircularDependencies,
    cycles,
    cycleCount,
    topologicalOrder,
    graphData,
    statistics,
    isStale,
    // Actions
    fetch,
    checkCircularDependencies,
    clearDependencies,
    clearError,
    // Helpers
    getNode,
    getDependenciesOf,
    getDependentsOf,
    isInCycle,
    getCycleContaining,
  }
}
