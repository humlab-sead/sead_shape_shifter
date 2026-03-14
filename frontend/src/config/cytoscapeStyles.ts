/**
 * Cytoscape.js style definitions for dependency graph visualization
 * Integrates with Vuetify theme for consistent styling
 */

import type { StylesheetCSS } from 'cytoscape'

export interface CytoscapeStyleConfig {
  light: StylesheetCSS[]
  dark: StylesheetCSS[]
}

const NOTE_DOT_SVG = `data:image/svg+xml;utf8,${encodeURIComponent(
  '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="16" fill="#0F172A"/><circle cx="50" cy="50" r="12.5" fill="#FFFFFF"/></svg>'
)}`

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

  // Node types - entity (derived)
  {
    selector: 'node[type="entity"]',
    css: {
      shape: 'ellipse',
      'background-color': '#1976d2',
    },
  },

  // Node types - CSV file
  {
    selector: 'node[type="csv"]',
    css: {
      shape: 'ellipse',
      'background-color': '#FFA500',
    },
  },

  // Node types - Excel (Pandas)
  {
    selector: 'node[type="xlsx"]',
    css: {
      shape: 'ellipse',
      'background-color': '#00a86b',
    },
  },

  // Node types - Excel (OpenPyXL)
  {
    selector: 'node[type="openpyxl"]',
    css: {
      shape: 'ellipse',
      'background-color': '#20b2aa',
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

  // Source node base styles
  {
    selector: 'node.source-node',
    css: {
      'background-opacity': 0.9,
      'border-width': 2,
      'border-style': 'solid',
      'font-size': '18px',
    },
  },

  // Datasource nodes - database with icon
  {
    selector: 'node.source-datasource',
    css: {
      shape: 'barrel',
      'background-color': '#1565C0', // Deep blue (database color)
      'border-color': '#42A5F5', // Light blue
      width: 40,
      height: 40,
    },
  },

  // Table nodes - data table with icon
  {
    selector: 'node.source-table',
    css: {
      shape: 'rectangle',
      'background-color': '#00838F', // Teal/cyan (data color)
      'border-color': '#26C6DA', // Light cyan
      width: 36,
      height: 36,
    },
  },

  // CSV file nodes - chart/data with icon
  {
    selector: 'node.source-file[sourceCategory="csv"]',
    css: {
      shape: 'round-rectangle',
      'background-color': '#C62828', // Red (CSV distinctive)
      'border-color': '#EF5350', // Light red
      width: 38,
      height: 38,
    },
  },

  // Excel file nodes - spreadsheet with icon
  {
    selector: 'node.source-file[sourceCategory="xlsx"], node.source-file[sourceCategory="openpyxl"]',
    css: {
      shape: 'round-rectangle',
      'background-color': '#2E7D32', // Green (Excel brand)
      'border-color': '#66BB6A', // Light green
      width: 38,
      height: 38,
    },
  },

  // Generic file nodes - fallback for other file types
  {
    selector: 'node.source-file',
    css: {
      shape: 'round-rectangle',
      'background-color': '#5E35B1', // Purple (generic file)
      'border-color': '#9575CD', // Light purple
      width: 38,
      height: 38,
    },
  },

  // Sheet nodes - Excel/spreadsheet sheets with icon
  {
    selector: 'node.source-sheet',
    css: {
      shape: 'round-rectangle',
      'background-color': '#1B5E20', // Excel dark green
      'border-color': '#4CAF50', // Excel light green
      width: 36,
      height: 36,
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

  // Source edges - visually distinct from entity edges
  {
    selector: 'edge.source-edge',
    css: {
      'line-style': 'dotted',
      'line-color': '#00796B',
      'target-arrow-color': '#00796B',
      width: 1.5,
      opacity: 0.7,
      'arrow-scale': 1,
    },
  },

  // Frozen edges - from materialized entities showing historical dependencies
  {
    selector: 'edge.frozen-edge',
    css: {
      'line-style': 'dashed',
      'line-color': '#4CAF50', // Green to match materialized nodes
      'target-arrow-color': '#4CAF50',
      width: 1.5,
      opacity: 0.6,
      'arrow-scale': 1,
      'line-dash-pattern': [8, 4], // Dashed pattern: 8px line, 4px gap
    },
  },

  // Materialized entities - multi-indicator strategy
  {
    selector: 'node.materialized',
    css: {
      'border-style': 'double', // Double border = frozen/locked state
      'border-width': 4,
      'border-color': '#4CAF50', // Green = stable/cached
      'background-opacity': 0.85, // Slightly transparent
    },
  },

  // Task status overlays (applied by ProjectDetailView via node classes)
  {
    selector: 'node.task-todo',
    css: {
      'background-color': '#FDD835',
      'border-color': '#F9A825',
      'border-width': 3,
    },
  },
  {
    selector: 'node.task-done',
    css: {
      'background-color': '#43A047',
      'border-color': '#2E7D32',
      'border-width': 3,
    },
  },
  {
    selector: 'node.task-ignored',
    css: {
      'background-color': '#9E9E9E',
      'border-color': '#616161',
      'border-style': 'dashed',
      'border-width': 3,
      opacity: 0.75,
    },
  },
  {
    selector: 'node.task-blocked',
    css: {
      'border-color': '#FB8C00',
      'border-width': 4,
    },
  },
  {
    selector: 'node.task-critical',
    css: {
      'border-color': '#E53935',
      'border-width': 4,
      'background-color': '#EF5350',
    },
  },
  {
    selector: 'node.task-ready',
    css: {
      'border-color': '#1E88E5',
      'border-width': 3,
    },
  },
  {
    selector: 'node.task-ongoing',
    css: {
      'background-color': '#2196F3',
      'border-color': '#1976D2',
      'border-width': 3,
    },
  },
  {
    selector: 'node.task-flagged',
    css: {
      'border-color': '#E91E63',
      'border-width': 4,
      'border-style': 'double',
    },
  },
  {
    selector: 'node.task-has-note',
    css: {
      'background-image': NOTE_DOT_SVG,
      'background-image-opacity': 1,
      'background-width': '100%',
      'background-height': '100%',
      'background-width-relative-to': 'inner',
      'background-height-relative-to': 'inner',
      'background-position-x': '50%',
      'background-position-y': '50%',
      'background-fit': 'none',
      'background-repeat': 'no-repeat',
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
