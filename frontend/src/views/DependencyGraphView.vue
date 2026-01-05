<template>
  <v-container fluid class="pa-6">
    <v-row>
      <v-col>
        <div class="d-flex align-center justify-space-between mb-6">
          <h1 class="text-h4">Dependency Graph</h1>
          <div class="d-flex gap-2">
            <v-select
              v-model="selectedProject"
              :items="projectOptions"
              label="Project"
              variant="outlined"
              density="compact"
              hide-details
              style="min-width: 250px"
            />
            <v-btn variant="outlined" prepend-icon="mdi-refresh" :loading="loading" @click="handleRefresh">
              Refresh
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Circular Dependencies Alert -->
    <circular-dependency-alert v-if="hasCircularDependencies" :cycles="cycles" class="mb-4" />

    <!-- Graph Controls -->
    <v-row>
      <v-col cols="12">
        <v-card variant="outlined" class="mb-4">
          <v-card-text class="d-flex align-center gap-4">
            <v-btn-toggle v-model="layoutType" mandatory density="compact">
              <v-btn value="hierarchical" prepend-icon="mdi-file-tree" size="small"> Hierarchical </v-btn>
              <v-btn value="force" prepend-icon="mdi-vector-arrange-above" size="small"> Force-Directed </v-btn>
            </v-btn-toggle>

            <v-divider vertical />

            <v-switch v-model="showNodeLabels" label="Show Node Labels" density="compact" hide-details />
            <v-switch v-model="showEdgeLabels" label="Show Edge Labels" density="compact" hide-details />

            <v-switch
              v-model="highlightCycles"
              label="Highlight Cycles"
              density="compact"
              hide-details
              :disabled="!hasCircularDependencies"
            />

            <v-spacer />

            <v-btn
              variant="outlined"
              prepend-icon="mdi-information-outline"
              size="small"
              @click="showLegend = !showLegend"
            >
              Legend
            </v-btn>

            <v-chip prepend-icon="mdi-cube-outline"> {{ statistics.nodeCount }} nodes </v-chip>
            <v-chip prepend-icon="mdi-arrow-right"> {{ statistics.edgeCount }} edges </v-chip>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="loading">
      <v-col cols="12" class="text-center py-12">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-grey">Loading dependency graph...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" variant="tonal">
      <v-alert-title>Error Loading Graph</v-alert-title>
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="handleRefresh">Retry</v-btn>
      </template>
    </v-alert>

    <!-- Graph Container -->
    <v-row v-else-if="dependencyGraph">
      <v-col cols="12">
        <v-card variant="outlined">
          <v-card-text class="pa-0">
            <div ref="graphContainer" class="graph-container" />
          </v-card-text>
          <v-card-actions class="justify-end">
            <v-btn variant="text" prepend-icon="mdi-fit-to-screen" size="small" @click="handleFit"> Fit </v-btn>
            <v-btn variant="text" prepend-icon="mdi-magnify-plus" size="small" @click="handleZoomIn"> Zoom In </v-btn>
            <v-btn variant="text" prepend-icon="mdi-magnify-minus" size="small" @click="handleZoomOut">
              Zoom Out
            </v-btn>
            <v-btn variant="text" prepend-icon="mdi-refresh" size="small" @click="handleResetView"> Reset View </v-btn>
            <v-divider vertical class="mx-2" />
            <v-btn variant="text" prepend-icon="mdi-download" size="small" @click="handleExportPNG"> Export PNG </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Empty State -->
    <v-row v-else>
      <v-col cols="12">
        <v-card variant="outlined" class="text-center py-12">
          <v-icon icon="mdi-graph-outline" size="64" color="grey" />
          <h3 class="text-h6 mt-4 mb-2">No Graph Data</h3>
          <p class="text-grey mb-4">Select a project to view its dependency graph</p>
        </v-card>
      </v-col>
    </v-row>

    <!-- Legend Dialog -->
    <v-dialog v-model="showLegend" max-width="500">
      <node-legend :show-source-nodes="false" @close="showLegend = false" />
    </v-dialog>

    <!-- Entity Details Drawer -->
    <v-navigation-drawer v-model="showDetailsDrawer" location="right" temporary width="400">
      <template v-if="selectedNode">
        <v-toolbar color="primary">
          <v-toolbar-title>{{ selectedNode }}</v-toolbar-title>
          <v-btn icon="mdi-close" @click="showDetailsDrawer = false" />
        </v-toolbar>

        <v-list>
          <v-list-item>
            <v-list-item-title>Entity Name</v-list-item-title>
            <v-list-item-subtitle>{{ selectedNodeInfo?.id }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Depth</v-list-item-title>
            <v-list-item-subtitle>{{ selectedNodeInfo?.depth ?? 'N/A' }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Topological Order</v-list-item-title>
            <v-list-item-subtitle>{{ selectedNodeInfo?.topologicalOrder ?? 'N/A' }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Dependencies</v-list-item-title>
            <v-list-item-subtitle>
              <v-chip v-for="dep in selectedNodeInfo?.dependencies ?? []" :key="dep" size="small" class="mr-1 mt-1">
                {{ dep }}
              </v-chip>
              <span v-if="(selectedNodeInfo?.dependencies ?? []).length === 0">None</span>
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Dependents</v-list-item-title>
            <v-list-item-subtitle>
              <v-chip
                v-for="dependent in selectedNodeInfo?.dependents ?? []"
                :key="dependent"
                size="small"
                class="mr-1 mt-1"
              >
                {{ dependent }}
              </v-chip>
              <span v-if="(selectedNodeInfo?.dependents ?? []).length === 0">None</span>
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="isInCycle(selectedNode)">
            <v-alert type="warning" variant="tonal" density="compact">
              This entity is part of a circular dependency
            </v-alert>
          </v-list-item>
        </v-list>

        <v-divider />

        <v-card-actions>
          <v-btn variant="text" prepend-icon="mdi-pencil" block @click="handleEditEntity(selectedNode)">
            Edit Entity
          </v-btn>
        </v-card-actions>
      </template>
    </v-navigation-drawer>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useProjects, useDependencies, useCytoscape } from '@/composables'
import { getNodeInfo } from '@/utils/graphAdapter'
import CircularDependencyAlert from '@/components/dependencies/CircularDependencyAlert.vue'
import NodeLegend from '@/components/dependencies/NodeLegend.vue'

const router = useRouter()
const theme = useTheme()

// Composables
const { projects } = useProjects({ autoFetch: true })
const selectedProject = ref<string | null>(null)

const { dependencyGraph, loading, error, hasCircularDependencies, cycles, statistics, fetch, isInCycle, clearError } =
  useDependencies({
    projectName: selectedProject.value ?? undefined,
    autoFetch: false,
  })

// Local state
const graphContainer = ref<HTMLElement | null>(null)
const layoutType = ref<'hierarchical' | 'force'>('hierarchical')
const showNodeLabels = ref(true)
const showEdgeLabels = ref(true)
const highlightCycles = ref(true)
const showLegend = ref(false)
const showDetailsDrawer = ref(false)
const selectedNode = ref<string | null>(null)

// Computed
const projectOptions = computed(() => {
  return projects.value.map((c) => ({
    title: c.name,
    value: c.name,
  }))
})

const isDark = computed(() => theme.global.current.value.dark)

const selectedNodeInfo = computed(() => {
  if (!selectedNode.value) return null
  return getNodeInfo(selectedNode.value, dependencyGraph.value)
})

// Cytoscape integration
const { fit, zoomIn, zoomOut, reset, exportPNG } = useCytoscape({
  container: graphContainer,
  graphData: dependencyGraph,
  layoutType,
  showNodeLabels,
  showEdgeLabels,
  highlightCycles,
  cycles,
  isDark,
  onNodeClick: (nodeId: string) => {
    selectedNode.value = nodeId
    showDetailsDrawer.value = true
  },
  onBackgroundClick: () => {
    selectedNode.value = null
    showDetailsDrawer.value = false
  },
})

// Methods
async function handleRefresh() {
  if (selectedProject.value) {
    clearError()
    await fetch(selectedProject.value)
  }
}

function handleEditEntity(entityName: string) {
  if (selectedProject.value) {
    router.push({
      name: 'project-detail',
      params: { name: selectedProject.value },
      query: { entity: entityName },
    })
  }
}

function handleFit() {
  fit()
}

function handleZoomIn() {
  zoomIn()
}

function handleZoomOut() {
  zoomOut()
}

function handleResetView() {
  reset()
}

function handleExportPNG() {
  const png = exportPNG()
  if (png) {
    const link = document.createElement('a')
    link.download = `dependency-graph-${selectedProject.value || 'export'}.png`
    link.href = png
    link.click()
  }
}

// Watch for project changes
watch(selectedProject, async (newProject) => {
  if (newProject) {
    await fetch(newProject)
  }
})

// Select first project on mount
onMounted(() => {
  if (projects.value.length > 0 && !selectedProject.value) {
    selectedProject.value = projects.value[0]?.name || null
  }
})
</script>

<style scoped>
.graph-container {
  width: 100%;
  height: 600px;
  min-height: 600px;
  position: relative;
  background: transparent;
}

.gap-2 {
  gap: 0.5rem;
}

.gap-4 {
  gap: 1rem;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-data {
  background-color: #1976d2;
}

.legend-sql {
  background-color: #2e7d32;
}

.legend-fixed {
  background-color: #6a1b9a;
}
</style>
