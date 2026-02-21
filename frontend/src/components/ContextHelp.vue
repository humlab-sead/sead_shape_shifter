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
      'Create a new project to get started',
      'Import existing project configurations',
      'Explore sample projects for examples'
    ]
  },
  'projects': {
    title: 'Project Management',
    description: 'Manage your data transformation projects.',
    tips: [
      'Click a project to open it',
      'Use the search bar to filter projects',
      'Create backups before major changes',
      'Projects are stored as YAML files'
    ],
    shortcuts: [
      { keys: 'Ctrl+N', action: 'New Project' },
      { keys: 'Ctrl+S', action: 'Save Changes' }
    ]
  },
  'project-detail-dependencies': {
    title: 'Dependency Graph',
    description: 'Visualize entity dependencies and data flow.',
    tips: [
      'Right-click nodes for quick actions (Preview, Duplicate, Delete)',
      'Double-click nodes to edit entity configuration',
      'Click nodes to open YAML editor',
      'Drag nodes in custom layout mode to rearrange',
      'Save custom layouts to preserve positions',
      '<strong>Display Options:</strong>',
      '• <em>Show Sources</em> - Toggle databases and files visibility',
      '• <em>Show Source Entities</em> - Toggle tables and sheets visibility',
      '• Both on: Full chain (database → table → entity)',
      '• Only Sources: Direct links (database → entity)',
      '• Only Source Entities: Entity focus (table → entity)',
      '<span style="color: #9C27B0; font-weight: 600;">Purple</span> entities have fixed values (no data source)',
      '<span style="color: #4CAF50; font-weight: 600;">Green</span> entities are SQL sourced (e.g. SEAD)',
      '<span style="color: #2196F3; font-weight: 600;">Blue</span> entities are source from another entity',
      '<span style="color: #f44336; font-weight: 600;">Red</span> nodes/edges indicate circular dependencies',
      'Entity shapes: Ellipse (CSV/file), Rectangle (SQL), Diamond (Fixed values)',
      'Source node icons: 🗄️ Database, 📋 Table, 📊 CSV, 📗 Excel, 📄 Sheet, 📁 File',
      'Source colors: Blue (database), Teal (table), Red (CSV), Green (Excel), Purple (generic)',
      'Solid edges show entity dependencies, dotted edges show source relationships',
      '<span style="color: #4CAF50; font-weight: 600;">Dashed green</span> edges indicate frozen dependencies from materialized entities'
    ],
    shortcuts: [
      { keys: 'Click', action: 'Open YAML editor' },
      { keys: 'Double-click', action: 'Edit entity' },
      { keys: 'Right-click', action: 'Context menu (Preview/Duplicate/Delete)' },
      { keys: 'Drag', action: 'Move node (custom layout)' }
    ]
  },
  'project-detail-entities': {
    title: 'Entity Configuration',
    description: 'Configure data entities and transformations.',
    tips: [
      'Each entity represents a target table',
      'Define data sources and SQL queries',
      'Use "unnest" to transform wide to long format',
      'Map source columns to target columns',
      'Set up foreign key relationships',
      'Use filters to exclude rows'
    ]
  },
  'project-detail-validation': {
    title: 'Validation',
    description: 'Check project configuration for errors.',
    tips: [
      'Red errors must be fixed before execution',
      'Yellow warnings should be reviewed',
      'Click errors to see details and fixes',
      'Use Auto-fix for common issues',
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
      'Test connections to verify settings',
      'Store credentials securely',
      'Use meaningful names for easy reference'
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
