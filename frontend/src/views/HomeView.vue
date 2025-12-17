<template>
  <v-container fluid class="pa-6">
    <v-row>
      <v-col cols="12">
        <div class="text-center mb-8">
          <v-icon icon="mdi-shape" size="80" color="primary" class="mb-4" />
          <h1 class="text-h3 mb-2">SEAD Shape Shifter</h1>
          <p class="text-h6 text-grey">Configuration Editor</p>
        </div>
            
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
