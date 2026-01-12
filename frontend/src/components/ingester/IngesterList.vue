<template>
  <v-card>
    <v-card-title>Available Ingesters</v-card-title>
    <v-card-text>
      <v-list>
        <v-list-item
          v-for="ingester in ingesters"
          :key="ingester.key"
          :active="selectedIngester?.key === ingester.key"
          @click="selectIngester(ingester.key)"
        >
          <template v-slot:prepend>
            <v-icon>mdi-database-import</v-icon>
          </template>

          <v-list-item-title>{{ ingester.name }}</v-list-item-title>
          <v-list-item-subtitle>{{ ingester.description }}</v-list-item-subtitle>

          <template v-slot:append>
            <v-chip size="small" variant="outlined">
              v{{ ingester.version }}
            </v-chip>
          </template>
        </v-list-item>
      </v-list>

      <v-alert v-if="!hasIngesters && !loading" type="info" variant="tonal">
        No ingesters available
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useIngesterStore } from '@/stores/ingester'

const ingesterStore = useIngesterStore()
const { ingesters, selectedIngester, hasIngesters, loading } = storeToRefs(ingesterStore)
const { selectIngester } = ingesterStore
</script>
