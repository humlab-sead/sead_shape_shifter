<template>
  <div class="test-run-view">
    <v-container fluid>
      <!-- Header -->
      <v-row class="mb-4">
        <v-col>
          <div class="d-flex justify-space-between align-center">
            <h1 class="text-h4">Configuration Test Run</h1>
            <div class="d-flex ga-2">
              <v-btn
                variant="outlined"
                prepend-icon="mdi-refresh"
                @click="handleReset"
                :disabled="isRunning"
              >
                Reset
              </v-btn>
              <v-btn
                color="primary"
                prepend-icon="mdi-play"
                @click="handleStartTest"
                :loading="isRunning"
                :disabled="isRunning || !configName"
              >
                Run Test
              </v-btn>
            </div>
          </div>
        </v-col>
      </v-row>

      <!-- Config Info -->
      <v-row v-if="configName" class="mb-4">
        <v-col>
          <v-alert type="info" variant="tonal">
            <strong>Configuration:</strong> {{ configName }}
          </v-alert>
        </v-col>
      </v-row>

      <!-- Error Alert -->
      <v-row v-if="error" class="mb-4">
        <v-col>
          <v-alert
            type="error"
            variant="tonal"
            closable
            @click:close="error = null"
          >
            <strong>Error:</strong> {{ error }}
          </v-alert>
        </v-col>
      </v-row>

      <v-divider class="my-4" />

      <!-- Test Configuration (before run) -->
      <v-row v-if="!testResult">
        <v-col>
          <v-card>
            <v-card-text>
              <TestRunConfig
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
      <v-row v-if="isLoadingConfig">
        <v-col class="text-center">
          <v-progress-circular indeterminate size="64" />
          <p class="mt-4">Loading configuration...</p>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import TestRunConfig from '@/components/TestRun/TestRunConfig.vue'
import TestRunProgress from '@/components/TestRun/TestRunProgress.vue'
import TestRunResults from '@/components/TestRun/TestRunResults.vue'
import testRunApi from '@/api/testRunApi'
import { configurationsApi } from '@/api/configurations'
import type { TestRunOptions, TestRunResult } from '@/types/testRun'
import { DEFAULT_TEST_RUN_OPTIONS } from '@/types/testRun'

const route = useRoute()

const configName = ref<string>(route.params.name as string)
const options = ref<Partial<TestRunOptions>>({ ...DEFAULT_TEST_RUN_OPTIONS })
const selectedEntities = ref<string[]>([])
const availableEntities = ref<string[]>([])
const testResult = ref<TestRunResult | null>(null)
const isRunning = ref(false)
const isLoadingConfig = ref(true)
const error = ref<string | null>(null)

// Load configuration and available entities
onMounted(async () => {
  if (!configName.value) {
    error.value = 'No configuration name provided'
    isLoadingConfig.value = false
    return
  }

  try {
    isLoadingConfig.value = true
    const config = await configurationsApi.get(configName.value)
    availableEntities.value = Object.keys(config.entities || {})
    error.value = null
  } catch (err) {
    console.error('Failed to load configuration:', err)
    error.value = `Failed to load configuration: ${err instanceof Error ? err.message : String(err)}`
  } finally {
    isLoadingConfig.value = false
  }
})

const handleStartTest = async () => {
  if (!configName.value) {
    error.value = 'No configuration selected'
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
      config_name: configName.value,
      options: testOptions,
    })

    testResult.value = result

    // Check for errors
    if (result.status === 'failed') {
      error.value = result.error_message || 'Test run failed'
    }
  } catch (err) {
    console.error('Test run failed:', err)
    const errorMessage = err instanceof Error ? err.message : String(err)
    error.value = errorMessage
  } finally {
    isRunning.value = false
  }
}

const handleReset = () => {
  testResult.value = null
  error.value = null
  options.value = { ...DEFAULT_TEST_RUN_OPTIONS }
  selectedEntities.value = []
}
</script>

<style scoped>
.test-run-view {
  padding: 20px;
}
</style>
