<template>
  <div class="test-run-view">
    <v-container fluid>
      <!-- Header -->
      <v-row class="mb-4">
        <v-col>
          <div class="d-flex justify-space-between align-center">
            <h1 class="text-h4">Project Test Run</h1>
            <div class="d-flex ga-2">
              <v-btn variant="outlined" prepend-icon="mdi-refresh" @click="handleReset" :disabled="isRunning">
                Reset
              </v-btn>
              <v-btn
                color="primary"
                prepend-icon="mdi-play"
                @click="handleStartTest"
                :loading="isRunning"
                :disabled="isRunning || !projectName"
              >
                Run Test
              </v-btn>
            </div>
          </div>
        </v-col>
      </v-row>

      <!-- Project Info and Status -->
      <v-row v-if="projectName" class="mb-4">
        <v-col>
          <v-alert type="info" variant="tonal">
            <div class="d-flex justify-space-between align-center">
              <div><strong>Project:</strong> {{ projectName }}</div>
              <v-chip
                v-if="testResult"
                :color="getStatusColor(testResult.status)"
                :prepend-icon="getStatusIcon(testResult.status)"
                variant="flat"
              >
                {{ testResult.status.toUpperCase() }}
                <v-progress-circular v-if="isPolling" indeterminate size="16" width="2" class="ml-2" />
              </v-chip>
            </div>
          </v-alert>
        </v-col>
      </v-row>

      <!-- Error Alert -->
      <v-row v-if="error" class="mb-4">
        <v-col>
          <v-alert type="error" variant="tonal" closable @click:close="error = null">
            <strong>Error:</strong> {{ error }}
          </v-alert>
        </v-col>
      </v-row>

      <v-divider class="my-4" />

      <!-- Test Project (before run) -->
      <v-row v-if="!testResult">
        <v-col>
          <v-card>
            <v-card-text>
              <TestRunProject
                v-model:options="options"
                v-model:selected-entities="selectedEntities"
                :entities="availableEntities"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Test Progress and Results (after run) -->
      <template v-if="testResult">
        <!-- Progress -->
        <v-row class="mb-4">
          <v-col>
            <v-card>
              <v-card-text>
                <TestRunProgress :progress="testResult" />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Results -->
        <v-row>
          <v-col>
            <v-card>
              <v-card-text>
                <TestRunResults :result="testResult" />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </template>

      <!-- Loading -->
      <v-row v-if="isLoadingProject">
        <v-col class="text-center">
          <v-progress-circular indeterminate size="64" />
          <p class="mt-4">Loading project...</p>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import TestRunProject from '@/components/testrun/TestRunProject.vue'
import TestRunProgress from '@/components/testrun/TestRunProgress.vue'
import TestRunResults from '@/components/testrun/TestRunResults.vue'
import testRunApi from '@/api/testRunApi'
import { projectsApi } from '@/api/projects'
import type { TestRunOptions, TestRunResult } from '@/types/testRun'
import { DEFAULT_TEST_RUN_OPTIONS } from '@/types/testRun'

const route = useRoute()

const projectName = ref<string>(route.params.name as string)
const options = ref<Partial<TestRunOptions>>({ ...DEFAULT_TEST_RUN_OPTIONS })
const selectedEntities = ref<string[]>([])
const availableEntities = ref<string[]>([])
const testResult = ref<TestRunResult | null>(null)
const isRunning = ref(false)
const isLoadingProject = ref(true)
const error = ref<string | null>(null)
const pollInterval = ref<number | null>(null)
const currentRunId = ref<string | null>(null)

// Load project and available entities
onMounted(async () => {
  if (!projectName.value) {
    error.value = 'No project name provided'
    isLoadingProject.value = false
    return
  }

  try {
    isLoadingProject.value = true
    const project = await projectsApi.get(projectName.value)
    availableEntities.value = Object.keys(project.entities || {})
    error.value = null
  } catch (err) {
    console.error('Failed to load project:', err)
    error.value = `Failed to load project: ${err instanceof Error ? err.message : String(err)}`
  } finally {
    isLoadingProject.value = false
  }
})

const isPolling = computed(() => {
  const status = testResult.value?.status
  return status === 'pending' || status === 'running'
})

const getStatusColor = (status: string) => {
  switch (status) {
    case 'pending':
      return 'blue'
    case 'running':
      return 'orange'
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'cancelled':
      return 'grey'
    default:
      return 'default'
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'pending':
      return 'mdi-clock-outline'
    case 'running':
      return 'mdi-play-circle'
    case 'completed':
      return 'mdi-check-circle'
    case 'failed':
      return 'mdi-alert-circle'
    case 'cancelled':
      return 'mdi-close-circle'
    default:
      return 'mdi-help-circle'
  }
}

const stopPolling = () => {
  if (pollInterval.value !== null) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

const pollTestResult = async () => {
  if (!currentRunId.value) return

  try {
    const result = await testRunApi.getTestRun(currentRunId.value)
    testResult.value = result

    // Stop polling if completed, failed, or cancelled
    if (result.status === 'completed' || result.status === 'failed' || result.status === 'cancelled') {
      stopPolling()
      isRunning.value = false

      if (result.status === 'failed') {
        error.value = result.error_message || 'Test run failed'
      }
    }
  } catch (err) {
    console.error('Failed to poll test result:', err)
    stopPolling()
    isRunning.value = false
    error.value = err instanceof Error ? err.message : String(err)
  }
}

const startPolling = () => {
  stopPolling() // Clear any existing interval
  pollInterval.value = window.setInterval(() => {
    pollTestResult()
  }, 2000) // Poll every 2 seconds
}

const handleStartTest = async () => {
  if (!projectName.value) {
    error.value = 'No project selected'
    return
  }

  try {
    isRunning.value = true
    error.value = null

    const testOptions: Partial<TestRunOptions> = {
      ...options.value,
    }

    // Add selected entities if any
    if (selectedEntities.value.length > 0) {
      testOptions.entities = selectedEntities.value
    }

    const result = await testRunApi.startTestRun({
      project_name: projectName.value,
      options: testOptions,
    })

    testResult.value = result
    currentRunId.value = result.run_id

    // Start polling if status is pending or running
    if (result.status === 'pending' || result.status === 'running') {
      startPolling()
    } else {
      // Completed immediately
      isRunning.value = false
      if (result.status === 'failed') {
        error.value = result.error_message || 'Test run failed'
      }
    }
  } catch (err) {
    console.error('Test run failed:', err)
    const errorMessage = err instanceof Error ? err.message : String(err)
    error.value = errorMessage
    isRunning.value = false
  }
}

const handleReset = () => {
  stopPolling()
  testResult.value = null
  currentRunId.value = null
  error.value = null
  options.value = { ...DEFAULT_TEST_RUN_OPTIONS }
  selectedEntities.value = []
  isRunning.value = false
}

// Cleanup polling on unmount
onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.test-run-view {
  padding: 20px;
}
</style>
