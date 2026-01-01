<template>
  <v-alert type="warning" variant="tonal" prominent border="start" closable>
    <v-alert-title class="d-flex align-center">
      <v-icon icon="mdi-alert-circle" class="mr-2" />
      Circular Dependencies Detected
    </v-alert-title>

    <p class="mb-4">
      {{ cycles.length }} circular {{ cycles.length === 1 ? 'dependency' : 'dependencies' }}
      found. This may cause processing issues.
    </p>

    <v-expansion-panels variant="accordion">
      <v-expansion-panel
        v-for="(cycle, index) in cycles"
        :key="index"
        :title="`Cycle ${index + 1}: ${cycle.length} entities`"
      >
        <v-expansion-panel-text>
          <div class="d-flex align-center flex-wrap">
            <template v-for="(entity, entityIndex) in cycle" :key="entity">
              <v-chip color="warning" variant="outlined" size="small" prepend-icon="mdi-cube">
                {{ entity }}
              </v-chip>
              <v-icon v-if="entityIndex < cycle.length - 1" icon="mdi-arrow-right" size="small" class="mx-2" />
              <v-icon v-else icon="mdi-refresh" size="small" class="mx-2" color="warning" />
            </template>
          </div>

          <v-divider class="my-3" />

          <p class="text-caption text-grey">
            These entities depend on each other in a circular manner, which prevents topological ordering.
          </p>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-alert>
</template>

<script setup lang="ts">
interface Props {
  cycles: string[][]
}

defineProps<Props>()
</script>
