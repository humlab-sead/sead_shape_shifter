<template>
  <v-container fluid class="pa-6">
    <!-- Header -->
    <v-row>
      <v-col>
        <div class="d-flex align-center justify-space-between mb-6">
          <div class="d-flex align-center">
            <v-btn
              icon="mdi-arrow-left"
              variant="text"
              @click="$router.push({ name: 'configurations' })"
            />
            <div class="ml-2">
              <h1 class="text-h4">{{ configName }}</h1>
              <div class="d-flex align-center mt-1">
                <v-chip
                  v-if="entityCount > 0"
                  size="small"
                  variant="outlined"
                  prepend-icon="mdi-cube-outline"
                  class="mr-2"
                >
                  {{ entityCount }} {{ entityCount === 1 ? 'entity' : 'entities' }}
                </v-chip>
                <v-chip
                  v-if="validationResult"
                  size="small"
                  :color="validationChipColor"
                  variant="tonal"
                  :prepend-icon="validationChipIcon"
                >
                  {{ validationChipText }}
                </v-chip>
              </div>
            </div>
          </div>

          <div class="d-flex gap-2">
            <v-btn
              variant="outlined"
              prepend-icon="mdi-play-circle-outline"
              color="success"
              @click="handleTestRun"
            >
              Test Run
            </v-btn>
            <v-btn
              variant="outlined"
              prepend-icon="mdi-check-circle-outline"
              :loading="validationLoading"
              @click="handleValidate"
            >
              Validate
            </v-btn>
            <v-btn
              variant="outlined"
              prepend-icon="mdi-history"
              @click="showBackupsDialog = true"
            >
              Backups
            </v-btn>
            <v-btn
              color="primary"
              prepend-icon="mdi-content-save"
              :disabled="!hasUnsavedChanges"
              @click="handleSave"
            >
              Save Changes
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="configLoading">
      <v-col cols="12" class="text-center py-12">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-grey">Loading configuration...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-alert v-else-if="configError" type="error" variant="tonal">
      <v-alert-title>Error Loading Configuration</v-alert-title>
      {{ configError }}
      <template #append>
        <v-btn variant="text" @click="handleRefresh">Retry</v-btn>
      </template>
    </v-alert>

    <!-- Main Content -->
    <v-row v-else-if="selectedConfig">
      <v-col cols="12">
        <v-tabs v-model="activeTab" bg-color="transparent">
          <v-tab value="entities">
            <v-icon icon="mdi-cube-outline" class="mr-2" />
            Entities
          </v-tab>
          <v-tab value="validation">
            <v-icon icon="mdi-check-circle-outline" class="mr-2" />
            Validation
            <v-badge
              v-if="validationResult && (hasErrors || hasWarnings)"
              :content="errorCount + warningCount"
              :color="hasErrors ? 'error' : 'warning'"
              inline
              class="ml-2"
            />
          </v-tab>
          <v-tab value="settings">
            <v-icon icon="mdi-cog-outline" class="mr-2" />
            Settings
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab" class="mt-4">
          <!-- Entities Tab -->
          <v-window-item value="entities">
            <entity-list-card
              :config-name="configName"
              @entity-updated="handleEntityUpdated"
            />
          </v-window-item>

          <!-- Validation Tab -->
          <v-window-item value="validation">
            <validation-panel
              :config-name="configName"
              :validation-result="validationResult"
              :loading="validationLoading"
              @validate="handleValidate"
            />
          </v-window-item>

          <!-- Settings Tab -->
          <v-window-item value="settings">
            <v-card variant="outlined">
              <v-card-text>
                <p class="text-h6 mb-4">Configuration Settings</p>
                <p class="text-body-2 text-grey">
                  Advanced settings and options will be available here.
                </p>
              </v-card-text>
            </v-card>
          </v-window-item>
        </v-window>
      </v-col>
    </v-row>

    <!-- Backups Dialog -->
    <v-dialog v-model="showBackupsDialog" max-width="600">
      <v-card>
        <v-card-title>
          <v-icon icon="mdi-history" class="mr-2" />
          Configuration Backups
        </v-card-title>
        <v-card-text>
          <v-list v-if="backups.length > 0">
            <v-list-item
              v-for="backup in backups"
              :key="backup.file_path"
              @click="handleRestoreBackup(backup.file_path)"
            >
              <template #prepend>
                <v-icon icon="mdi-file-clock-outline" />
              </template>
              <v-list-item-title>{{ backup.file_name }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatBackupDate(backup.created_at) }}
              </v-list-item-subtitle>
              <template #append>
                <v-btn
                  icon="mdi-restore"
                  variant="text"
                  size="small"
                  @click.stop="handleRestoreBackup(backup.file_path)"
                />
              </template>
            </v-list-item>
          </v-list>
          <v-alert v-else type="info" variant="tonal">
            No backups available for this configuration.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showBackupsDialog = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Success Snackbar -->
    <v-snackbar v-model="showSuccessSnackbar" color="success" timeout="3000">
      {{ successMessage }}
      <template #actions>
        <v-btn variant="text" @click="showSuccessSnackbar = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useConfigurations, useEntities, useValidation } from '@/composables'
