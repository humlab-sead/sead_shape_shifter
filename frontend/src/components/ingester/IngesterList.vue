<template>
  <v-card>
    <v-card-title>Available Ingesters</v-card-title>
    <v-card-text>
      <v-list>
        <v-list-item
          v-for="ingester in availableIngesters"
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
            <v-chip size="small" variant="outlined"> v{{ ingester.version }} </v-chip>
          </template>
        </v-list-item>
      </v-list>

      <v-alert v-if="availableIngesters.length === 0 && !loading" type="info" variant="tonal">
        No ingesters available
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useIngesterStore } from '@/stores/ingester'

const props = withDefaults(defineProps<{ excludedIngesterKeys?: string[] }>(), {
  excludedIngesterKeys: () => [],
})

const ingesterStore = useIngesterStore()
const { ingesters, selectedIngester, loading } = storeToRefs(ingesterStore)
const { selectIngester } = ingesterStore
const availableIngesters = computed(() =>
  ingesters.value.filter((ingester) => !props.excludedIngesterKeys.includes(ingester.key))
)
</script>
