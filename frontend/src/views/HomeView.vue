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
            <v-list-item v-for="item in navItems" :key="item.title" :to="item.to" :prepend-icon="item.icon">
              <v-list-item-title>{{ item.title }}</v-list-item-title>
              <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
            </v-list-item>
          </v-list> -->

          <!-- <v-divider class="my-4" /> -->

          <v-row>
            <v-col cols="12" md="6">
              <v-list bg-color="transparent">
                <v-list-item v-for="item in navItems" :key="item.title" :to="item.to" :prepend-icon="item.icon">
                  <v-list-item-title>{{ item.title }}</v-list-item-title>
                  <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
            <v-col cols="12" md="6" class="d-flex flex-column align-stretch home-side-cards ga-4">
              <v-card variant="plain">
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

              <v-card v-if="latestNote" variant="tonal" color="primary" class="latest-update-card">
                <v-card-title class="d-flex align-center justify-space-between flex-wrap ga-2">
                  <div class="d-flex align-center">
                    <v-icon class="mr-2">mdi-new-box</v-icon>
                    Latest Update
                  </div>
                  <v-chip size="small" variant="outlined">v{{ latestNote.version }}</v-chip>
                </v-card-title>
                <v-card-text>
                  <div v-if="latestNote.date" class="text-caption text-medium-emphasis mb-2">{{ latestNote.date }}</div>
                  <div class="text-body-2 mb-3">{{ latestNote.highlights[0] || 'Recent workflow and UI improvements are available.' }}</div>
                  <v-list bg-color="transparent" density="compact" class="pa-0 mb-2">
                    <v-list-item v-for="highlight in latestNote.highlights.slice(1, 3)" :key="highlight" class="px-0">
                      <template #prepend>
                        <v-icon size="small" color="primary">mdi-chevron-right</v-icon>
                      </template>
                      <v-list-item-title class="text-body-2 home-highlight">{{ highlight }}</v-list-item-title>
                    </v-list-item>
                  </v-list>
                  <v-btn variant="outlined" size="small" :to="{ name: 'whats-new' }">
                    View What's New
                  </v-btn>
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
          :src="seadLogo"
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
import seadLogo from '@/assets/images/SEAD-logo-subtext.svg'
import { useWhatsNew } from '@/composables/useWhatsNew'

const navItems = [
  {
    title: 'Projects',
    description: 'Manage project files',
    icon: 'mdi-file-document-multiple',
    to: { name: 'projects' },
  },
  {
    title: 'Data Sources',
    description: 'Configure database connections',
    icon: 'mdi-database',
    to: { name: 'data-sources' },
  },
  {
    title: 'Settings',
    description: 'Configure editor preferences',
    icon: 'mdi-cog',
    to: { name: 'settings' },
  },
  {
    title: "What's New",
    description: 'See the latest user-facing changes',
    icon: 'mdi-new-box',
    to: { name: 'whats-new' },
  },
]

const healthStatus = ref({
  isHealthy: false,
  version: '',
  environment: '',
})

const { latestNote, loadLatestNote } = useWhatsNew()

onMounted(async () => {
  try {
    await loadLatestNote()
  } catch (loadError) {
    console.error('Failed to load latest release note:', loadError)
  }

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

.home-side-cards {
  min-height: 100%;
}

.latest-update-card {
  border: 1px solid rgba(var(--v-theme-primary), 0.18);
}

.home-highlight {
  white-space: normal;
}

.sead-footer-logo {
  opacity: 0.1;
  transition: opacity 0.3s ease;
}

.sead-footer-logo:hover {
  opacity: 0.15;
}
</style>
