<template>
  <v-container fluid class="pa-6">
    <v-row>
      <v-col>
        <h1 class="text-h4 mb-6">Projects</h1>
      </v-col>
    </v-row>

    <!-- Toolbar -->
    <v-row>
      <v-col cols="12" md="6">
        <v-text-field
          v-model="searchQuery"
          prepend-inner-icon="mdi-magnify"
          label="Search projects"
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
        <v-btn color="primary" prepend-icon="mdi-plus" @click="showCreateDialog = true"> New Project </v-btn>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="loading" class="mt-4">
      <v-col cols="12" class="text-center py-12">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-grey">Loading projects...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" variant="tonal" class="mt-4">
      <v-alert-title>Error Loading Projects</v-alert-title>
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
          <h3 class="text-h6 mt-4 mb-2">No Projects Yet</h3>
          <p class="text-grey mb-4">Create your first project to get started</p>
          <v-btn color="primary" prepend-icon="mdi-plus" @click="showCreateDialog = true"> Create Project </v-btn>
        </v-card>
      </v-col>
    </v-row>

    <!-- No Matching Results -->
    <v-row v-else-if="filteredProjects.length === 0" class="mt-4">
      <v-col cols="12">
        <v-card variant="flat">
          <v-card-text class="text-center py-8">
            <v-icon icon="mdi-file-search-outline" size="64" color="grey" />
            <p class="text-h6 mt-4 mb-2">No matching projects</p>
            <p class="text-grey">Try adjusting your search or sort selection.</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Project List -->
    <v-row v-else class="mt-4">
      <v-col cols="12">
        <v-card variant="flat">
          <v-list density="compact">
            <v-list-item
              v-for="project in filteredProjects"
              :key="project.name"
              :value="project.name"
              class="project-list-item"
              @click="handleSelectProject(project.name)"
            >
              <template #prepend>
                <v-icon icon="mdi-file-document" size="small" />
              </template>

              <v-list-item-title class="project-title-row">
                <span class="project-name">{{ project.name }}</span>
                <v-chip size="x-small" variant="outlined" class="mx-2">
                  {{ project.entity_count }}
                  {{ project.entity_count === 1 ? 'entity' : 'entities' }}
                </v-chip>
                <span v-if="project.modified_at" class="text-caption text-medium-emphasis">
                  Modified {{ formatDate(project.modified_at) }}
                </span>
              </v-list-item-title>

              <template #append>
                <v-btn
                  icon="mdi-pencil"
                  variant="text"
                  size="x-small"
                  @click.stop="handleSelectProject(project.name)"
                />
                <v-btn
                  icon="mdi-content-copy"
                  variant="text"
                  size="x-small"
                  @click.stop="handleCopyClick(project)"
                />
                <v-btn
                  icon="mdi-check-circle-outline"
                  variant="text"
                  size="x-small"
                  @click.stop="handleValidate(project.name)"
                />
                <v-btn
                  icon="mdi-delete"
                  variant="text"
                  size="x-small"
                  color="error"
                  @click.stop="handleDeleteClick(project)"
                />
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <!-- Create Dialog -->
    <create-project-dialog v-model="showCreateDialog" @created="handleProjectCreated" />

    <!-- Copy Dialog -->
    <copy-project-dialog
      v-model="showCopyDialog"
      :source-name="projectToCopy?.name ?? null"
      @copied="handleProjectCopied"
    />

    <!-- Delete Confirmation Dialog -->
    <delete-confirmation-dialog
      v-model="showDeleteDialog"
      :item-name="projectToDelete?.name"
      item-type="project"
      @confirm="handleDeleteConfirm"
    />

    <!-- Success Snackbar with Animation -->
    <v-scale-transition>
      <v-snackbar v-if="showSuccessSnackbar" v-model="showSuccessSnackbar" color="success" timeout="3000">
        {{ successMessage }}
        <template #actions>
          <v-btn variant="text" @click="showSuccessSnackbar = false"> Close </v-btn>
        </template>
      </v-snackbar>
    </v-scale-transition>

    <!-- Error Snackbar for operation failures -->
    <v-scale-transition>
      <v-snackbar v-if="showErrorSnackbar" v-model="showErrorSnackbar" color="error" timeout="6000">
        {{ errorMessage }}
        <template #actions>
          <v-btn variant="text" @click="showErrorSnackbar = false"> Close </v-btn>
        </template>
      </v-snackbar>
    </v-scale-transition>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useProjects } from '@/composables'
