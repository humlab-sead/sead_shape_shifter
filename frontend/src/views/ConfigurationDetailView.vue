<template>
  <v-container fluid class="pa-6">
    <v-row>
      <v-col>
        <div class="d-flex align-center mb-6">
          <v-btn
            icon="mdi-arrow-left"
            variant="text"
            @click="$router.push({ name: 'configurations' })"
          />
          <h1 class="text-h4 ml-2">{{ configName }}</h1>
        </div>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="loading">
      <v-col cols="12" class="text-center py-12">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-grey">Loading configuration...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" variant="tonal">
      <v-alert-title>Error Loading Configuration</v-alert-title>
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="handleRefresh">Retry</v-btn>
      </template>
    </v-alert>

    <!-- Configuration Content -->
    <v-row v-else-if="selectedConfig">
      <v-col cols="12">
        <v-card variant="outlined">
          <v-card-text>
            <p class="text-h6 mb-4">Configuration Details</p>
            <p class="text-body-2">
              This view will display detailed configuration information and entity management.
              Coming in the next sprint!
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useConfigurations } from '@/composables'

const route = useRoute()
const configName = computed(() => route.params.name as string)

const { selectedConfig, loading, error, select, clearError } = useConfigurations({
  autoFetch: false,
})

onMounted(async () => {
  if (configName.value) {
    await select(configName.value)
  }
})

async function handleRefresh() {
  clearError()
  if (configName.value) {
    await select(configName.value)
  }
}
</script>
