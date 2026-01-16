<template>
  <v-container fluid class="pa-6 d-flex flex-column home-view">
    <div class="flex-grow-1">
      <v-row>
        <v-col cols="12">
          <!-- <div class="text-center mb-8">
            <h1 class="text-h3 mb-2">SEAD Shape Shifter</h1>
            <p class="text-h6 text-grey">Project Editor</p>
          </div> -->
          <!-- <div class="d-flex justify-center mb-8">
            <v-img
              src="src/assets/images/SEAD-logo-with-subtext.png"
              alt="SEAD Logo"
              max-width="50%"
            />
          </div> -->
          <!-- <v-list>
            <v-list-item v-for="item in navItems" :key="item.path" :to="item.path" :prepend-icon="item.icon">
              <v-list-item-title>{{ item.title }}</v-list-item-title>
              <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
            </v-list-item>
          </v-list> -->

          <!-- <v-divider class="my-4" /> -->

          <v-row>
            <v-col cols="12" md="6">
              <v-list bg-color="transparent">
                <v-list-item v-for="item in navItems" :key="item.path" :to="item.path" :prepend-icon="item.icon">
                  <v-list-item-title>{{ item.title }}</v-list-item-title>
                  <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
            <v-col cols="12" md="6" class="d-flex justify-end align-start">
              <v-card variant="plain" class="mt-n4">
                <v-card-title class="pt-0">Backend Status</v-card-title>
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
          </v-row>
        </v-col>
      </v-row>
    </div>

    <!-- SEAD Branding Footer -->
    <v-row class="mt-auto">
      <v-col cols="12" class="d-flex justify-center align-center pb-4">
        <v-img
          src="/src/assets/images/SEAD-logo-subtext.svg"
          alt="Strategic Environmental Archaeology Database"
          width="100%"
          contain
          class="sead-footer-logo"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const navItems = [
  {
    title: 'Projects',
    description: 'Manage project files',
    icon: 'mdi-file-document-multiple',
    path: '/projects',
  },
  {
    title: 'Data Sources',
    description: 'Configure database connections',
    icon: 'mdi-database',
    path: '/data-sources',
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

<style scoped>
.home-view {
  min-height: calc(100vh - 64px);
  height: 100%;
  display: flex !important;
  flex-direction: column !important;
}

.flex-grow-1 {
  flex: 1 1 auto;
}

.sead-footer-logo {
  opacity: 0.1;
  transition: opacity 0.3s ease;
}

.sead-footer-logo:hover {
  opacity: 0.15;
}
</style>
