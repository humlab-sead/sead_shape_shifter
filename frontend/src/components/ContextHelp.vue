<template>
  <div v-if="!rail" class="context-help">
    <v-expansion-panels variant="accordion" :model-value="expanded ? [0] : []">
      <v-expansion-panel>
        <v-expansion-panel-title @click="expanded = !expanded">
          <div class="d-flex align-center">
            <v-icon size="small" class="mr-2">mdi-help-circle-outline</v-icon>
            <span class="text-body-2 font-weight-medium">Context Help</span>
          </div>
        </v-expansion-panel-title>
        
        <v-expansion-panel-text>
          <div v-if="helpContent" class="help-content">
            <div v-if="helpContent.title" class="text-subtitle-2 font-weight-bold mb-2">
              {{ helpContent.title }}
            </div>
            
            <div v-if="helpContent.description" class="text-caption mb-3">
              {{ helpContent.description }}
            </div>
            
            <div v-if="helpContent.tips && helpContent.tips.length > 0" class="tips-section mt-3">
              <div class="text-caption font-weight-medium mb-1 text-medium-emphasis">Tips</div>
              <div
                v-for="(tip, index) in helpContent.tips"
                :key="index"
                class="tip-item"
              >
                <span class="tip-bullet">•</span>
                <span class="tip-text" v-html="tip" />
              </div>
            </div>
            
            <div v-if="helpContent.shortcuts && helpContent.shortcuts.length > 0" class="shortcuts-section mt-3">
              <div class="text-caption font-weight-medium mb-1 text-medium-emphasis">Shortcuts</div>
              <div
                v-for="(shortcut, index) in helpContent.shortcuts"
                :key="index"
                class="shortcut-item"
              >
                <div class="shortcut-keys">{{ shortcut.keys }}</div>
                <div class="shortcut-action">{{ shortcut.action }}</div>
              </div>
            </div>
          </div>
          
          <div v-else class="text-caption text-grey">
            No help available for this view.
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

interface HelpContent {
  title: string
  description?: string
  tips?: string[]
  shortcuts?: Array<{ keys: string; action: string }>
}

interface Props {
  rail?: boolean
}

defineProps<Props>()

const route = useRoute()
const expanded = ref(true)

// Help content for different contexts
const helpContentMap: Record<string, HelpContent> = {
  'home': {
    title: 'Welcome to SEAD Shape Shifter',
    description: 'A tool for transforming and normalizing data for the SEAD database.',
    tips: [
      'Create a new project to get started'
    ]
  },
  'projects': {
    title: 'Project Management',
    description: 'Manage your data transformation projects.',
    tips: [
      'Click a project to open it',
      'Use the search bar to filter projects',
      'Projects are stored as YAML files'
    ],
    shortcuts: [
      { keys: 'Ctrl+N', action: 'New Project' },
      { keys: 'Ctrl+S', action: 'Save Changes' }
    ]
  },
  'project-detail-dependencies': {
    title: 'Dependency Graph',
    description: 'Visualize entity dependencies, source lineage, and task status.',
    tips: [
      'Click an entity node to open the quick YAML drawer.',
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
      '<span style="color: #4CAF50; font-weight: 600;">Double green borders</span> mark materialized entities with cached data.'
    ],
    shortcuts: [
      { keys: 'Click', action: 'Open quick YAML drawer' },
      { keys: 'Double-click', action: 'Open full entity editor' },
      { keys: 'Ctrl/Cmd + Double-click', action: 'Open YAML tab in editor' },
      { keys: 'Right-click', action: 'Open context menu and task actions' },
      { keys: 'Drag', action: 'Move node in custom layout mode' }
    ]
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
      'Materialized badges indicate cached entity data; materialize or unmaterialize from the editor when you need to freeze or refresh derived output.'
    ],
    shortcuts: [
      { keys: 'Esc', action: 'Close the entity editor' },
      { keys: 'Ctrl+Shift+P', action: 'Toggle split preview view in the entity editor' }
    ]
  },
  'project-detail-validation': {
    title: 'Validation',
    description: 'Check project configuration for errors.',
    tips: [
      'Red errors must be fixed before execution',
      'Yellow warnings should be reviewed',
      'Click errors to see details and fixes',
      'Validate data to check actual values'
    ]
  },
  'project-detail-data-sources': {
    title: 'Data Sources',
    description: 'Configure database connections and files.',
    tips: [
      'Add multiple data sources',
      'Test connections before use',
      'Use environment variables for credentials',
      'Supported: PostgreSQL, SQLite, MS Access, CSV, Excel'
    ]
  },
  'data-sources': {
    title: 'Data Source Management',
    description: 'Manage database connections across projects.',
    tips: [
      'Shared data sources available to all projects',
      'Test connections to verify settings'
    ]
  },
  'schema-explorer': {
    title: 'Schema Explorer',
    description: 'Browse database schemas and tables.',
    tips: [
      'Select a data source to explore',
      'View table structures and columns',
      'Use this to plan your entities',
      'Check data types and constraints'
    ]
  },
  'query-tester': {
    title: 'Query Tester',
    description: 'Test SQL queries before using them.',
    tips: [
      'Write and test queries safely',
      'Preview results before adding to entities',
      'Use this to debug query issues',
      'Check column names and data'
    ]
  }
}

const helpContent = computed(() => {
  const routeName = route.name as string
  
  // For project detail views, include the active tab
  if (routeName === 'project-detail' && route.query.tab) {
    const tabKey = `project-detail-${route.query.tab}`
    return helpContentMap[tabKey] || null
  }
  
  return helpContentMap[routeName] || null
})
</script>

<style scoped>
.context-help {
  margin: 0.5rem;
}

.help-content {
  font-size: 0.8125rem;
  line-height: 1.4;
}

.tips-section,
.shortcuts-section {
  margin-top: 0.75rem;
}

.tip-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 0.375rem;
  font-size: 0.75rem;
  line-height: 1.3;
}

.tip-bullet {
  color: rgb(var(--v-theme-primary));
  margin-right: 0.375rem;
  flex-shrink: 0;
  font-weight: bold;
}

.tip-text {
  flex: 1;
  word-wrap: break-word;
  overflow-wrap: break-word;
  hyphens: auto;
}

.shortcut-item {
  display: flex;
  flex-direction: column;
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  line-height: 1.3;
}

.shortcut-keys {
  font-weight: 600;
  color: rgb(var(--v-theme-secondary));
  font-family: 'Courier New', monospace;
  font-size: 0.6875rem;
  margin-bottom: 0.125rem;
}

.shortcut-action {
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.8;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
</style>
