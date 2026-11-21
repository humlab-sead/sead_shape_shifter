/**
 * Typed registry for the sidebar Context Help topics.
 *
 * One module owns the topic shape, the static topics, and the rules that pick a
 * topic from the current view. Adding help for a new view or configuration
 * sub-tab means adding an entry here, not editing the help component.
 */

import {
  reconciliationHelp,
  reconciliationWorkspaceHelp,
  type ReconciliationHelpItem,
} from '@/components/reconciliation/reconciliationHelp'
import type { SelectionMode } from '@/types/reconciliation'

export interface HelpGroup {
  title: string
  tips: string[]
}

export interface HelpShortcut {
  keys: string
  action: string
}

export interface HelpTopic {
  title: string
  description?: string
  tips?: string[]
  groups?: HelpGroup[]
  shortcuts?: HelpShortcut[]
  rowActions?: ReconciliationHelpItem[]
}

/** The view details that decide which topic the sidebar shows. */
export interface HelpContext {
  routeName: string
  tab: string | null
  workspaceActive: boolean
  workspaceMode: SelectionMode
}

/** Workspace help follows the Search/Browse mode shown in the open workspace. */
export function reconciliationWorkspaceTopic(mode: SelectionMode): HelpTopic {
  const modeHelp = reconciliationWorkspaceHelp.modes[mode]
  return {
    title: reconciliationWorkspaceHelp.title,
    description: reconciliationWorkspaceHelp.description,
    groups: [
      { title: modeHelp.label, tips: modeHelp.tips },
      { title: reconciliationWorkspaceHelp.saving.label, tips: reconciliationWorkspaceHelp.saving.tips },
    ],
    shortcuts: reconciliationWorkspaceHelp.shortcuts,
  }
}

/**
 * Static topics keyed by route name, or by `<route-name>-<tab>` for tabbed
 * views. Keys that no route uses are harmless.
 */
