/**
 * Composable for Cytoscape.js graph visualization
 * Handles initialization, styling, layout, and event management
 */

import { ref, watch, onBeforeUnmount, type Ref } from 'vue'
import cytoscape, { type Core, type LayoutOptions } from 'cytoscape'
// @ts-expect-error - No type definitions available
import dagre from 'cytoscape-dagre'
// @ts-expect-error - No type definitions available
import coseBilkent from 'cytoscape-cose-bilkent'
import { getCytoscapeStyles } from '@/config/cytoscapeStyles'
import { toCytoscapeElements, getLayoutConfig } from '@/utils/graphAdapter'
import type { DependencyGraph } from '@/types'

// Register layouts
cytoscape.use(dagre)
cytoscape.use(coseBilkent)

export interface UseCytoscapeOptions {
  /**
   * Container element reference
   */
  container: Ref<HTMLElement | null>

  /**
   * Graph data to visualize
   */
  graphData: Ref<DependencyGraph | null>

  /**
   * Layout type
   */
  layoutType?: Ref<'hierarchical' | 'force'>

  /**
   * Whether to show node labels
   */
  showNodeLabels?: Ref<boolean>

  /**
   * Whether to show edge labels
   */
  showEdgeLabels?: Ref<boolean>

  /**
   * Whether to highlight cycle nodes/edges
   */
  highlightCycles?: Ref<boolean>

  /**
   * Cycles to highlight
   */
  cycles?: Ref<string[][]>

  /**
   * Dark theme enabled
   */
  isDark?: Ref<boolean>

  /**
   * Node click handler
   */
  onNodeClick?: (nodeId: string) => void

  /**
   * Background click handler
   */
  onBackgroundClick?: () => void
}

export function useCytoscape(options: UseCytoscapeOptions) {
  const {
    container,
    graphData,
    layoutType = ref('hierarchical'),
    showNodeLabels = ref(true),
    showEdgeLabels = ref(true),
    highlightCycles = ref(false),
    cycles = ref([]),
    isDark = ref(false),
    onNodeClick,
    onBackgroundClick,
  } = options

  const cy = ref<Core | null>(null)
  const isInitialized = ref(false)
  const isAnimating = ref(false)

  /**
   * Initialize Cytoscape instance
   */
  function initialize() {
    if (!container.value || isInitialized.value) return

    try {
      cy.value = cytoscape({
        container: container.value,
        elements: [],
        style: getCytoscapeStyles(isDark.value),
        minZoom: 0.3,
        maxZoom: 3,
        wheelSensitivity: 0.2,
        boxSelectionEnabled: false,
        autounselectify: false,
      })

      // Add event listeners
      if (cy.value) {
        cy.value.on('tap', 'node', (event) => {
          const nodeId = event.target.id()
          onNodeClick?.(nodeId)
        })

        cy.value.on('tap', (event) => {
          if (event.target === cy.value) {
            onBackgroundClick?.()
          }
        })
      }

      isInitialized.value = true
    } catch (error) {
      console.error('Failed to initialize Cytoscape:', error)
    }
  }

  /**
   * Update graph elements
   */
  function updateElements() {
    if (!cy.value || !graphData.value) return

    const elements = toCytoscapeElements(graphData.value, {
      cycles: cycles.value,
      showNodeLabels: showNodeLabels.value,
      showEdgeLabels: showEdgeLabels.value,
      highlightCycles: highlightCycles.value,
    })

    cy.value.elements().remove()
    cy.value.add(elements)
  }

  /**
   * Apply layout
   */
  function applyLayout(animate: boolean = true) {
    if (!cy.value || isAnimating.value) return

    const layoutConfig = getLayoutConfig(layoutType.value, animate)

    isAnimating.value = true

    const layout = cy.value.layout(layoutConfig as LayoutOptions)

    layout.on('layoutstop', () => {
      isAnimating.value = false
    })

    layout.run()
  }

  /**
   * Update styles (e.g., for theme changes)
   */
  function updateStyles() {
    if (!cy.value) return

    cy.value.style(getCytoscapeStyles(isDark.value))
  }

  /**
   * Fit graph to viewport
   */
  function fit(padding: number = 50) {
    if (!cy.value) return
    cy.value.fit(undefined, padding)
  }

  /**
   * Center graph in viewport
   */
  function center() {
    if (!cy.value) return
    cy.value.center()
  }

  /**
   * Reset zoom and pan
   */
  function reset() {
    fit()
  }

  /**
   * Zoom in
   */
  function zoomIn() {
    if (!cy.value) return
    cy.value.zoom({
      level: cy.value.zoom() * 1.2,
      renderedPosition: {
        x: cy.value.width() / 2,
        y: cy.value.height() / 2,
      },
    })
  }

  /**
   * Zoom out
   */
  function zoomOut() {
    if (!cy.value) return
    cy.value.zoom({
      level: cy.value.zoom() * 0.8,
      renderedPosition: {
        x: cy.value.width() / 2,
        y: cy.value.height() / 2,
      },
    })
  }

  /**
   * Export graph as PNG
   */
  function exportPNG(): string | null {
    if (!cy.value) return null
    return cy.value.png({
      output: 'base64',
      bg: isDark.value ? '#121212' : '#ffffff',
      full: true,
      scale: 2,
    })
  }

  /**
   * Export graph as JSON
   */
  function exportJSON(): object | null {
    if (!cy.value) return null
    return cy.value.json()
  }

  /**
   * Render the graph (initialize + update + layout)
   */
  function render() {
    if (!container.value) return

    if (!isInitialized.value) {
      initialize()
    }

    if (cy.value && graphData.value) {
      updateElements()
      applyLayout(true)
    }
  }

  /**
   * Destroy Cytoscape instance
   */
  function destroy() {
    if (cy.value) {
      cy.value.destroy()
      cy.value = null
      isInitialized.value = false
    }
  }

  // Watch for container changes - initialize when container becomes available
  watch(container, (newContainer) => {
    if (newContainer && !isInitialized.value) {
      initialize()
      if (graphData.value) {
        render()
      }
    }
  })

  // Watch for graph data changes
  watch(graphData, (newData) => {
    if (newData) {
      render()
    }
  })

  // Watch for layout type changes
  watch(layoutType, () => {
    applyLayout(true)
  })

  // Watch for node label visibility changes
  watch(showNodeLabels, () => {
    updateElements()
    applyLayout(false) // Re-apply layout without animation
  })

  // Watch for edge label visibility changes
  watch(showEdgeLabels, () => {
    updateElements()
    applyLayout(false) // Re-apply layout without animation
  })

  // Watch for cycle highlighting changes
  watch(highlightCycles, () => {
    updateElements()
    applyLayout(false) // Re-apply layout without animation
  })

  // Watch for theme changes
  watch(isDark, () => {
    updateStyles()
  })

  // Cleanup on unmount
  onBeforeUnmount(() => {
    destroy()
  })

  return {
    cy,
    isInitialized,
    isAnimating,
    initialize,
    render,
    updateElements,
    applyLayout,
    updateStyles,
    fit,
    center,
    reset,
    zoomIn,
    zoomOut,
    exportPNG,
    exportJSON,
    destroy,
  }
}
