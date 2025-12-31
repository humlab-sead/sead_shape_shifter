<template>
  <v-expansion-panels v-model="panel">
    <v-expansion-panel value="preview">
      <v-expansion-panel-title>
        <div class="d-flex align-center">
          <v-icon icon="mdi-eye-outline" class="mr-2" />
          <span>Data Preview</span>
          <v-chip v-if="rowCount > 0" size="small" variant="flat" color="primary" class="ml-3">
            {{ rowCount }} rows
          </v-chip>
        </div>
      </v-expansion-panel-title>

      <v-expansion-panel-text>
        <!-- Controls -->
        <div class="d-flex align-center gap-2 mb-4">
          <!-- Row limit selector -->
          <v-select
            v-model="localLimit"
            :items="limitOptions"
            item-title="title"
            item-value="value"
            label="Rows to preview"
            density="compact"
            variant="outlined"
            style="max-width: 220px"
            hide-details
            @update:model-value="handleLimitChange"
          />

          <!-- Load preview button -->
          <v-btn color="primary" variant="flat" :loading="loading" :disabled="!entityName" @click="loadPreview">
            <v-icon icon="mdi-play" start />
            Load Preview
          </v-btn>

          <!-- Refresh button -->
          <v-btn variant="outlined" :loading="loading" :disabled="!hasData" @click="refreshPreview">
            <v-icon icon="mdi-refresh" start />
            Refresh
          </v-btn>

          <!-- Clear cache button -->
          <v-btn variant="text" color="warning" :disabled="loading" @click="clearCache">
            <v-icon icon="mdi-cache-remove" start />
            Clear Cache
          </v-btn>

          <v-spacer />

          <!-- Export button -->
          <v-menu v-if="hasData">
            <template #activator="{ props: menuProps }">
              <v-btn variant="outlined" v-bind="menuProps">
                <v-icon icon="mdi-download" start />
                Export
              </v-btn>
            </template>
            <v-list>
              <v-list-item @click="exportToCSV">
                <v-list-item-title>
                  <v-icon icon="mdi-file-delimited" start size="small" />
                  Export as CSV
                </v-list-item-title>
              </v-list-item>
              <v-list-item @click="exportToJSON">
                <v-list-item-title>
                  <v-icon icon="mdi-code-json" start size="small" />
                  Export as JSON
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>

        <!-- Warning for "All rows" selection -->
        <v-alert v-if="localLimit === null" type="warning" variant="tonal" density="compact" class="mb-4">
          <div class="d-flex align-center">
            <v-icon icon="mdi-alert" class="mr-2" />
            <div>
              <strong>All rows selected:</strong> Loading the entire dataset may take longer and consume more memory for
              large entities.
            </div>
          </div>
        </v-alert>

        <!-- Preview component -->
        <entity-data-preview :preview-data="previewData" :loading="loading" :error="error" @refresh="refreshPreview" />

        <!-- Info message for no entity -->
        <v-alert v-if="!entityName" type="info" variant="tonal" density="compact" class="mt-4">
          Save the entity first to preview its data
        </v-alert>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useEntityPreview } from '@/composables/useEntityPreview'
import EntityDataPreview from './EntityDataPreview.vue'

interface Props {
  projectName: string
  entityName: string
  autoLoad?: boolean
  autoRefresh?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  autoLoad: false,
  autoRefresh: false,
})

const emit = defineEmits<{
  loaded: [rows: number]
  error: [error: string]
}>()

// Composable
const { loading, error, previewData, hasData, rowCount, previewEntity, invalidateCache, clearError } =
  useEntityPreview()

// Local state
const panel = ref<string | undefined>(props.autoLoad ? 'preview' : undefined)
const localLimit = ref<number | null>(50)
const limitOptions = [
  { title: '10 rows', value: 10 },
  { title: '25 rows', value: 25 },
  { title: '50 rows', value: 50 },
  { title: '100 rows', value: 100 },
  { title: '200 rows', value: 200 },
  { title: '500 rows', value: 500 },
  { title: '1,000 rows', value: 1000 },
  { title: '5,000 rows', value: 5000 },
  { title: 'All rows', value: null },
]

// Debounced auto-refresh
let refreshTimeout: ReturnType<typeof setTimeout> | null = null

// Watch for entity changes with debouncing
watch(
  () => ({ name: props.entityName, config: props.projectName }),
  (newVal, oldVal) => {
    // Clear existing timeout
    if (refreshTimeout) {
      clearTimeout(refreshTimeout)
      refreshTimeout = null
    }

    // Initial load or auto-load
    if (newVal.name && props.autoLoad && !oldVal) {
      loadPreview()
      return
    }

    // Auto-refresh on entity name change (after initial load)
    if (
      props.autoRefresh &&
      newVal.name &&
      oldVal &&
      (newVal.name !== oldVal.name || newVal.config !== oldVal.config)
    ) {
      // Debounce preview refresh by 1 second
      refreshTimeout = setTimeout(() => {
        if (hasData.value) {
          loadPreview()
        }
      }, 1000)
    }
  },
  { immediate: true }
)

// Watch for errors and emit
watch(error, (newError) => {
  if (newError) {
    emit('error', newError)
  }
})

// Watch for successful loads
watch(rowCount, (count) => {
  if (count > 0) {
    emit('loaded', count)
  }
})

async function loadPreview() {
  if (!props.entityName) return

  clearError()
  const result = await previewEntity(props.projectName, props.entityName, localLimit.value)

  if (result) {
    // Auto-expand panel on successful load
    panel.value = 'preview'
  }
}

async function refreshPreview() {
  await loadPreview()
}

async function clearCache() {
  const success = await invalidateCache(props.projectName, props.entityName)
  if (success) {
    // Reload preview after cache clear
    await loadPreview()
  }
}

function handleLimitChange() {
  // Auto-reload if data is already loaded
  if (hasData.value) {
    loadPreview()
  }
}

function exportToCSV() {
  if (!previewData.value) return

  const { columns, rows } = previewData.value

  // CSV header
  const header = columns.map((c) => c.name).join(',')

  // CSV rows
  const csvRows = rows.map((row) => {
    return columns
      .map((col) => {
        const value = row[col.name]
        if (value === null || value === undefined) return ''
        // Escape quotes and wrap in quotes if contains comma
        const strValue = String(value)
        if (strValue.includes(',') || strValue.includes('"') || strValue.includes('\n')) {
          return `"${strValue.replace(/"/g, '""')}"`
        }
        return strValue
      })
      .join(',')
  })

  const csv = [header, ...csvRows].join('\n')

  // Download
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.entityName}_preview.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function exportToJSON() {
  if (!previewData.value) return

  const json = JSON.stringify(previewData.value, null, 2)

  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.entityName}_preview.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
