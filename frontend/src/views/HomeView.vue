<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="text-h4 mb-4">
            <v-icon icon="mdi-shape" size="large" class="mr-2" />
            Shape Shifter Configuration Editor
          </v-card-title>
          <v-card-text>
            <p class="text-h6 mb-4">Welcome to the Configuration Editor</p>
            <v-alert type="info" variant="tonal" class="mb-4">
              This is a visual editor for Shape Shifter YAML configuration files.
            </v-alert>
            
            <v-list>
              <v-list-item
                v-for="item in navItems"
                :key="item.path"
                :to="item.path"
                :prepend-icon="item.icon"
              >
                <v-list-item-title>{{ item.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-divider class="my-4" />

            <v-row>
              <v-col cols="12" md="6">
                <v-card variant="outlined">
                  <v-card-title>Backend Status</v-card-title>
                  <v-card-text>
                    <v-chip
                      :color="healthStatus.isHealthy ? 'success' : 'error'"
                      :prepend-icon="healthStatus.isHealthy ? 'mdi-check-circle' : 'mdi-alert-circle'"
                    >
                      {{ healthStatus.isHealthy ? 'Connected' : 'Disconnected' }}
                    </v-chip>
                    <div v-if="healthStatus.isHealthy" class="mt-2">
                      <div><strong>Version:</strong> {{ healthStatus.version }}</div>
                      <div><strong>Environment:</strong> {{ healthStatus.environment }}</div>
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined">
                  <v-card-title>Quick Start</v-card-title>
                  <v-card-text>
                    <ol>
                      <li>Load a configuration file</li>
                      <li>Edit entities and dependencies</li>
                      <li>Validate your changes</li>
                      <li>Save the configuration</li>
                    </ol>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const navItems = [
  {
    title: 'Entities',
    description: 'Manage entities and their properties',
    icon: 'mdi-table',
    path: '/entities',
  },
  {
    title: 'Dependency Graph',
    description: 'Visualize entity dependencies',
    icon: 'mdi-graph',
    path: '/graph',
  },
  {
    title: 'Validation',
    description: 'Check configuration for errors',
    icon: 'mdi-check-circle',
    path: '/validation',
  },
  {
    title: 'Settings',
    description: 'Configure editor preferences',
    icon: 'mdi-cog',
    path: '/settings',
  },
]

const healthStatus = ref({
  isHealthy: false,
  version: '',
  environment: '',
})

onMounted(async () => {
  try {
    const response = await axios.get('/api/v1/health')
    healthStatus.value = {
      isHealthy: true,
      version: response.data.version,
      environment: response.data.environment,
    }
  } catch (error) {
    console.error('Failed to check backend health:', error)
  }
})
</script>