import type { ProjectMetadata } from '@/types'
import CreateProjectDialog from '@/components/projects/CreateProjectDialog.vue'
import CopyProjectDialog from '@/components/projects/CopyProjectDialog.vue'
import DeleteConfirmationDialog from '@/components/common/DeleteConfirmationDialog.vue'

const router = useRouter()

// Composables
const { projects, loading, error, isEmpty, remove, validate, fetch, clearError } = useProjects({
  autoFetch: true,
})

// Local state
const searchQuery = ref('')
const sortBy = ref('name')
const showCreateDialog = ref(false)
const showCopyDialog = ref(false)
const showDeleteDialog = ref(false)
const projectToCopy = ref<ProjectMetadata | null>(null)
const projectToDelete = ref<ProjectMetadata | null>(null)
const showSuccessSnackbar = ref(false)
const successMessage = ref('')
const showErrorSnackbar = ref(false)
const errorMessage = ref('')

// Sort options
const sortOptions = [
  { title: 'Name (A-Z)', value: 'name' },
  { title: 'Name (Z-A)', value: 'name-desc' },
  { title: 'Entity Count (Low-High)', value: 'entity-count' },
  { title: 'Entity Count (High-Low)', value: 'entity-count-desc' },
  { title: 'Recently Modified', value: 'modified' },
]

// Computed
const filteredProjects = computed(() => {
  let filtered = projects.value

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter((project) => project.name.toLowerCase().includes(query))
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

function handleSelectProject(name: string) {
  // Navigate directly - let ProjectDetailView handle loading
  router.push({ name: 'project-detail', params: { name } })
}

async function handleValidate(name: string) {
  try {
    await validate(name)
    successMessage.value = `Project "${name}" validated successfully`
    showSuccessSnackbar.value = true
  } catch (err) {
    console.error('Failed to validate project:', err)
  }
}

function handleCopyClick(project: ProjectMetadata) {
  projectToCopy.value = project
  showCopyDialog.value = true
}

async function handleProjectCopied(targetName: string) {
  successMessage.value = `Project "${projectToCopy.value?.name}" copied to "${targetName}"`
  showSuccessSnackbar.value = true
  projectToCopy.value = null
  // Refresh project list to show new copy
  await fetch()
}

function handleDeleteClick(project: ProjectMetadata) {
  projectToDelete.value = project
  showDeleteDialog.value = true
}

async function handleDeleteConfirm() {
  if (!projectToDelete.value) return

  const projectName = projectToDelete.value.name
  try {
    await remove(projectName)
    successMessage.value = `Project "${projectName}" deleted`
    showSuccessSnackbar.value = true
    projectToDelete.value = null
  } catch (err) {
    console.error('Failed to delete project:', err)
    // Show error in snackbar without affecting project list
    errorMessage.value = err instanceof Error ? err.message : `Failed to delete project "${projectName}"`
    showErrorSnackbar.value = true
    // Keep dialog open so user can try again or cancel
  }
}

function handleProjectCreated(name: string) {
  successMessage.value = `Project "${name}" created`
  showSuccessSnackbar.value = true
  router.push({ name: 'project-detail', params: { name } })
}

async function handleRefresh() {
  clearError()
  await fetch()
}
</script>

<style scoped>
.project-list-item {
  font-size: 0.9rem;
}

.project-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.project-name {
  font-weight: 500;
  font-size: 0.9rem;
}
</style>
