/**
 * Composable for Cytoscape.js graph visualization
 * Handles initialization, styling, layout, and event management
 */

import { ref, watch, onBeforeUnmount, nextTick, type Ref } from 'vue'
import cytoscape, { type Core, type LayoutOptions } from 'cytoscape'
// @ts-expect-error - No type definitions available
import dagre from 'cytoscape-dagre'
// @ts-expect-error - No type definitions available
import coseBilkent from 'cytoscape-cose-bilkent'
import { getCytoscapeStyles } from '@/config/cytoscapeStyles'
import { toCytoscapeElements, getLayoutConfig } from '@/utils/graphAdapter'
import type { CustomGraphLayout, DependencyGraph } from '@/types'

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
  layoutType?: Ref<'hierarchical' | 'force' | 'custom'>

  /**
   * Custom layout positions
   */
  customPositions?: Ref<CustomGraphLayout | null>

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
   * Whether to show source nodes
   */
  showSourceNodes?: Ref<boolean>

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
   * Node double-click handler
   */
  onNodeDoubleClick?: (nodeId: string) => void
  
  /**
   * Node right-click handler
   */
  onNodeRightClick?: (nodeId: string, x: number, y: number) => void

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
    customPositions = ref(null),
    showNodeLabels = ref(true),
    showEdgeLabels = ref(true),
    highlightCycles = ref(false),
    showSourceNodes = ref(false),
    cycles = ref([]),
    isDark = ref(false),
    onNodeClick,
    onNodeDoubleClick,
    onNodeRightClick,
    onBackgroundClick,
  } = options

  const cy = ref<Core | null>(null)
  const isInitialized = ref(false)
  const isAnimating = ref(false)
  
  // Track single-click timeout for preventing conflicts with double-click
  let singleClickTimeout: number | null = null
  const CLICK_DELAY = 250 // milliseconds

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
        wheelSensitivity: 0.3,
        boxSelectionEnabled: false,
        autounselectify: false,
      })

      // Add event listeners
      if (cy.value) {
        // Double tap/click - handle FIRST to prevent single-click action
        cy.value.on('dbltap', 'node', (event) => {
          const nodeId = event.target.id()
          console.debug('[useCytoscape] Node double-click:', nodeId)
          
          // Cancel any pending single-click action
          if (singleClickTimeout !== null) {
            clearTimeout(singleClickTimeout)
            singleClickTimeout = null
          }
          
          onNodeDoubleClick?.(nodeId)
        })
        
        // Single tap/click - delay to allow double-click to cancel it
        cy.value.on('tap', 'node', (event) => {
          const nodeId = event.target.id()
          
          // Cancel previous timeout if exists
          if (singleClickTimeout !== null) {
            clearTimeout(singleClickTimeout)
          }
          
          // Delay single-click action to see if double-click occurs
          singleClickTimeout = window.setTimeout(() => {
            console.debug('[useCytoscape] Node single-click:', nodeId)
            onNodeClick?.(nodeId)
            singleClickTimeout = null
          }, CLICK_DELAY)
        })
        
        // Right-click (context menu) - using cxttap event
        cy.value.on('cxttap', 'node', (event) => {
          console.debug('[useCytoscape] cxttap event fired!', event)
          const nodeId = event.target.id()
          
          // Get the graph container's position
          const containerRect = container.value?.getBoundingClientRect()
          if (!containerRect) return
          
          // Get the rendered position (position on screen relative to container)
          const renderedPosition = event.renderedPosition
          
          // Calculate absolute screen coordinates
          const x = containerRect.left + renderedPosition.x
          const y = containerRect.top + renderedPosition.y
          
          console.debug('[useCytoscape] Node right-click:', nodeId, 'at screen position', { x, y })
          
          onNodeRightClick?.(nodeId, x, y)
          
          // Prevent default context menu
          event.preventDefault()
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
   * Update graph elements (preserves positions of existing nodes)
   */
  function updateElements() {
    console.log('[useCytoscape] updateElements called', {
      hasCy: !!cy.value,
      hasGraphData: !!graphData.value,
      nodesCount: graphData.value?.nodes?.length ?? 0,
    })
    
    if (!cy.value || !graphData.value) {
      console.warn('[useCytoscape] updateElements early return:', {
        hasCy: !!cy.value,
        hasGraphData: !!graphData.value,
      })
      return
    }

    const newElements = toCytoscapeElements(graphData.value, {
      cycles: cycles.value,
      showNodeLabels: showNodeLabels.value,
      showEdgeLabels: showEdgeLabels.value,
      highlightCycles: highlightCycles.value,
      showSourceNodes: showSourceNodes.value,
    })

    const currentElements = cy.value.elements()
    const isInitialRender = currentElements.length === 0
    
    console.log('[useCytoscape] Updating elements:', {
      newElementsCount: newElements.length,
      currentElementsCount: currentElements.length,
      isInitialRender,
    })

    if (isInitialRender) {
      // Initial render: add all elements and run full layout
      console.log('[useCytoscape] Initial render: adding all elements')
      cy.value.add(newElements)
      applyLayout(true)
    } else {
      // Incremental update: preserve existing positions
      const currentIds = new Set(currentElements.map((el) => el.id()))
      const newIds = new Set(newElements.map((el) => el.data.id))
      const toRemove = currentElements.filter((el) => !newIds.has(el.id()))
      const toAdd = newElements.filter((el) => !currentIds.has(el.data.id))

      // Remove deleted elements
      if (toRemove.length > 0) {
        console.log('[useCytoscape] Removing', toRemove.length, 'elements')
        toRemove.remove()
      }

      // Add new elements and layout only them
      if (toAdd.length > 0) {
        console.log('[useCytoscape] Adding', toAdd.length, 'new elements')
        const added = cy.value.add(toAdd)
        
        // Run layout only on new nodes
        const newNodes = added.nodes()
        if (newNodes.length > 0) {
          console.log('[useCytoscape] Running layout for', newNodes.length, 'new nodes')
          
          // For custom layout, run on all nodes to trigger smart positioning
          if (layoutType.value === 'custom') {
            applyLayout(true)
          } else {
            // For other layouts, only layout new nodes
            const layoutConfig = getLayoutConfig(
              layoutType.value,
              true,
              layoutType.value === 'custom' ? customPositions.value ?? undefined : undefined
            )
            newNodes.layout(layoutConfig as LayoutOptions).run()
          }
        }
      }
    }

    console.log('[useCytoscape] Elements updated, final count:', cy.value.elements().length)
  }

  /**
   * Apply layout
   */
  function applyLayout(animate: boolean = true) {
    if (!cy.value || isAnimating.value) return

    const layoutConfig = getLayoutConfig(
      layoutType.value,
      animate,
      layoutType.value === 'custom' ? customPositions.value ?? undefined : undefined
    )

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
    console.log('[useCytoscape] render() called', {
      hasContainer: !!container.value,
      isInitialized: isInitialized.value,
      hasCy: !!cy.value,
      hasGraphData: !!graphData.value,
      nodesCount: graphData.value?.nodes?.length ?? 0,
    })
    
    if (!container.value) {
      console.warn('[useCytoscape] render() early return: no container')
      return
    }

    if (!isInitialized.value) {
      console.log('[useCytoscape] render() calling initialize()')
      initialize()
    }

    if (cy.value && graphData.value) {
      console.log('[useCytoscape] render() calling updateElements()')
      updateElements()
      // Don't call applyLayout here - updateElements handles layout for new nodes
    } else {
      console.warn('[useCytoscape] render() skipped updateElements:', {
        hasCy: !!cy.value,
        hasGraphData: !!graphData.value,
      })
    }
    console.log('[useCytoscape] render() complete')
  }

  /**
   * Destroy Cytoscape instance
   */
  function destroy() {
    console.warn('[useCytoscape] destroy() called!', new Error().stack)
    if (cy.value) {
      cy.value.destroy()
      cy.value = null
      isInitialized.value = false
    }
  }

  // Watch for container changes - initialize when container becomes available
  // Also handles container re-creation (when Vue replaces the div element)
  watch(container, (newContainer, oldContainer) => {
    if (!newContainer) return

    // Case 1: Initial creation (no cy instance yet)
    if (!isInitialized.value) {
      initialize()
      
      // If graphData is already available (race condition after component remount), render it
      if (graphData.value) {
        nextTick(() => render())
      }
      return
    }

    // Case 2: Container was replaced or reappeared (cy exists but container changed)
    // This handles Vue recreating the container div during reactive updates
    if (cy.value && newContainer !== oldContainer) {
      const canvas = newContainer.querySelector('canvas')
      if (!canvas) {
        // Re-mount Cytoscape to the new container
        cy.value.mount(newContainer)
        nextTick(() => render())
      }
    }
  })


  // Watch for graph data changes
  watch(
    graphData,
    (newData) => {
      if (newData && isInitialized.value) {
        render()
      }
    },
    { deep: true }
  )

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

  // Watch for source node visibility changes
  watch(showSourceNodes, () => {
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

  /**
   * Get current node positions for saving custom layout
   * Saves positions for all visible nodes (entities and sources)
   */
  function getCurrentPositions(): CustomGraphLayout {
    if (!cy.value) return {}

    const positions: CustomGraphLayout = {}
    cy.value.nodes().forEach((node) => {
      const nodeName = node.data('id')
      const pos = node.position()
      positions[nodeName] = { x: pos.x, y: pos.y }
    })
    return positions
  }

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
    getCurrentPositions,
    zoomIn,
    zoomOut,
    exportPNG,
    exportJSON,
    destroy,
  }
}
