<template>
  <v-card variant="outlined">
    <v-card-title class="d-flex align-center justify-space-between">
      <span>Entities</span>
      <div class="d-flex gap-2">
        <v-btn color="success" size="small" prepend-icon="mdi-play-circle" @click="showExecuteDialog = true">
          Execute
        </v-btn>
        <v-btn color="primary" size="small" prepend-icon="mdi-plus" @click="showCreateDialog = true">
          Add Entity
        </v-btn>
      </div>
    </v-card-title>

    <v-card-text>
      <!-- Search and Filter -->
      <v-row class="mb-4">
        <v-col cols="12" md="6">
          <v-text-field
            v-model="searchQuery"
            prepend-inner-icon="mdi-magnify"
            label="Search entities"
            variant="outlined"
            density="compact"
            clearable
            hide-details
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="filterType"
            :items="entityTypes"
            label="Filter by type"
            variant="outlined"
            density="compact"
            clearable
            hide-details
          />
        </v-col>
      </v-row>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" />
        <p class="mt-2 text-grey">Loading entities...</p>
      </div>

      <!-- Error State -->
      <v-alert v-else-if="error" type="error" variant="tonal">
        {{ error }}
      </v-alert>

      <!-- Empty State -->
      <div v-else-if="filteredEntities.length === 0" class="text-center py-8">
        <v-icon icon="mdi-cube-off-outline" size="64" color="grey" />
        <p class="text-h6 mt-4 mb-2">
          {{ searchQuery || filterType ? 'No matching entities' : 'No entities yet' }}
        </p>
        <p class="text-grey mb-4">
          {{
            searchQuery || filterType
              ? 'Try adjusting your search or filter'
              : 'Add entities to define your data structure'
          }}
        </p>
        <v-btn
          v-if="!searchQuery && !filterType"
          color="primary"
          prepend-icon="mdi-plus"
          @click="showCreateDialog = true"
        >
          Add First Entity
        </v-btn>
      </div>

      <!-- Entity List -->
      <v-list v-else density="compact">
        <v-list-item
          v-for="entity in filteredEntities"
          :key="entity.name"
          :value="entity.name"
          class="entity-list-item"
          @click="handleSelectEntity(entity)"
        >
          <template #prepend>
            <v-icon :icon="getEntityIcon(entity.entity_data.type)" size="small" />
          </template>

          <v-list-item-title class="entity-title-row">
            <span class="entity-name">{{ entity.name }}</span>
            <v-chip size="x-small" variant="outlined" class="mx-2">
              {{ entity.entity_data.type || 'data' }}
            </v-chip>
            <span v-if="entity.entity_data.source" class="text-caption text-medium-emphasis">
              Source: {{ entity.entity_data.source }}
            </span>
          </v-list-item-title>

          <template #append>
            <v-btn icon="mdi-pencil" variant="text" size="x-small" @click.stop="handleEditEntity(entity)" />
            <v-btn
              icon="mdi-delete"
              variant="text"
              size="x-small"
              color="error"
              @click.stop="handleDeleteClick(entity)"
            />
          </template>
        </v-list-item>
      </v-list>
    </v-card-text>

    <!-- Entity Form Dialog -->
    <entity-form-dialog
      v-model="showFormDialog"
      :project-name="projectName"
      :entity="selectedEntity"
      :mode="dialogMode"
      @saved="handleEntitySaved"
    />

    <!-- Execute Dialog -->
    <execute-dialog
      v-model="showExecuteDialog"
      :project-name="projectName"
      @executed="handleExecuted"
    />

    <!-- Delete Confirmation -->
    <delete-confirmation-dialog
      v-model="showDeleteDialog"
      :item-name="entityToDelete?.name"
      item-type="entity"
      @confirm="handleDeleteConfirm"
    />

    <!-- Success Snackbar -->
    <v-snackbar v-model="showSuccessSnackbar" color="success" timeout="3000">
      {{ successMessage }}
    </v-snackbar>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useEntities } from '@/composables'
import type { EntityResponse } from '@/api/entities'
import EntityFormDialog from './EntityFormDialog.vue'
import ExecuteDialog from '@/components/execute/ExecuteDialog.vue'
import DeleteConfirmationDialog from '@/components/common/DeleteConfirmationDialog.vue'

interface Props {
  projectName: string
}

interface Emits {
  (e: 'entity-updated'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { entities, loading, error, remove } = useEntities({
  projectName: props.projectName,
  autoFetch: true,
})

// Local state
const searchQuery = ref('')
const filterType = ref<string | null>(null)
const showFormDialog = ref(false)
const showCreateDialog = ref(false)
const showExecuteDialog = ref(false)
const showDeleteDialog = ref(false)
const selectedEntity = ref<EntityResponse | null>(null)
const entityToDelete = ref<EntityResponse | null>(null)
const dialogMode = ref<'create' | 'edit'>('create')
const showSuccessSnackbar = ref(false)
const successMessage = ref('')

// Computed
const entityTypes = computed(() => {
  const types = new Set<string>()
  entities.value.forEach((e) => {
    types.add((e.entity_data.type as string) || 'unknown')
  })
  return Array.from(types).map((type) => ({ title: type, value: type }))
})

const filteredEntities = computed(() => {
  let filtered = entities.value

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter((e) => e.name.toLowerCase().includes(query))
  }

  // Filter by type
  if (filterType.value) {
    filtered = filtered.filter((e) => e.entity_data.type === filterType.value)
  }

  return filtered
})

// Methods
function getEntityIcon(type: unknown): string {
  switch (type) {
    case 'data':
      return 'mdi-database'
    case 'sql':
      return 'mdi-code-braces'
    case 'fixed':
      return 'mdi-table-lock'
    default:
      return 'mdi-cube'
  }
}

function handleSelectEntity(entity: EntityResponse) {
  selectedEntity.value = entity
  dialogMode.value = 'edit'
  showFormDialog.value = true
}

function handleEditEntity(entity: EntityResponse) {
  selectedEntity.value = entity
  dialogMode.value = 'edit'
  showFormDialog.value = true
}

function handleDeleteClick(entity: EntityResponse) {
  entityToDelete.value = entity
  showDeleteDialog.value = true
}

async function handleDeleteConfirm() {
  if (!entityToDelete.value) return

  try {
    await remove(entityToDelete.value.name)
    successMessage.value = `Entity "${entityToDelete.value.name}" deleted`
    showSuccessSnackbar.value = true
    emit('entity-updated')
    entityToDelete.value = null
  } catch (err) {
    console.error('Failed to delete entity:', err)
  }
}

function handleEntitySaved() {
  successMessage.value = dialogMode.value === 'create' ? 'Entity created' : 'Entity updated'
  showSuccessSnackbar.value = true
  emit('entity-updated')
}

function handleExecuted(result: any) {
  successMessage.value = `Workflow executed successfully: ${result.message}`
  showSuccessSnackbar.value = true
}

// Watch for create dialog trigger
import { watch } from 'vue'
watch(showCreateDialog, (newValue) => {
  if (newValue) {
    selectedEntity.value = null
    dialogMode.value = 'create'
    showFormDialog.value = true
    showCreateDialog.value = false
  }
})
</script>

<style scoped>
.entity-list-item {
  font-size: 0.9rem;
}

.entity-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.entity-name {
  font-weight: 500;
  font-size: 0.9rem;
}

/* Compact mode adjustments */
.compact-mode .entity-list-item {
  font-size: 0.8125rem;
  min-height: 36px !important;
}

.compact-mode .entity-name {
  font-size: 0.8125rem;
}

.compact-mode .entity-title-row {
  gap: 2px;
}
</style>
