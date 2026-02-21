<template>
  <v-card variant="outlined">
    <v-card-title class="d-flex align-center justify-space-between">
      <span>Connected Data Sources</span>
      <v-btn color="primary" prepend-icon="mdi-link-plus" @click="showConnectDialog = true">
        Connect Data Source
      </v-btn>
    </v-card-title>

    <v-divider />

    <!-- Loading State -->
    <v-card-text v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" />
      <p class="mt-4 text-grey">Loading data sources...</p>
    </v-card-text>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" variant="tonal" class="ma-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadDataSources">Retry</v-btn>
      </template>
    </v-alert>

    <!-- Empty State -->
    <v-card-text v-else-if="connectedSources.length === 0" class="text-center py-12">
      <v-icon icon="mdi-database-off-outline" size="64" color="grey" />
      <h3 class="text-h6 mt-4 mb-2">No Data Sources Connected</h3>
      <p class="text-grey mb-4">Connect global data sources to use them in your entities</p>
      <v-btn color="primary" prepend-icon="mdi-link-plus" @click="showConnectDialog = true">
        Connect Data Source
      </v-btn>
    </v-card-text>

    <!-- Data Sources List -->
    <v-list v-else>
      <v-list-item
        v-for="source in connectedSources"
        :key="source.name"
        :title="source.name"
        :subtitle="source.reference"
      >
        <template #prepend>
          <v-avatar :color="getSourceColor(source.reference)" variant="tonal">
            <v-icon :icon="getSourceIcon(source.reference)" />
          </v-avatar>
        </template>

        <template #append>
          <div class="d-flex gap-1">
            <v-btn
              icon="mdi-table-arrow-right"
              variant="text"
              color="primary"
              size="small"
              @click="handleCreateEntity(source.name)"
            >
              <v-icon>mdi-table-arrow-right</v-icon>
              <v-tooltip activator="parent" location="top"> Create Entity from Table </v-tooltip>
            </v-btn>
            <v-btn
              icon="mdi-link-off"
              variant="text"
              color="error"
              size="small"
              @click="handleDisconnect(source.name)"
            >
              <v-icon>mdi-link-off</v-icon>
              <v-tooltip activator="parent" location="top"> Disconnect </v-tooltip>
            </v-btn>
          </div>
        </template>

        <v-list-item-subtitle v-if="source.details" class="mt-1">
          <v-chip size="x-small" variant="outlined" class="mr-1">
            {{ source.details.driver }}
          </v-chip>
          <span v-if="source.details.host" class="text-caption">
            {{ source.details.host }}
          </span>
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <!-- Connect Data Source Dialog -->
    <v-dialog v-model="showConnectDialog" max-width="600">
      <v-card>
        <v-card-title>Connect Data Source</v-card-title>
        <v-card-subtitle> Select a global data source file to connect to this project </v-card-subtitle>

        <v-card-text>
          <v-text-field
            v-model="newSourceName"
            label="Source Name"
            hint="Name to use in this project (e.g., 'sead', 'arbodat_data')"
            persistent-hint
            variant="outlined"
            density="comfortable"
            class="mb-4"
          />

          <v-select
            v-model="selectedSourceFile"
            :items="availableSourceFiles"
            item-title="display"
            item-value="filename"
            label="Data Source File"
            hint="Select from available global data source files"
            persistent-hint
            variant="outlined"
            density="comfortable"
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <template #prepend>
                  <v-icon :icon="getDriverIcon(item.raw.driver)" />
                </template>
                <template #subtitle>
                  <span class="text-caption">{{ item.raw.driver }}</span>
                  <span v-if="item.raw.host" class="text-caption ml-2"> • {{ item.raw.host }} </span>
                </template>
              </v-list-item>
            </template>
          </v-select>

          <v-alert v-if="connectError" type="error" variant="tonal" class="mt-4">
            {{ connectError }}
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showConnectDialog = false"> Cancel </v-btn>
          <v-btn
            color="primary"
            :disabled="!newSourceName || !selectedSourceFile"
            :loading="connecting"
            @click="handleConnect"
          >
            Connect
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Disconnect Confirmation Dialog -->
    <v-dialog v-model="showDisconnectDialog" max-width="500">
      <v-card>
        <v-card-title>Disconnect Data Source?</v-card-title>
        <v-card-text>
          <p>
            Are you sure you want to disconnect
            <strong>{{ disconnectingSource }}</strong
            >?
          </p>
          <p class="text-caption text-warning mt-2">
            <v-icon icon="mdi-alert" size="small" class="mr-1" />
            Entities using this data source may become invalid.
          </p>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDisconnectDialog = false"> Cancel </v-btn>
          <v-btn color="error" :loading="disconnecting" @click="confirmDisconnect"> Disconnect </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Create Entity From Table Dialog -->
    <CreateEntityFromTableDialog
      v-model="showCreateEntityDialog"
      :project-name="props.projectName"
      :data-source="createEntityDataSource"
      @created="handleEntityCreated"
    />
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useDataSourceStore } from '@/stores/data-source'
import CreateEntityFromTableDialog from '@/components/entities/CreateEntityFromTableDialog.vue'

