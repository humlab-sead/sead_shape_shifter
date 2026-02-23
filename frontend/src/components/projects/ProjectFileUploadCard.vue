<template>
  <v-card variant="outlined">
    <v-card-title class="d-flex align-center">
      <v-icon icon="mdi-file-upload" class="mr-2" />
      Data Files
      <v-spacer />
      <v-btn
        icon="mdi-refresh"
        size="small"
        variant="text"
        :loading="loading"
        @click="loadFiles"
      />
    </v-card-title>

    <v-card-text>
      <!-- Drop Zone -->
      <div
        class="drop-zone"
        :class="{ 'drop-zone-active': isDragging }"
        @drop.prevent="handleDrop"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @click="() => fileInput?.click()"
      >
        <v-icon icon="mdi-cloud-upload" size="48" class="mb-2" color="primary" />
        <p class="text-body-1 mb-2">
          Drag and drop files here or click to browse
        </p>
        <p class="text-caption text-grey">
          Supported: Excel (.xlsx, .xls), CSV (.csv)
        </p>
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".xlsx,.xls,.csv"
          style="display: none"
          @change="handleFileSelect"
        />
        <v-btn
          color="primary"
          variant="outlined"
          class="mt-2"
          prepend-icon="mdi-upload"
          :loading="uploading"
          @click.stop="() => fileInput?.click()"
        >
          Select Files
        </v-btn>
      </div>

      <!-- Upload Progress -->
      <v-alert v-if="uploadError" type="error" variant="tonal" class="mt-4" closable @click:close="uploadError = null">
        {{ uploadError }}
      </v-alert>

      <v-alert v-if="uploadSuccess" type="success" variant="tonal" class="mt-4" closable @click:close="uploadSuccess = null">
        {{ uploadSuccess }}
      </v-alert>

      <!-- File List -->
      <div v-if="files.length > 0" class="mt-4">
        <v-list>
          <v-list-subheader>Uploaded Files ({{ files.length }})</v-list-subheader>
          <v-list-item
            v-for="file in files"
            :key="file.name"
            :title="file.name"
            :subtitle="formatFileSize(file.size_bytes)"
          >
            <template #prepend>
              <v-icon :icon="getFileIcon(file.name)" />
            </template>
            <template #append>
              <v-chip size="small" variant="tonal" color="primary">
                {{ file.location === 'local' ? 'Project' : 'Shared' }}
              </v-chip>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <!-- Empty State -->
      <v-alert v-else type="info" variant="tonal" class="mt-4">
        <v-alert-title>No files uploaded yet</v-alert-title>
        Upload Excel or CSV files to use them in your entity configurations with <code>location: local</code>.
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { projectsApi } from '@/api/projects'
import type { ProjectFileInfo } from '@/types'

const props = defineProps<{
  projectName: string
}>()

const files = ref<ProjectFileInfo[]>([])
const loading = ref(false)
const uploading = ref(false)
const uploadError = ref<string | null>(null)
const uploadSuccess = ref<string | null>(null)
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement>()

onMounted(() => {
  loadFiles()
})

async function loadFiles() {
  loading.value = true
  uploadError.value = null
  try {
    files.value = await projectsApi.listFiles(props.projectName)
  } catch (error) {
    uploadError.value = error instanceof Error ? error.message : 'Failed to load files'
  } finally {
    loading.value = false
  }
}

async function handleDrop(event: DragEvent) {
  isDragging.value = false
  const droppedFiles = Array.from(event.dataTransfer?.files || [])
  await uploadFiles(droppedFiles)
}

async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const selectedFiles = Array.from(target.files || [])
  await uploadFiles(selectedFiles)
  target.value = '' // Reset input
}

async function uploadFiles(filesToUpload: File[]) {
  if (filesToUpload.length === 0) return

  uploading.value = true
  uploadError.value = null
  uploadSuccess.value = null

  try {
    const uploadedCount = filesToUpload.length
    for (const file of filesToUpload) {
      await projectsApi.uploadFile(props.projectName, file)
    }
    uploadSuccess.value = `Successfully uploaded ${uploadedCount} file${uploadedCount > 1 ? 's' : ''}`
    await loadFiles() // Refresh list
  } catch (error) {
    uploadError.value = error instanceof Error ? error.message : 'Upload failed'
  } finally {
    uploading.value = false
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'xlsx' || ext === 'xls') return 'mdi-file-excel'
  if (ext === 'csv') return 'mdi-file-delimited'
  return 'mdi-file'
}
</script>

<style scoped>
.drop-zone {
  border: 2px dashed rgb(var(--v-theme-primary));
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  background-color: rgba(var(--v-theme-primary), 0.02);
}

.drop-zone:hover {
  background-color: rgba(var(--v-theme-primary), 0.05);
  border-color: rgb(var(--v-theme-primary));
}

.drop-zone-active {
  background-color: rgba(var(--v-theme-primary), 0.1);
  border-color: rgb(var(--v-theme-primary));
  transform: scale(1.02);
}
</style>
