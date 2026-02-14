<template>
  <v-card variant="elevated" class="legend-card">
    <v-card-title class="d-flex align-center justify-space-between">
      <span>Legend</span>
      <v-btn icon="mdi-close" variant="text" size="small" @click="emit('close')" />
    </v-card-title>

    <v-card-text>
      <div class="legend-section mb-4">
        <h4 class="text-subtitle-2 font-weight-bold mb-3">Entity Nodes</h4>
        <div class="legend-item mb-2">
          <div class="node-preview">
            <div class="node-shape ellipse data" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">Entity (Derived)</span>
            <div class="text-caption text-medium-emphasis">
              Entity derived from another entity
            </div>
          </div>
        </div>

        <div class="legend-item mb-2">
          <div class="node-preview">
            <div class="node-shape ellipse csv" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">CSV File Entity</span>
            <div class="text-caption text-medium-emphasis">
              Data loaded from a CSV file
            </div>
          </div>
        </div>

        <div class="legend-item mb-2">
          <div class="node-preview">
            <div class="node-shape ellipse xlsx" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">Excel Entity (Pandas)</span>
            <div class="text-caption text-medium-emphasis">
              Data loaded from Excel using Pandas
            </div>
          </div>
        </div>

        <div class="legend-item mb-2">
          <div class="node-preview">
            <div class="node-shape ellipse openpyxl" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">Excel Entity (OpenPyXL)</span>
            <div class="text-caption text-medium-emphasis">
              Data loaded from Excel using OpenPyXL
            </div>
          </div>
        </div>

        <div class="legend-item mb-2">
          <div class="node-preview">
            <div class="node-shape rectangle sql" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">SQL Entity</span>
            <div class="text-caption text-medium-emphasis">
              Data derived from a SQL query
            </div>
          </div>
        </div>

        <div class="legend-item">
          <div class="node-preview">
            <div class="node-shape diamond fixed" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">Fixed Values Entity</span>
            <div class="text-caption text-medium-emphasis">
              Entity with manually defined fixed values
            </div>
          </div>
        </div>
      </div>

      <v-divider class="my-3" />

      <div class="legend-section mb-4" v-if="showSources || showSourceEntities">
        <h4 class="text-subtitle-2 font-weight-bold mb-3">Source Nodes</h4>
        <div class="legend-item mb-2" v-if="showSources">
          <div class="node-preview">
            <div class="node-shape barrel datasource" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">Data Source / Database</span>
            <div class="text-caption text-medium-emphasis">
              A database or file-based data source
            </div>
          </div>
        </div>

        <div class="legend-item" v-if="showSourceEntities">
          <div class="node-preview">
            <div class="node-shape small-rectangle table" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">Database Table / Sheet</span>
            <div class="text-caption text-medium-emphasis">
              A specific table or Excel sheet
            </div>
          </div>
        </div>
      </div>

      <v-divider class="my-3" />

      <div class="legend-section">
        <h4 class="text-subtitle-2 font-weight-bold mb-3">Edge Types</h4>
        <div class="legend-item mb-2">
          <div class="edge-preview solid" />
          <div class="legend-text">
            <span class="font-weight-medium">Entity Dependency</span>
            <div class="text-caption text-medium-emphasis">
              One entity depends on another
            </div>
          </div>
        </div>

        <div class="legend-item" v-if="showSources || showSourceEntities">
          <div class="edge-preview dotted" />
          <div class="legend-text">
            <span class="font-weight-medium">Source Relationship</span>
            <div class="text-caption text-medium-emphasis">
              Connection between source nodes and entities
            </div>
          </div>
        </div>
      </div>

      <v-divider class="my-3" />

      <div class="legend-section">
        <h4 class="text-subtitle-2 font-weight-bold mb-3">Node States</h4>
        <div class="legend-item mb-2">
          <div class="node-preview">
            <div class="node-shape small-circle valid" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">Valid / Normal</span>
            <div class="text-caption text-medium-emphasis">
              Node with no issues
            </div>
          </div>
        </div>

        <div class="legend-item">
          <div class="node-preview">
            <div class="node-shape small-circle in-cycle" />
          </div>
          <div class="legend-text">
            <span class="font-weight-medium">In Circular Dependency</span>
            <div class="text-caption text-medium-emphasis">
              Node is part of a circular dependency cycle
            </div>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
defineProps<{
  showSources?: boolean
  showSourceEntities?: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()
</script>

<style scoped>
.legend-section {
  display: flex;
  flex-direction: column;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.node-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  background-color: #f5f5f5;
  border-radius: 4px;
  flex-shrink: 0;
}

.node-shape {
  display: inline-block;
  border: 2px solid #333;
}

.node-shape.ellipse {
  width: 30px;
  height: 24px;
  border-radius: 50%;
}

.node-shape.rectangle {
  width: 28px;
  height: 20px;
  border-radius: 3px;
}

.node-shape.small-rectangle {
  width: 24px;
  height: 18px;
  border-radius: 2px;
}

.node-shape.diamond {
  width: 24px;
  height: 24px;
  transform: rotate(45deg);
}

.node-shape.barrel {
  width: 26px;
  height: 22px;
  border-radius: 6px 6px 3px 3px;
}

.legend-card {
  background-color: rgb(var(--v-theme-surface)) !important;
  color: var(--v-theme-on-surface);
  box-shadow: var(--v-shadow-4);
}

/* Dark theme override */
:deep(.v-card) {
  background-color: rgb(var(--v-theme-surface)) !important;
  opacity: 1 !important;
}

:deep(.v-card-text) {
  background-color: transparent;
}

.node-shape.small-circle {
  width: 18px;
  height: 18px;
  border-radius: 50%;
}

.node-shape.data {
  background-color: #1976d2;
  border-color: #1976d2;
}

.node-shape.csv {
  background-color: #FFA500;
  border-color: #FFA500;
}

.node-shape.xlsx {
  background-color: #00a86b;
  border-color: #00a86b;
}

.node-shape.openpyxl {
  background-color: #20b2aa;
  border-color: #20b2aa;
}

.node-shape.sql {
  background-color: #2e7d32;
  border-color: #2e7d32;
}

.node-shape.fixed {
  background-color: #6a1b9a;
  border-color: #6a1b9a;
}

.node-shape.datasource {
  background-color: #00796b;
  border-color: #00796b;
  border-style: dashed;
}

.node-shape.table {
  background-color: #0097a7;
  border-color: #0097a7;
  border-style: dashed;
}

.node-shape.valid {
  background-color: #2e7d32;
  border-color: #2e7d32;
}

.node-shape.in-cycle {
  background-color: #ef5350;
  border-color: #c62828;
}

.edge-preview {
  width: 50px;
  height: 4px;
  border-radius: 2px;
  flex-shrink: 0;
}

.edge-preview.solid {
  background-color: #666;
  background-image: linear-gradient(90deg, #999 0%, #999 100%);
}

.edge-preview.dotted {
  background-image: repeating-linear-gradient(
    90deg,
    #00796b 0px,
    #00796b 6px,
    transparent 6px,
    transparent 12px
  );
}

.legend-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
