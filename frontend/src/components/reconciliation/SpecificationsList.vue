<template>
  <div class="specifications-list">
    <v-card variant="outlined">
      <v-card-title class="d-flex align-center justify-space-between">
        <span>Reconciliation Specifications</span>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openAddDialog">
          Add Specification
        </v-btn>
      </v-card-title>

      <v-card-text>
        <!-- Loading State -->
        <div v-if="loadingSpecs" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" />
          <p class="text-grey mt-4">Loading specifications...</p>
        </div>

        <!-- Error State -->
        <v-alert v-else-if="specsError" type="error" variant="tonal" class="mb-4">
          {{ specsError }}
        </v-alert>

        <!-- Empty State -->
        <v-alert v-else-if="specifications.length === 0" type="info" variant="tonal" class="mb-4">
          <div class="d-flex align-center">
            <v-icon start>mdi-information</v-icon>
            <div>
              <div class="font-weight-bold">No specifications configured</div>
              <div class="text-caption">Add your first reconciliation specification to get started</div>
            </div>
          </div>
        </v-alert>

        <!-- Data Table -->
        <v-data-table
          v-else
          :headers="headers"
          :items="specifications"
          :items-per-page="10"
          class="elevation-0"
          hover
        >
          <!-- Entity Name Column -->
          <template #item.entity_name="{ item }">
            <div class="d-flex align-center">
              <v-icon start size="small">mdi-table</v-icon>
              <span class="font-weight-medium">{{ item.entity_name }}</span>
            </div>
          </template>

          <!-- Target Field Column -->
          <template #item.target_field="{ item }">
            <v-chip size="small" variant="tonal" color="primary">
              <v-icon start size="x-small">mdi-target</v-icon>
              {{ item.target_field }}
            </v-chip>
          </template>

          <!-- Remote Type Column -->
          <template #item.remote="{ item }">
            <v-chip
              v-if="item.remote.service_type"
              size="small"
              :color="isRemoteTypeValid(item) ? 'success' : 'warning'"
              variant="tonal"
            >
              {{ item.remote.service_type }}
            </v-chip>
            <v-chip v-else size="small" color="grey" variant="tonal">
              <v-icon start size="x-small">mdi-minus-circle</v-icon>
              Disabled
            </v-chip>
          </template>

          <!-- Mappings Column -->
          <template #item.mapping_count="{ item }">
            <v-chip
              size="small"
              :color="item.mapping_count > 0 ? 'info' : 'default'"
              variant="tonal"
            >
              <v-icon start size="x-small">mdi-link-variant</v-icon>
              {{ item.mapping_count }}
            </v-chip>
          </template>

          <!-- Thresholds Column -->
          <template #item.thresholds="{ item }">
            <div class="text-caption">
              <div>Auto: {{ (item.auto_accept_threshold * 100).toFixed(0) }}%</div>
              <div>Review: {{ (item.review_threshold * 100).toFixed(0) }}%</div>
            </div>
          </template>

          <!-- Actions Column -->
          <template #item.actions="{ item }">
            <div class="d-flex gap-1">
              <v-tooltip text="Edit specification" location="top">
                <template #activator="{ props }">
                  <v-btn
                    icon="mdi-pencil"
                    size="small"
                    variant="text"
                    v-bind="props"
                    @click.stop="editSpecification(item)"
                  />
                </template>
              </v-tooltip>

              <v-tooltip text="Delete specification" location="top">
                <template #activator="{ props }">
                  <v-btn
                    icon="mdi-delete"
                    size="small"
                    variant="text"
                    color="error"
                    v-bind="props"
                    @click.stop="confirmDelete(item)"
                  />
                </template>
              </v-tooltip>
            </div>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Specification Editor Dialog -->
    <SpecificationEditor
      v-model="editorDialog"
      :project-name="projectName"
      :specification="selectedSpec"
      :is-new="isNewSpec"
      @saved="handleSpecSaved"
    />

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="500">
      <v-card>
        <v-card-title class="text-h6">
          <v-icon start color="warning">mdi-alert</v-icon>
          Delete Specification?
        </v-card-title>

        <v-card-text>
          <p>
            Are you sure you want to delete the specification for
            <strong>{{ specToDelete?.entity_name }}.{{ specToDelete?.target_field }}</strong>?
          </p>

          <v-alert v-if="specToDelete && specToDelete.mapping_count > 0" type="warning" variant="tonal" class="mt-4">
            <div class="font-weight-bold">Warning: This specification has {{ specToDelete.mapping_count }} existing mappings</div>
            <div class="text-caption mt-1">All mappings will be permanently deleted.</div>
          </v-alert>

          <p v-else class="text-caption text-grey mt-4">This action cannot be undone.</p>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn
            color="error"
            variant="elevated"
            :loading="deletingSpec"
            @click="performDelete"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useReconciliationStore } from '@/stores/reconciliation'
import type { SpecificationListItem } from '@/types/reconciliation'
import SpecificationEditor from './SpecificationEditor.vue'

interface Props {
  projectName: string
}

const props = defineProps<Props>()

const reconciliationStore = useReconciliationStore()
const { specifications, loadingSpecs, specsError } = storeToRefs(reconciliationStore)

// State
const editorDialog = ref(false)
const deleteDialog = ref(false)
const selectedSpec = ref<SpecificationListItem | null>(null)
const specToDelete = ref<SpecificationListItem | null>(null)
const isNewSpec = ref(false)
const deletingSpec = ref(false)

// Table headers
const headers = [
  { title: 'Entity', key: 'entity_name', sortable: true },
  { title: 'Target Field', key: 'target_field', sortable: true },
  { title: 'Remote Type', key: 'remote', sortable: false },
  { title: 'Mappings', key: 'mapping_count', sortable: true },
  { title: 'Thresholds', key: 'thresholds', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' as const },
]

// Methods
function isRemoteTypeValid(item: SpecificationListItem): boolean {
  // TODO: Validate against available remote types from service
  return item.remote.service_type != null
}

function openAddDialog() {
  selectedSpec.value = null
  isNewSpec.value = true
  editorDialog.value = true
}

function editSpecification(item: SpecificationListItem) {
  selectedSpec.value = item
  isNewSpec.value = false
  editorDialog.value = true
}

function confirmDelete(item: SpecificationListItem) {
  specToDelete.value = item
  deleteDialog.value = true
}

async function performDelete() {
  if (!specToDelete.value) return

  deletingSpec.value = true
  try {
    await reconciliationStore.deleteSpecification(
      props.projectName,
      specToDelete.value.entity_name,
      specToDelete.value.target_field,
      true // force delete even with mappings
    )
    deleteDialog.value = false
    specToDelete.value = null
  } catch (error) {
    console.error('Failed to delete specification:', error)
  } finally {
    deletingSpec.value = false
  }
}

async function handleSpecSaved() {
  editorDialog.value = false
  selectedSpec.value = null
  // List is automatically reloaded by store actions
}

// Lifecycle
onMounted(async () => {
  if (props.projectName) {
    await reconciliationStore.loadSpecifications(props.projectName)
  }
})
</script>

<style scoped>
.specifications-list {
  width: 100%;
}

.gap-1 {
  gap: 4px;
}

.gap-2 {
  gap: 8px;
}
</style>
