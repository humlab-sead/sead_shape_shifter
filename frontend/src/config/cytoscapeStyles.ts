/**
 * Cytoscape.js style definitions for dependency graph visualization
 * Integrates with Vuetify theme for consistent styling
 */

import type { Stylesheet } from 'cytoscape'

export interface CytoscapeStyleConfig {
  light: Stylesheet[]
  dark: Stylesheet[]
}

/**
 * Base styles that work for both light and dark themes
 */
const baseStyles: Stylesheet[] = [
  // Node styles
  {
    selector: 'node',
    style: {
      width: 40,
      height: 40,
      'background-color': '#1976d2', // Vuetify primary blue
      'border-width': 2,
      'border-color': '#fff',
      label: 'data(label)',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 8,
      'font-size': '12px',
      'font-family': 'Roboto, sans-serif',
      color: '#333',
      'overlay-padding': 6,
    },
  },

  // Hide labels when showLabels is false
  {
    selector: 'node.hide-label',
    style: {
      label: '',
    },
  },

  // Edge styles
  {
    selector: 'edge',
    style: {
      width: 2,
      'line-color': '#999',
      'target-arrow-color': '#999',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'arrow-scale': 1.2,
    },
  },

  // Cycle highlighting - nodes
  {
    selector: 'node.in-cycle',
    style: {
      'background-color': '#ef5350', // Red for cycles
      'border-color': '#c62828',
      'border-width': 3,
    },
  },

  // Cycle highlighting - edges
  {
    selector: 'edge.cycle-edge',
    style: {
      'line-color': '#ef5350',
      'target-arrow-color': '#ef5350',
      width: 3,
    },
  },

  // Hover states
  {
    selector: 'node:active',
    style: {
      'overlay-opacity': 0.2,
    },
  },

  // Selected node
  {
    selector: 'node:selected',
    style: {
      'border-width': 4,
      'border-color': '#FFA726', // Orange highlight
      'background-color': '#FF9800',
    },
  },

  // Selected edge
  {
    selector: 'edge:selected',
    style: {
      width: 4,
      'line-color': '#FFA726',
      'target-arrow-color': '#FFA726',
    },
  },

  // Node types - data source
  {
    selector: 'node[type="data"]',
    style: {
      shape: 'ellipse',
    },
  },

  // Node types - SQL source
  {
    selector: 'node[type="sql"]',
    style: {
      shape: 'round-rectangle',
    },
  },

  // Node types - fixed values
  {
    selector: 'node[type="fixed"]',
    style: {
      shape: 'diamond',
    },
  },

  // Status indicators
  {
    selector: 'node[status="error"]',
    style: {
      'border-color': '#ef5350',
      'border-width': 3,
    },
  },

  {
    selector: 'node[status="warning"]',
    style: {
      'border-color': '#FFA726',
      'border-width': 3,
    },
  },
]

/**
 * Light theme specific styles
 */
const lightThemeStyles: Stylesheet[] = [
  {
    selector: 'node',
    style: {
      color: '#333',
      'text-outline-color': '#fff',
      'text-outline-width': 1,
    },
  },
]

/**
 * Dark theme specific styles
 */
const darkThemeStyles: Stylesheet[] = [
  {
    selector: 'node',
    style: {
      color: '#fff',
      'text-outline-color': '#121212',
      'text-outline-width': 1,
      'border-color': '#1e1e1e',
    },
  },
  {
    selector: 'edge',
    style: {
      'line-color': '#666',
      'target-arrow-color': '#666',
    },
  },
]

/**
 * Get styles for the current theme
 */
export function getCytoscapeStyles(isDark: boolean = false): Stylesheet[] {
  return [...baseStyles, ...(isDark ? darkThemeStyles : lightThemeStyles)]
}

/**
 * Export combined config for convenience
 */
export const cytoscapeStyleConfig: CytoscapeStyleConfig = {
  light: [...baseStyles, ...lightThemeStyles],
  dark: [...baseStyles, ...darkThemeStyles],
}
