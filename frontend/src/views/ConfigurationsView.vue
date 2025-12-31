<template>
  <v-container fluid class="pa-6">
    <v-row>
      <v-col>
        <h1 class="text-h4 mb-6">Configurations</h1>
      </v-col>
    </v-row>

    <!-- Toolbar -->
    <v-row>
      <v-col cols="12" md="6">
        <v-text-field
          v-model="searchQuery"
          prepend-inner-icon="mdi-magnify"
          label="Search configurations"
          variant="outlined"
          density="compact"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="sortBy"
          :items="sortOptions"
          label="Sort by"
          variant="outlined"
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="3" class="text-right">
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="showCreateDialog = true"
        >
          New Project
        </v-btn>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="loading" class="mt-4">
      <v-col cols="12" class="text-center py-12">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-grey">Loading configurations...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" variant="tonal" class="mt-4">
      <v-alert-title>Error Loading Configurations</v-alert-title>
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="handleRefresh">Retry</v-btn>
      </template>
    </v-alert>

    <!-- Empty State -->
    <v-row v-else-if="isEmpty" class="mt-4">
      <v-col cols="12">
        <v-card variant="outlined" class="text-center py-12">
          <v-icon icon="mdi-file-document-outline" size="64" color="grey" />
          <h3 class="text-h6 mt-4 mb-2">No Configurations Yet</h3>
          <p class="text-grey mb-4">
            Create your first configuration to get started
          </p>
          <v-btn
            color="primary"
            prepend-icon="mdi-plus"
            @click="showCreateDialog = true"
          >
            Create Project
          </v-btn>
        </v-card>
      </v-col>
    </v-row>

    <!-- Project List -->
    <v-row v-else class="mt-4">
      <v-col
        v-for="config in filteredConfigurations"
        :key="config.name"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card
          variant="outlined"
          hover
          :ripple="false"
          @click="handleSelectConfig(config.name)"
        >
          <v-card-title class="d-flex align-center">
            <v-icon icon="mdi-file-document" class="mr-2" />
            <span class="text-truncate">{{ config.name }}</span>
          </v-card-title>

          <v-card-text>
            <div class="d-flex align-center mb-2">
              <v-icon icon="mdi-cube-outline" size="small" class="mr-2" />
              <span class="text-body-2">
                {{ config.entity_count }}
                {{ config.entity_count === 1 ? 'entity' : 'entities' }}
              </span>
            </div>

            <div v-if="config.modified_at" class="d-flex align-center">
              <v-icon icon="mdi-clock-outline" size="small" class="mr-2" />
              <span class="text-body-2 text-grey">
                Modified {{ formatDate(config.modified_at) }}
              </span>
            </div>
          </v-card-text>

          <v-card-actions>
            <v-btn
              variant="text"
              size="small"
              prepend-icon="mdi-pencil"
              @click.stop="handleSelectConfig(config.name)"
            >
              Edit
            </v-btn>
            <v-btn
              variant="text"
              size="small"
              prepend-icon="mdi-check-circle-outline"
              @click.stop="handleValidate(config.name)"
            >
              Validate
            </v-btn>
            <v-spacer />
            <v-btn
              variant="text"
              size="small"
              color="error"
              icon="mdi-delete"
              @click.stop="handleDeleteClick(config)"
            />
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Create Dialog -->
    <create-configuration-dialog
      v-model="showCreateDialog"
      @created="handleConfigCreated"
    />

    <!-- Delete Confirmation Dialog -->
    <delete-confirmation-dialog
      v-model="showDeleteDialog"
      :item-name="configToDelete?.name"
      item-type="configuration"
      @confirm="handleDeleteConfirm"
    />

    <!-- Success Snackbar with Animation -->
    <v-scale-transition>
      <v-snackbar v-if="showSuccessSnackbar" v-model="showSuccessSnackbar" color="success" timeout="3000">
        {{ successMessage }}
        <template #actions>
          <v-btn variant="text" @click="showSuccessSnackbar = false">
            Close
          </v-btn>
        </template>
      </v-snackbar>
    </v-scale-transition>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useConfigurations } from '@/composables'
import type { ProjectMetadata } from '@/types'
import CreateConfigurationDialog from '@/components/configurations/CreateConfigurationDialog.vue'
import DeleteConfirmationDialog from '@/components/common/DeleteConfirmationDialog.vue'

const router = useRouter()

// Composables
const {
  configurations,
  loading,
  error,
  isEmpty,
  select,
  remove,
  validate,
  fetch,
  clearError,
} = useConfigurations({ autoFetch: true })

// Local state
const searchQuery = ref('')
const sortBy = ref('name')
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const configToDelete = ref<ProjectMetadata | null>(null)
const showSuccessSnackbar = ref(false)
const successMessage = ref('')

// Sort options
const sortOptions = [
  { title: 'Name (A-Z)', value: 'name' },
  { title: 'Name (Z-A)', value: 'name-desc' },
  { title: 'Entity Count (Low-High)', value: 'entity-count' },
  { title: 'Entity Count (High-Low)', value: 'entity-count-desc' },
  { title: 'Recently Modified', value: 'modified' },
]

// Computed
const filteredConfigurations = computed(() => {
  let filtered = configurations.value

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter((config) => config.name.toLowerCase().includes(query))
  }

  // Sort
  const sorted = [...filtered]
  switch (sortBy.value) {
    case 'name':
      sorted.sort((a, b) => a.name.localeCompare(b.name))
      break
    case 'name-desc':
      sorted.sort((a, b) => b.name.localeCompare(a.name))
      break
    case 'entity-count':
      sorted.sort((a, b) => a.entity_count - b.entity_count)
      break
    case 'entity-count-desc':
      sorted.sort((a, b) => b.entity_count - a.entity_count)
      break
    case 'modified':
      sorted.sort((a, b) => {
        const aTime = a.modified_at ? new Date(a.modified_at).getTime() : 0
        const bTime = b.modified_at ? new Date(b.modified_at).getTime() : 0
        return bTime - aTime
      })
      break
  }

  return sorted
})

// Methods
function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString()
}

async function handleSelectConfig(name: string) {
  try {
    await select(name)
    router.push({ name: 'config-detail', params: { name } })
  } catch (err) {
    console.error('Failed to select configuration:', err)
  }
}

async function handleValidate(name: string) {
  try {
    await validate(name)
    successMessage.value = `Project "${name}" validated successfully`
    showSuccessSnackbar.value = true
  } catch (err) {
    console.error('Failed to validate configuration:', err)
  }
}

function handleDeleteClick(config: ProjectMetadata) {
  configToDelete.value = config
  showDeleteDialog.value = true
}

async function handleDeleteConfirm() {
  if (!configToDelete.value) return

  try {
    await remove(configToDelete.value.name)
    successMessage.value = `Project "${configToDelete.value.name}" deleted`
    showSuccessSnackbar.value = true
    configToDelete.value = null
  } catch (err) {
    console.error('Failed to delete configuration:', err)
  }
}

function handleConfigCreated(name: string) {
  successMessage.value = `Project "${name}" created`
  showSuccessSnackbar.value = true
  router.push({ name: 'config-detail', params: { name } })
}

async function handleRefresh() {
  clearError()
  await fetch()
}
</script>

<style scoped>
.v-card {
  cursor: pointer;
  transition: all 0.2s;
}

.v-card:hover {
  border-color: rgb(var(--v-theme-primary));
}
</style>