import EntityListCard from '@/components/entities/EntityListCard.vue'
import ValidationPanel from '@/components/validation/ValidationPanel.vue'

const route = useRoute()
const configName = computed(() => route.params.name as string)

// Composables
const {
  selectedConfig,
  loading: configLoading,
  error: configError,
  hasUnsavedChanges,
  backups,
  select,
  update,
  clearError,
  fetchBackups,
  restore,
  markAsChanged,
} = useConfigurations({ autoFetch: false })

const { entityCount } = useEntities({
  configName: configName.value,
  autoFetch: true,
})

const {
  validationResult,
  loading: validationLoading,
  hasErrors,
  hasWarnings,
  errorCount,
  warningCount,
  validate,
} = useValidation({
  configName: configName.value,
  autoValidate: false,
})

// Local state
const activeTab = ref('entities')
const showBackupsDialog = ref(false)
const showSuccessSnackbar = ref(false)
const successMessage = ref('')

// Computed
const validationChipColor = computed(() => {
  if (!validationResult.value) return 'default'
  if (hasErrors.value) return 'error'
  if (hasWarnings.value) return 'warning'
  return 'success'
})

const validationChipIcon = computed(() => {
  if (!validationResult.value) return 'mdi-help-circle'
  if (hasErrors.value) return 'mdi-alert-circle'
  if (hasWarnings.value) return 'mdi-alert'
  return 'mdi-check-circle'
})

const validationChipText = computed(() => {
  if (!validationResult.value) return 'Not validated'
  if (hasErrors.value) return `${errorCount.value} errors`
  if (hasWarnings.value) return `${warningCount.value} warnings`
  return 'Valid'
})

// Methods
function handleTestRun() {
  window.location.href = `/test-run/${configName.value}`
}

async function handleValidate() {
  try {
    await validate(configName.value)
    successMessage.value = 'Configuration validated successfully'
    showSuccessSnackbar.value = true
  } catch (err) {
    console.error('Validation failed:', err)
  }
}

async function handleSave() {
  if (!selectedConfig.value) return

  try {
    await update(configName.value, {
      entities: selectedConfig.value.entities,
      options: selectedConfig.value.options ?? {},
    })
    successMessage.value = 'Configuration saved successfully'
    showSuccessSnackbar.value = true
  } catch (err) {
    console.error('Failed to save configuration:', err)
  }
}

async function handleRefresh() {
  clearError()
  if (configName.value) {
    await select(configName.value)
  }
}

function handleEntityUpdated() {
  markAsChanged()
}

async function handleRestoreBackup(backupPath: string) {
  try {
    await restore(configName.value, backupPath)
    successMessage.value = 'Backup restored successfully'
    showSuccessSnackbar.value = true
    showBackupsDialog.value = false
  } catch (err) {
    console.error('Failed to restore backup:', err)
  }
}

function formatBackupDate(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString()
}

// Lifecycle
onMounted(async () => {
  if (configName.value) {
    await select(configName.value)
    await fetchBackups(configName.value)
  }
})

// Watch for config name changes
watch(
  () => configName.value,
  async (newName) => {
    if (newName) {
      await select(newName)
      await fetchBackups(newName)
    }
  }
)
</script>

<style scoped>
.gap-2 {
  gap: 0.5rem;
}
</style>
