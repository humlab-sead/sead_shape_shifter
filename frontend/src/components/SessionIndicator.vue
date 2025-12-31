<template>
  <v-alert v-if="hasActiveSession" density="compact" variant="outlined" :color="alertColor" class="mb-4">
    <v-row align="center" no-gutters>
      <v-col>
        <div class="d-flex align-center">
          <v-icon :icon="alertIcon" size="small" class="mr-2" />
          <span class="text-body-2">
            <strong>Session active:</strong> {{ projectName }}
            <v-chip v-if="isModified" size="x-small" color="warning" variant="flat" class="ml-2"> Unsaved </v-chip>
            <span v-if="version" class="ml-2 text-caption text-grey"> v{{ version }} </span>
          </span>
        </div>
      </v-col>
      <v-col cols="auto" class="d-flex gap-2">
        <v-btn
          v-if="concurrentEditWarning"
          size="x-small"
          color="warning"
          variant="tonal"
          prepend-icon="mdi-alert"
          @click="showConcurrentWarning = !showConcurrentWarning"
        >
          {{ concurrentEditors }} {{ concurrentEditors === 1 ? 'Editor' : 'Editors' }}
        </v-btn>
        <v-btn size="x-small" variant="text" @click="handleCloseSession"> Close </v-btn>
      </v-col>
    </v-row>

    <!-- Concurrent Edit Warning Expansion -->
    <v-expand-transition>
      <div
        v-if="showConcurrentWarning && concurrentEditWarning"
        class="mt-2 pt-2"
        style="border-top: 1px solid rgba(var(--v-theme-warning), 0.3)"
      >
        <v-icon icon="mdi-alert" color="warning" size="small" class="mr-2" />
        <span class="text-caption">
          <strong>Warning:</strong> {{ concurrentEditors }} other
          {{ concurrentEditors === 1 ? 'session is' : 'sessions are' }} editing this project. Changes may
          conflict. Save carefully.
        </span>
      </div>
    </v-expand-transition>
  </v-alert>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSession } from '@/composables/useSession'

interface Props {
  projectName: string
}

const props = defineProps<Props>()

const { hasActiveSession, isModified, version, concurrentEditWarning, otherActiveSessions, endSession } = useSession()

const showConcurrentWarning = ref(false)

const concurrentEditors = computed(() => otherActiveSessions.value.length)

const alertColor = computed(() => {
  if (concurrentEditWarning.value) return 'warning'
  if (isModified.value) return 'info'
  return 'success'
})

const alertIcon = computed(() => {
  if (concurrentEditWarning.value) return 'mdi-alert-circle'
  if (isModified.value) return 'mdi-pencil-circle'
  return 'mdi-check-circle'
})

async function handleCloseSession() {
  if (isModified.value) {
    const confirmed = confirm('You have unsaved changes. Close session anyway?')
    if (!confirmed) return
  }
  await endSession()
}
</script>