const props = defineProps<{
  projectName: string
}>()

const emit = defineEmits<{
  updated: []
}>()

const projectStore = useProjectStore()
const dataSourceStore = useDataSourceStore()

// State
const loading = ref(false)
const error = ref<string | null>(null)
const connectedSourcesData = ref<Record<string, string>>({})
const showConnectDialog = ref(false)
const showDisconnectDialog = ref(false)
const disconnectingSource = ref<string | null>(null)
const newSourceName = ref('')
const selectedSourceFile = ref<string | null>(null)
const connecting = ref(false)
const disconnecting = ref(false)
const connectError = ref<string | null>(null)
const showCreateEntityDialog = ref(false)
const createEntityDataSource = ref<string>('')

// Computed
const connectedSources = computed(() => {
  return Object.entries(connectedSourcesData.value).map(([name, reference]) => {
    // Parse @include reference to get filename
    const filename = reference.replace('@include:', '').trim()

    // Try to find details from loaded data sources
    const details = dataSourceStore.dataSources.find(
      (ds) => ds.filename === filename || ds.name === filename.replace('.yml', '')
    )

    return {
      name,
      reference,
      filename,
      details: details || null,
    }
  })
})

const availableSourceFiles = computed(() => {
  return dataSourceStore.sortedDataSources.map((ds) => ({
    filename: ds.filename || `${ds.name}.yml`,
    display: `${ds.name} (${ds.filename || `${ds.name}.yml`})`,
    driver: ds.driver,
    host: ds.host,
    name: ds.name,
  }))
})

// Methods
async function loadDataSources() {
  loading.value = true
  error.value = null

  try {
    // Load connected sources for this project
    connectedSourcesData.value = await projectStore.getProjectDataSources(props.projectName)

    // Only load global data sources if not already loaded (avoid duplicate fetch)
    if (dataSourceStore.dataSourceCount === 0) {
      await dataSourceStore.fetchDataSources()
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load data sources'
  } finally {
    loading.value = false
  }
}

async function handleConnect() {
  if (!newSourceName.value || !selectedSourceFile.value) return

  connecting.value = true
  connectError.value = null

  try {
    await projectStore.connectDataSource(props.projectName, newSourceName.value, selectedSourceFile.value)

    // Reload data sources
    await loadDataSources()

    // Close dialog and reset
    showConnectDialog.value = false
    newSourceName.value = ''
    selectedSourceFile.value = null

    emit('updated')
  } catch (e) {
    connectError.value = e instanceof Error ? e.message : 'Failed to connect data source'
  } finally {
    connecting.value = false
  }
}

function handleDisconnect(sourceName: string) {
  disconnectingSource.value = sourceName
  showDisconnectDialog.value = true
}

async function confirmDisconnect() {
  if (!disconnectingSource.value) return

  disconnecting.value = true

  try {
    await projectStore.disconnectDataSource(props.projectName, disconnectingSource.value)

    // Reload data sources
    await loadDataSources()

    // Close dialog
    showDisconnectDialog.value = false
    disconnectingSource.value = null

    emit('updated')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to disconnect data source'
  } finally {
    disconnecting.value = false
  }
}

function getSourceColor(reference: string): string {
  if (reference.includes('@include:')) return 'primary'
  return 'grey'
}

function getSourceIcon(reference: string): string {
  if (reference.includes('@include:')) return 'mdi-file-link-outline'
  return 'mdi-database-outline'
}

function getDriverIcon(driver: string): string {
  const icons: Record<string, string> = {
    postgresql: 'mdi-database',
    postgres: 'mdi-database',
    sqlite: 'mdi-database-outline',
    ucanaccess: 'mdi-microsoft-access',
    access: 'mdi-microsoft-access',
    csv: 'mdi-file-delimited-outline',
  }
  return icons[driver?.toLowerCase()] || 'mdi-database'
}

function handleCreateEntity(sourceName: string) {
  createEntityDataSource.value = sourceName
  showCreateEntityDialog.value = true
}

function handleEntityCreated(entityName: string) {
  console.log(`Entity '${entityName}' created successfully`)
  emit('updated')
}

// Lifecycle
onMounted(() => {
  loadDataSources()
})
</script>