export const HELP_TOPICS: Record<string, HelpTopic> = {
  home: {
    title: 'Welcome to SEAD Shape Shifter',
    description: 'A tool for transforming and normalizing data for the SEAD database.',
    tips: ['Create a new project to get started'],
  },
  projects: {
    title: 'Project Management',
    description: 'Manage your data transformation projects.',
    tips: ['Click a project to open it', 'Use the search bar to filter projects', 'Projects are stored as YAML files'],
    shortcuts: [
      { keys: 'Ctrl+N', action: 'New Project' },
      { keys: 'Ctrl+S', action: 'Save Changes' },
    ],
  },
  'project-detail-dependencies': {
    title: 'Dependency Graph',
    description: 'Visualize entity dependencies, source lineage, and task status.',
    tips: [
      'Click an entity node to open the quick Task Note/YAML drawer.',
      'Double-click an entity node to open the full editor overlay.',
      'Use Ctrl/Cmd + double-click to jump straight to the YAML tab in the editor.',
      'Right-click a node for preview, verify, duplicate, delete, task-status actions, and task notes.',
      'Use <strong>Layout</strong> to switch between hierarchical, force-directed, and saved custom positions.',
      'Drag nodes only when using a custom layout, then save the layout to preserve positions.',
      'Use <strong>Display</strong> to toggle node labels, edge labels, sources, and source entities.',
      '<em>Show Sources</em> adds databases and files; <em>Show Source Entities</em> adds tables and sheets between sources and entities.',
      'Use <strong>Color By</strong> to switch between entity type and task status. In task mode, a centered dot marks entities with notes.',
      'The floating buttons on the right let you fit, zoom, reset the view, create a new entity, and export PNG.',
      'Solid edges show entity dependencies, dotted edges show source lineage, and dashed green edges show frozen dependencies from materialized entities.',
      '<span style="color: #4CAF50; font-weight: 600;">Double green borders</span> mark materialized entities with cached data.',
    ],
    shortcuts: [
      { keys: 'Click', action: 'Open quick YAML drawer' },
      { keys: 'Double-click', action: 'Open full entity editor' },
      { keys: 'Ctrl/Cmd + Double-click', action: 'Open YAML tab in editor' },
      { keys: 'Right-click', action: 'Open context menu and task actions' },
      { keys: 'Drag', action: 'Move node in custom layout mode' },
    ],
  },
  'project-detail-entities': {
    title: 'Entity Configuration',
    description: 'Create entities, define transformations, and inspect results while you edit.',
    tips: [
      'Use the search box and type filter to narrow large entity lists quickly.',
      'Use <strong>Add Entity</strong> to create a new entity, or the pencil button to edit an existing one.',
      'The editor supports form view, split view, and preview view so you can compare configuration and output side by side.',
      'Use the <strong>YAML</strong> tab when you need direct control over the raw entity configuration.',
      'Set identity fields carefully: <em>system_id</em> is always local, <em>public_id</em> defines exported and FK column names, and <em>business keys</em> control matching and deduplication.',
      'Use the <strong>Foreign Keys</strong>, <strong>Filters</strong>, <strong>Unnest</strong>, <strong>Append</strong>, <strong>Extra Columns</strong>, and <strong>Replace</strong> tabs to model each transformation step explicitly.',
      'Use preview to verify columns, row shape, and source data before saving larger changes.',
      'Fixed entities can be edited as grid values, and some entities may load values from external storage instead of inline YAML.',
      'Materialized badges indicate cached entity data; materialize or unmaterialize from the editor when you need to freeze or refresh derived output.',
    ],
    shortcuts: [
      { keys: 'Esc', action: 'Close the entity editor' },
      { keys: 'Ctrl+Shift+P', action: 'Toggle split preview view in the entity editor' },
    ],
  },
  'project-detail-validation': {
    title: 'Validation',
    description: 'Check project configuration for errors.',
    tips: [
      'Red errors must be fixed before execution',
      'Yellow warnings should be reviewed',
      'Click errors to see details and fixes',
      'Validate data to check actual values',
    ],
  },
  'project-detail-reconciliation': {
    title: reconciliationHelp.title,
    description: reconciliationHelp.description,
    tips: reconciliationHelp.quickTips,
    rowActions: reconciliationHelp.rowActions.filter((action) => action.icon),
  },
  'project-detail-data-sources': {
    title: 'Data Sources',
    description: 'Configure database connections and files.',
    tips: [
      'Add multiple data sources',
      'Test connections before use',
      'Use environment variables for credentials',
      'Supported: PostgreSQL, SQLite, MS Access, CSV, Excel',
    ],
  },
  'data-sources': {
    title: 'Data Source Management',
    description: 'Manage database connections across projects.',
    tips: ['Shared data sources available to all projects', 'Test connections to verify settings'],
  },
  'schema-explorer': {
    title: 'Schema Explorer',
    description: 'Browse database schemas and tables.',
    tips: [
      'Select a data source to explore',
      'View table structures and columns',
      'Use this to plan your entities',
      'Check data types and constraints',
    ],
  },
  'query-tester': {
    title: 'Query Tester',
    description: 'Test SQL queries before using them.',
    tips: [
      'Write and test queries safely',
      'Preview results before adding to entities',
      'Use this to debug query issues',
      'Check column names and data',
    ],
  },
  'whats-new': {
    title: "What's New",
    description: 'Browse recent user-facing updates and workflow improvements.',
    tips: [
      'Open the latest release first for the most relevant changes.',
      'Use this archive to scan feature additions, improvements, and fixes by version.',
      'The home page and startup dialog both link back here if you dismiss them.',
    ],
  },
}

/** Resolve the sidebar topic for the current view, or null when there is none. */
export function resolveHelpTopic(context: HelpContext): HelpTopic | null {
  if (context.routeName === 'project-detail' && context.tab) {
    if (context.tab === 'reconciliation' && context.workspaceActive) {
      return reconciliationWorkspaceTopic(context.workspaceMode)
    }
    return HELP_TOPICS[`project-detail-${context.tab}`] ?? null
  }

  return HELP_TOPICS[context.routeName] ?? null
}
