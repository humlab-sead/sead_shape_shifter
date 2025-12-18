<template>
  <v-container fluid class="pa-6">
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Entity Management</h1>
        
        <!-- No Configuration Loaded -->
        <v-card v-if="!configurationStore.currentConfigName" variant="outlined" class="mb-4">
          <v-card-text class="text-center py-8">
            <v-icon icon="mdi-file-question" size="64" color="grey" class="mb-4" />
            <h2 class="text-h6 mb-2">No Configuration Loaded</h2>
            <p class="text-grey mb-4">
              To manage entities, you need to load a configuration file first.
            </p>
            <v-btn
              color="primary"
              prepend-icon="mdi-folder-open"
              to="/configurations"
            >
              Browse Configurations
            </v-btn>
          </v-card-text>
        </v-card>

        <!-- Configuration Loaded -->
        <div v-else>
          <v-card variant="outlined" class="mb-4">
            <v-card-title>
              <v-icon icon="mdi-file-document" class="mr-2" />
              {{ configurationStore.currentConfigName }}
            </v-card-title>
            <v-card-subtitle>
              {{ entityCount }} {{ entityCount === 1 ? 'entity' : 'entities' }}
            </v-card-subtitle>
          </v-card>

          <entity-list-card
            v-if="configurationStore.currentConfigName"
            @entity-updated="handleEntityUpdated"
          />
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useConfigurationStore } from '@/stores/configuration'
import { useEntities } from '@/composables/useEntities'
import EntityListCard from '@/components/entities/EntityListCard.vue'

const configurationStore = useConfigurationStore()
const configName = computed(() => configurationStore.currentConfigName || '')

const { entityCount, refetchEntities } = useEntities({
  configName: configName.value,
})

function handleEntityUpdated() {
  refetchEntities()
}
</script>
