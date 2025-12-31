<template>
  <div class="dependency-graph">
    <!-- Circular Dependencies Alert -->
    <circular-dependency-alert v-if="hasCircularDependencies" :cycles="cycles" class="mb-4" />

    <!-- Graph Controls -->
    <v-card variant="outlined" class="mb-4">
      <v-card-text class="d-flex align-center gap-4">
        <v-btn-toggle v-model="layoutType" mandatory density="compact">
          <v-btn value="hierarchical" prepend-icon="mdi-file-tree"> Hierarchical </v-btn>
          <v-btn value="force" prepend-icon="mdi-vector-arrange-above"> Force-Directed </v-btn>
        </v-btn-toggle>

        <v-divider vertical />

        <v-switch v-model="showLabels" label="Show Labels" density="compact" hide-details />

        <v-switch
          v-model="highlightCycles"
          label="Highlight Cycles"
          density="compact"
          hide-details
          :disabled="!hasCircularDependencies"
        />

        <v-spacer />

        <v-btn variant="outlined" prepend-icon="mdi-refresh" :loading="loading" @click="handleRefresh"> Refresh </v-btn>

        <v-chip prepend-icon="mdi-cube-outline"> {{ statistics.nodeCount }} nodes </v-chip>
        <v-chip prepend-icon="mdi-arrow-right"> {{ statistics.edgeCount }} edges </v-chip>
      </v-card-text>
    </v-card>

    <!-- Loading State -->
    <v-card v-if="loading" variant="outlined" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
      <p class="mt-4 text-grey">Loading dependency graph...</p>
    </v-card>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" variant="tonal">
      <v-alert-title>Error Loading Graph</v-alert-title>
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="handleRefresh">Retry</v-btn>
      </template>
    </v-alert>

    <!-- Graph Container -->
    <v-card v-else-if="graphData" variant="outlined" style="min-height: 600px">
      <div ref="graphContainer" class="graph-container" />
    </v-card>

    <!-- Empty State -->
    <v-card v-else variant="outlined" class="text-center py-12">
      <v-icon icon="mdi-graph-outline" size="64" color="grey" />
      <h3 class="text-h6 mt-4 mb-2">No Graph Data</h3>
      <p class="text-grey mb-4">No dependency data available for this project</p>
    </v-card>

    <!-- Entity Details Drawer -->
    <v-navigation-drawer v-model="showDetailsDrawer" location="right" temporary width="400">
      <template v-if="selectedNode">
        <v-toolbar color="primary">
          <v-toolbar-title>{{ selectedNode.label }}</v-toolbar-title>
          <v-btn icon="mdi-close" @click="showDetailsDrawer = false" />
        </v-toolbar>

        <v-list>
          <v-list-item>
            <v-list-item-title>Type</v-list-item-title>
            <v-list-item-subtitle>{{ selectedNode.data?.type || 'Unknown' }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Topological Order</v-list-item-title>
            <v-list-item-subtitle>{{ selectedNode.topological_order ?? 'N/A' }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Dependencies</v-list-item-title>
            <v-list-item-subtitle>
              <v-chip v-for="dep in getDependenciesOf(selectedNode.id)" :key="dep" size="small" class="mr-1 mt-1">
                {{ dep }}
              </v-chip>
              <span v-if="getDependenciesOf(selectedNode.id).length === 0">None</span>
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Dependents</v-list-item-title>
            <v-list-item-subtitle>
              <v-chip
                v-for="dependent in getDependentsOf(selectedNode.id)"
                :key="dependent"
                size="small"
                class="mr-1 mt-1"
              >
                {{ dependent }}
              </v-chip>
              <span v-if="getDependentsOf(selectedNode.id).length === 0">None</span>
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="isInCycle(selectedNode.id)">
            <v-alert type="warning" variant="tonal" density="compact">
              This entity is part of a circular dependency
            </v-alert>
          </v-list-item>
        </v-list>

        <v-divider />

        <v-card-actions>
          <v-btn variant="text" prepend-icon="mdi-pencil" block @click="handleEditEntity(selectedNode.id)">
            Edit Entity
          </v-btn>
        </v-card-actions>
      </template>
    </v-navigation-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useDependencies } from '@/composables'
import CircularDependencyAlert from '@/components/dependencies/CircularDependencyAlert.vue'
import type { GraphNode } from '@/types'

// Extend GraphNode for force-directed layout with velocity properties
interface LayoutNode extends GraphNode {
  vx?: number
  vy?: number
}

// Props
const props = defineProps<{
  projectName: string
}>()

// Emits
const emit = defineEmits<{
  'edit-entity': [entityName: string]
}>()

// Composables
const {
  graphData,
  loading,
  error,
  hasCircularDependencies,
  cycles,
  statistics,
  fetch,
  getDependenciesOf,
  getDependentsOf,
  isInCycle,
  clearError,
} = useDependencies({
  projectName: props.projectName,
  autoFetch: true,
})

// Local state
const graphContainer = ref<HTMLElement | null>(null)
const layoutType = ref<'hierarchical' | 'force'>('hierarchical')
const showLabels = ref(true)
const highlightCycles = ref(true)
const showDetailsDrawer = ref(false)
const selectedNode = ref<GraphNode | null>(null)

// Methods
async function handleRefresh() {
  clearError()
  await fetch(props.projectName)
}

function handleEditEntity(entityName: string) {
  showDetailsDrawer.value = false
  emit('edit-entity', entityName)
}

function renderGraph() {
  if (!graphContainer.value || !graphData.value) return

  // Clear previous graph
  graphContainer.value.innerHTML = ''

  const container = graphContainer.value
  const width = container.clientWidth
  const height = 600

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svg.setAttribute('width', String(width))
  svg.setAttribute('height', String(height))
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`)

  // Calculate positions based on layout type
  const nodes: LayoutNode[] = graphData.value.nodes.map((n) => ({ ...n }))

  if (layoutType.value === 'hierarchical') {
    // Hierarchical layout
    const maxDepth = Math.max(...nodes.map((n) => n.data?.depth || 0))
    const levelHeight = height / (maxDepth + 2)

    nodes.forEach((node) => {
      const depth = node.data?.depth || 0
      const nodesAtLevel = nodes.filter((n) => (n.data?.depth || 0) === depth)
      const levelIndex = nodesAtLevel.indexOf(node)
      const levelWidth = width / (nodesAtLevel.length + 1)

      node.x = levelWidth * (levelIndex + 1)
      node.y = levelHeight * (depth + 1)
    })
  } else {
    // Force-directed layout (simple physics simulation)
    // Initialize random positions
    nodes.forEach((node) => {
      node.x = node.x ?? Math.random() * width
      node.y = node.y ?? Math.random() * height
      node.vx = 0
      node.vy = 0
    })

    // Run simulation
    const iterations = 100
    const repulsion = 5000
    const attraction = 0.01
    const damping = 0.9

    for (let i = 0; i < iterations; i++) {
      // Apply repulsion between all nodes
      for (let j = 0; j < nodes.length; j++) {
        const nodeJ = nodes[j]
        if (!nodeJ) continue

        for (let k = j + 1; k < nodes.length; k++) {
          const nodeK = nodes[k]
          if (!nodeK) continue

          const dx = (nodeK.x ?? 0) - (nodeJ.x ?? 0)
          const dy = (nodeK.y ?? 0) - (nodeJ.y ?? 0)
          const distance = Math.sqrt(dx * dx + dy * dy) || 1
          const force = repulsion / (distance * distance)

          nodeJ.vx = (nodeJ.vx ?? 0) - (dx / distance) * force
          nodeJ.vy = (nodeJ.vy ?? 0) - (dy / distance) * force
          nodeK.vx = (nodeK.vx ?? 0) + (dx / distance) * force
          nodeK.vy = (nodeK.vy ?? 0) + (dy / distance) * force
        }
      }

      // Apply attraction along edges
      graphData.value.edges.forEach((edge) => {
        const source = nodes.find((n) => n.id === edge.source)
        const target = nodes.find((n) => n.id === edge.target)
        if (source && target) {
          const dx = (target.x ?? 0) - (source.x ?? 0)
          const dy = (target.y ?? 0) - (source.y ?? 0)
          const force = attraction

          source.vx = (source.vx ?? 0) + dx * force
          source.vy = (source.vy ?? 0) + dy * force
          target.vx = (target.vx ?? 0) - dx * force
          target.vy = (target.vy ?? 0) - dy * force
        }
      })

      // Update positions with damping
      nodes.forEach((node) => {
        node.x = (node.x ?? 0) + (node.vx ?? 0)
        node.y = (node.y ?? 0) + (node.vy ?? 0)
        node.vx = (node.vx ?? 0) * damping
        node.vy = (node.vy ?? 0) * damping

        // Keep nodes within bounds
        node.x = Math.max(50, Math.min(width - 50, node.x))
        node.y = Math.max(50, Math.min(height - 50, node.y))
      })
    }
  }

  // Draw edges
  graphData.value.edges.forEach((edge) => {
    const sourceNode = nodes.find((n) => n.id === edge.source)
    const targetNode = nodes.find((n) => n.id === edge.target)

    if (sourceNode && targetNode) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
      line.setAttribute('x1', String(sourceNode.x))
      line.setAttribute('y1', String(sourceNode.y))
      line.setAttribute('x2', String(targetNode.x))
      line.setAttribute('y2', String(targetNode.y))
      line.setAttribute(
        'stroke',
        highlightCycles.value &&
          cycles.value.some((cycle) => cycle.includes(edge.source) && cycle.includes(edge.target))
          ? '#ef5350'
          : '#999'
      )
      line.setAttribute('stroke-width', '2')
      line.setAttribute('marker-end', 'url(#arrowhead)')
      svg.appendChild(line)
    }
  })

  // Add arrowhead marker
  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs')
  const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker')
  marker.setAttribute('id', 'arrowhead')
  marker.setAttribute('viewBox', '0 -5 10 10')
  marker.setAttribute('refX', '15')
  marker.setAttribute('refY', '0')
  marker.setAttribute('markerWidth', '6')
  marker.setAttribute('markerHeight', '6')
  marker.setAttribute('orient', 'auto')
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
  path.setAttribute('d', 'M0,-5L10,0L0,5')
  path.setAttribute('fill', '#999')
  marker.appendChild(path)
  defs.appendChild(marker)
  svg.appendChild(defs)

  // Draw nodes
  nodes.forEach((node) => {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    g.setAttribute('transform', `translate(${node.x},${node.y})`)
    g.style.cursor = 'pointer'

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
    circle.setAttribute('r', '20')
    circle.setAttribute('fill', highlightCycles.value && isInCycle(node.id) ? '#ef5350' : '#1976d2')
    circle.setAttribute('stroke', '#fff')
    circle.setAttribute('stroke-width', '2')
    g.appendChild(circle)

    if (showLabels.value) {
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
      text.setAttribute('text-anchor', 'middle')
      text.setAttribute('dy', '35')
      text.setAttribute('font-size', '12px')
      text.setAttribute('fill', '#333')
      text.textContent = node.label
      g.appendChild(text)
    }

    g.addEventListener('click', () => {
      selectedNode.value = node
      showDetailsDrawer.value = true
    })

    svg.appendChild(g)
  })

  container.appendChild(svg)
}

// Watch for project changes
watch(
  () => props.projectName,
  async (newProject) => {
    if (newProject) {
      await fetch(newProject)
    }
  }
)

// Watch for graph data changes
watch(graphData, async () => {
  await nextTick()
  renderGraph()
})

// Watch for layout/display changes
watch([layoutType, showLabels, highlightCycles], () => {
  renderGraph()
})
</script>

<style scoped>
.graph-container {
  width: 100%;
  height: 600px;
  position: relative;
}

.gap-4 {
  gap: 1rem;
}
</style>
