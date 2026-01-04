/**
 * Cytoscape.js style definitions for dependency graph visualization
 * Integrates with Vuetify theme for consistent styling
 */

import type { StylesheetCSS } from 'cytoscape'

export interface CytoscapeStyleConfig {
  light: StylesheetCSS[]
  dark: StylesheetCSS[]
}

/**
 * Base styles that work for both light and dark themes
 */
const baseStyles: StylesheetCSS[] = [
  // Node styles
  {
    selector: 'node',
    css: {
      width: 40,
      height: 40,
      'background-color': '#1976d2', // Vuetify primary blue
      'border-width': 2,
      'border-color': '#fff',
      label: 'data(label)',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 8,
      'font-size': '20px',
      'font-family': 'Roboto, sans-serif',
      color: '#333',
      'overlay-padding': 6,
    },
  },

  // Hide labels when showLabels is false
  {
    selector: 'node.hide-label',
    css: {
      label: '',
    },
  },

  // Node types - data source
  {
    selector: 'node[type="data"]',
    css: {
      shape: 'ellipse',
      'background-color': '#1976d2',
    },
  },

  // Node types - SQL source
  {
    selector: 'node[type="sql"]',
    css: {
      shape: 'ellipse',
      'background-color': '#2E7D32',
    },
  },

  // Node types - fixed values
  {
    selector: 'node[type="fixed"]',
    css: {
      shape: 'ellipse',
      'background-color': '#6A1B9A',
    },
  },

  // Status indicators
  {
    selector: 'node[status="error"]',
    css: {
      'border-color': '#ef5350',
      'border-width': 3,
    },
  },

  {
    selector: 'node[status="warning"]',
    css: {
      'border-color': '#FFA726',
      'border-width': 3,
    },
  },

  // Edge styles
  {
    selector: 'edge',
    css: {
      width: 2,
      'line-color': '#999',
      'target-arrow-color': '#999',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'arrow-scale': 1.2,
      label: 'data(label)',
      'font-size': '10px',
      'text-rotation': 'autorotate',
      'text-margin-y': -10,
      'text-background-opacity': 0,
      color: '#666',
    },
  },

  // Hide edge labels (must come after edge styles to override)
  {
    selector: 'edge.hide-label',
    css: {
      label: '',
    },
  },

  // Cycle highlighting - nodes (must come after node type styles)
  {
    selector: 'node.in-cycle',
    css: {
      'background-color': '#ef5350', // Red for cycles
      'border-color': '#c62828',
      'border-width': 3,
    },
  },

  // Cycle highlighting - edges (must come after base edge styles)
  {
    selector: 'edge.cycle-edge',
    css: {
      'line-color': '#ef5350',
      'target-arrow-color': '#ef5350',
      width: 3,
    },
  },

  // Hover states
  {
    selector: 'node:active',
    css: {
      'overlay-opacity': 0.2,
    },
  },

  // Selected node (must come after node type and cycle styles)
  {
    selector: 'node:selected',
    css: {
      'border-width': 4,
      'border-color': '#FFA726', // Orange highlight
      'background-color': '#FF9800',
    },
  },

  // Selected edge (must come after base and cycle edge styles)
  {
    selector: 'edge:selected',
    css: {
      width: 4,
      'line-color': '#FFA726',
      'target-arrow-color': '#FFA726',
    },
  },
]

/**
 * Light theme specific styles
 */
const lightThemeStyles: StylesheetCSS[] = [
  {
    selector: 'node',
    css: {
      color: '#333',
      'text-outline-color': '#fff',
      'text-outline-width': 1,
    },
  },
]

/**
 * Dark theme specific styles
 */
const darkThemeStyles: StylesheetCSS[] = [
  {
    selector: 'node',
    css: {
      color: '#fff',
      'text-outline-color': '#121212',
      'text-outline-width': 1,
      'border-color': '#1e1e1e',
    },
  },
  {
    selector: 'edge',
    css: {
      'line-color': '#666',
      'target-arrow-color': '#666',
      color: '#aaa',
      'text-background-color': '#121212',
    },
  },
]

/**
 * Get styles for the current theme
 */
export function getCytoscapeStyles(isDark: boolean = false): StylesheetCSS[] {
  return [...baseStyles, ...(isDark ? darkThemeStyles : lightThemeStyles)]
}

/**
 * Export combined config for convenience
 */
export const cytoscapeStyleConfig: CytoscapeStyleConfig = {
  light: [...baseStyles, ...lightThemeStyles],
  dark: [...baseStyles, ...darkThemeStyles],
}
