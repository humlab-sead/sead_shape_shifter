<template>
  <v-dialog v-model="dialog" max-width="600">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-database-arrow-up</v-icon>
        Unmaterialize Entity
      </v-card-title>

      <v-card-text>
        <v-alert type="warning" variant="tonal" class="mb-4">
          This will restore the entity to its original dynamic state (SQL/entity/file-based).
          Any materialized data will be discarded.
        </v-alert>

        <div v-if="requiresCascade" class="mb-4">
          <v-alert type="error" variant="tonal">
            <div class="text-subtitle-2 mb-2">Dependent Entities Found</div>
            <p class="mb-2">
              The following materialized entities depend on this entity and must be unmaterialized
              first:
            </p>
            <ul class="ml-4">
              <li v-for="dep in affectedEntities" :key="dep">
                <strong>{{ dep }}</strong>
              </li>
            </ul>
          </v-alert>

          <v-checkbox
            v-model="cascade"
            label="Unmaterialize all dependent entities (cascade)"
            color="warning"
            density="compact"
          />

          <v-alert v-if="cascade" type="info" variant="text" density="compact" class="mt-2">
            All {{ affectedEntities.length }} dependent
            {{ affectedEntities.length === 1 ? 'entity' : 'entities' }} will be unmaterialized.
          </v-alert>
        </div>

        <div v-else>
          <p class="text-body-2">Are you sure you want to unmaterialize this entity?</p>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="close">Cancel</v-btn>
        <v-btn
          :color="requiresCascade && cascade ? 'warning' : 'primary'"
          :disabled="loading || (requiresCascade && !cascade)"
          :loading="loading"
          @click="unmaterialize"
        >
          {{ requiresCascade && cascade ? 'Cascade Unmaterialize' : 'Unmaterialize' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useToast } from 'vuetify-use-dialog'
import { materializationApi } from '@/api/materialization'

const toast = useToast()

interface Props {
  modelValue: boolean
  projectName: string
  entityName: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'unmaterialized': [entities: string[]]
}>()

const dialog = ref(props.modelValue)
const loading = ref(false)
const cascade = ref(false)
const requiresCascade = ref(false)
const affectedEntities = ref<string[]>([])

watch(
  () => props.modelValue,
  (val) => {
    dialog.value = val
    if (val) {
      // Reset state
      cascade.value = false
      requiresCascade.value = false
      affectedEntities.value = []
    }
  }
)

watch(dialog, (val) => {
  emit('update:modelValue', val)
})

async function unmaterialize() {
  loading.value = true
  try {
    const result = await materializationApi.unmaterialize(
      props.projectName,
      props.entityName,
      cascade.value
    )
    
    const count = result.unmaterialized_entities?.length || 1
    const entityList = result.unmaterialized_entities?.join(', ') || props.entityName
    
    if (count > 1) {
      toast.success(`Successfully unmaterialized ${count} entities: ${entityList}`)
    } else {
      toast.success(`Successfully unmaterialized entity: ${entityList}`)
    }
    
    emit('unmaterialized', result.unmaterialized_entities || [props.entityName])
    close()
  } catch (error: any) {
    console.error('Unmaterialization failed:', error)

    // Check if cascade is required
    if (error.response?.status === 409) {
      const detail = error.response.data.detail
      if (typeof detail === 'object' && detail.requires_cascade) {
        requiresCascade.value = true
        affectedEntities.value = detail.affected_entities || []
        toast.warning('Cascade required - dependent entities must be unmaterialized first')
        return
      }
    }

    const errorMessage = error.response?.data?.detail?.message || error.response?.data?.detail || error.message
    toast.error(`Unmaterialization failed: ${errorMessage}`)
  } finally {
    loading.value = false
  }
}

function close() {
  dialog.value = false
}
</script>
