<template>
  <v-container>
    <!-- Session Status Bar -->
    <v-alert v-if="hasActiveSession" type="info" variant="tonal" class="mb-4">
      <v-row align="center">
        <v-col>
          <strong>Editing:</strong> {{ projectName }}
          <span class="ml-2 text-caption">Version {{ version }}</span>
          <v-chip v-if="isModified" size="x-small" color="warning" class="ml-2"> Modified </v-chip>
        </v-col>
        <v-col cols="auto">
          <v-btn size="small" color="primary" :loading="loading" :disabled="!isModified" @click="handleSave">
            Save
          </v-btn>
          <v-btn size="small" variant="text" class="ml-2" @click="handleClose"> Close Session </v-btn>
        </v-col>
      </v-row>
    </v-alert>

    <!-- Concurrent Edit Warning -->
    <v-alert v-if="concurrentEditWarning" type="warning" variant="tonal" closable class="mb-4">
      <v-row align="center">
        <v-col>
          {{ concurrentEditWarning }}
        </v-col>
        <v-col cols="auto">
          <v-btn size="small" variant="outlined" @click="refreshActiveSessions"> Refresh </v-btn>
        </v-col>
      </v-row>

      <!-- List other active sessions -->
      <v-list v-if="otherActiveSessions.length > 0" density="compact" class="mt-2">
        <v-list-item v-for="session in otherActiveSessions" :key="session.session_id">
          <template #prepend>
            <v-icon>mdi-account</v-icon>
          </template>
          <v-list-item-title>
            {{ session.user_id || 'Anonymous User' }}
          </v-list-item-title>
          <v-list-item-subtitle> Active since {{ formatTime(session.loaded_at) }} </v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-alert>

    <!-- Project Selector -->
    <v-card v-if="!hasActiveSession" class="mb-4">
      <v-card-title>Select Project</v-card-title>
      <v-card-text>
        <v-select
          v-model="selectedProjectName"
          :items="projectNames"
          label="Project"
          hint="Select a project to start editing"
          persistent-hint
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" :disabled="!selectedProjectName" :loading="loading" @click="handleStartSession">
          Start Session
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- Error Display -->
    <v-alert v-if="error" type="error" variant="tonal" closable class="mb-4" @click:close="error = null">
      {{ error }}
    </v-alert>

    <!-- Content Area -->
    <div v-if="hasActiveSession">
      <!-- Your project editing UI goes here -->
      <slot />
    </div>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSession } from '@/composables'
import { useProjectStore } from '@/stores'

const projectStore = useProjectStore()
const {
  hasActiveSession,
  projectName,
  version,
  isModified,
  loading,
  error,
  concurrentEditWarning,
  otherActiveSessions,
  startSession,
  endSession,
  saveWithVersionCheck,
  checkConcurrentEditors,
} = useSession()

const selectedProjectName = ref<string | null>(null)

const projectNames = computed(() => {
  return projectStore.sortedProjects.map((c) => c.name)
})

// Fetch project on mount
onMounted(async () => {
  try {
    await projectStore.fetchProjects()
  } catch (err) {
    console.error('Failed to fetch projects:', err)
  }
})

// Cleanup on unmount
onUnmounted(async () => {
  if (hasActiveSession.value) {
    if (isModified.value) {
      const shouldSave = confirm('You have unsaved changes. Save before closing?')
      if (shouldSave) {
        await handleSave()
      }
    }
    await endSession()
  }
})

async function handleStartSession() {
  if (!selectedProjectName.value) return

  try {
    await startSession(selectedProjectName.value)
    await projectStore.selectProject(selectedProjectName.value)
  } catch (err) {
    console.error('Failed to start session:', err)
  }
}

async function handleSave() {
  try {
    await saveWithVersionCheck()
    // Show success message
    console.log('Project saved successfully')
  } catch (err: any) {
    console.error('Failed to save:', err)

    // Handle conflict
    if (err.message.includes('modified by another user')) {
      const shouldReload = confirm(
        'This project was modified by another user. ' + 'Would you like to reload it? (Your changes will be lost)'
      )
      if (shouldReload) {
        await projectStore.selectProject(projectName.value!)
      }
    }
  }
}

async function handleClose() {
  if (isModified.value) {
    const shouldSave = confirm('You have unsaved changes. Save before closing?')
    if (shouldSave) {
      await handleSave()
    }
  }

  await endSession()
  selectedProjectName.value = null
}

async function refreshActiveSessions() {
  const result = checkConcurrentEditors()
  console.log('Active sessions:', result)
}

function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString()
}
</script>
