<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Data Ingestion</h1>
        <p class="text-body-1 mb-6">
          Import Shape Shifter output to a database using registered ingesters.
        </p>
      </v-col>
    </v-row>

    <v-row>
      <!-- Ingester List (Left Column) -->
      <v-col cols="12" md="4">
        <IngesterList />
      </v-col>

      <!-- Ingester Form (Right Column) -->
      <v-col cols="12" md="8">
        <v-alert v-if="!selectedIngester" type="info" variant="tonal">
          Select an ingester from the list to begin
        </v-alert>
        <IngesterForm v-else />
      </v-col>
    </v-row>

    <!-- Loading Overlay -->
    <v-overlay :model-value="loading" class="align-center justify-center">
      <v-progress-circular indeterminate size="64" />
    </v-overlay>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useIngesterStore } from '@/stores/ingester'
import IngesterList from '@/components/ingester/IngesterList.vue'
import IngesterForm from '@/components/ingester/IngesterForm.vue'

const ingesterStore = useIngesterStore()
const { selectedIngester, loading } = storeToRefs(ingesterStore)
const { fetchIngesters } = ingesterStore

onMounted(async () => {
  await fetchIngesters()
})
</script>
