<template>
  <v-dialog v-model="internalShow" max-width="800" persistent>
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between bg-info">
        <div class="d-flex align-center">
          <v-icon icon="mdi-auto-fix" class="mr-2" />
          <span>Preview Auto-Fixes</span>
        </div>
        <v-btn icon="mdi-close" variant="text" size="small" @click="handleCancel" />
      </v-card-title>

      <!-- Loading State -->
      <v-card-text v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-grey">Analyzing fixes...</p>
      </v-card-text>

      <!-- Error State -->
      <v-alert v-else-if="error" type="error" variant="tonal" class="ma-4">
        <v-alert-title>Error</v-alert-title>
        {{ error }}
      </v-alert>

      <!-- Preview Content -->
      <div v-else-if="preview">
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <div class="d-flex align-center">
              <v-icon icon="mdi-information" class="mr-2" />
              <div>
                <strong>{{ preview.fixable_count }}</strong> of <strong>{{ preview.total_suggestions }}</strong> issues
                can be automatically fixed.
                <div v-if="preview.fixable_count > 0" class="text-caption mt-1">
                  A backup will be created before applying changes.
                </div>
              </div>
            </div>
          </v-alert>

          <!-- Changes List -->
          <v-list v-if="preview.changes && preview.changes.length > 0">
            <v-list-item v-for="(change, index) in preview.changes" :key="index" class="mb-2">
              <template #prepend>
                <v-icon
                  :icon="change.auto_fixable ? 'mdi-check-circle' : 'mdi-alert-circle'"
                  :color="change.auto_fixable ? 'success' : 'warning'"
                />
              </template>

              <v-list-item-title class="font-weight-medium">
                {{ change.entity }}
              </v-list-item-title>

              <v-list-item-subtitle class="mb-2"> Issue: {{ change.issue_code }} </v-list-item-subtitle>

              <!-- Actions -->
              <v-expansion-panels variant="accordion" class="mt-2">
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <span class="text-body-2">
                      {{ change.actions.length }}
                      {{ change.actions.length === 1 ? 'action' : 'actions' }}
                    </span>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-list density="compact">
                      <v-list-item v-for="(action, actionIndex) in change.actions" :key="actionIndex" class="px-0">
                        <v-list-item-title class="text-body-2">
                          <v-chip size="x-small" :color="getActionColor(action.type)" class="mr-2">
                            {{ action.type }}
                          </v-chip>
                          {{ action.description }}
                        </v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>

              <!-- Warnings -->
              <v-alert
                v-if="change.warnings && change.warnings.length > 0"
                type="warning"
                variant="tonal"
                density="compact"
                class="mt-2"
              >
                <ul class="pl-4 mb-0">
                  <li v-for="(warning, wIndex) in change.warnings" :key="wIndex" class="text-body-2">
                    {{ warning }}
                  </li>
                </ul>
              </v-alert>

              <!-- Non-auto-fixable notice -->
              <v-alert v-if="!change.auto_fixable" type="info" variant="tonal" density="compact" class="mt-2">
                <div class="d-flex align-center">
                  <v-icon icon="mdi-hand-back-right" size="small" class="mr-2" />
                  <span class="text-body-2">Manual fix required</span>
                </div>
              </v-alert>
            </v-list-item>
          </v-list>

          <!-- No fixable issues -->
          <v-alert v-else type="warning" variant="tonal">
            No automatically fixable issues found. All issues require manual intervention.
          </v-alert>
        </v-card-text>

        <v-divider />

        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" prepend-icon="mdi-cancel" @click="handleCancel"> Cancel </v-btn>
          <v-btn
            v-if="preview.fixable_count > 0"
            color="info"
            variant="flat"
            prepend-icon="mdi-check"
            :loading="applying"
            @click="handleApply"
          >
            Apply {{ preview.fixable_count }}
            {{ preview.fixable_count === 1 ? 'Fix' : 'Fixes' }}
          </v-btn>
        </v-card-actions>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface FixAction {
  type: string
  entity: string
  field: string | null
  old_value: any
  new_value: any
  description: string
}

interface FixChange {
  entity: string
  issue_code: string
  auto_fixable: boolean
  actions: FixAction[]
  warnings?: string[]
}

interface FixPreview {
  project_name: string
  fixable_count: number
  total_suggestions: number
  changes: FixChange[]
}

interface Props {
  show: boolean
  preview: FixPreview | null
  loading?: boolean
  error?: string | null
}

interface Emits {
  (e: 'update:show', value: boolean): void
  (e: 'apply'): void
  (e: 'cancel'): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
})

const emit = defineEmits<Emits>()

const applying = ref(false)

const internalShow = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value),
})

function getActionColor(type: string): string {
  const colorMap: Record<string, string> = {
    remove_column: 'error',
    add_column: 'success',
    update_reference: 'warning',
    add_constraint: 'info',
    remove_constraint: 'warning',
    update_query: 'primary',
    add_entity: 'success',
    remove_entity: 'error',
  }
  return colorMap[type] || 'default'
}

function handleCancel() {
  emit('cancel')
  emit('update:show', false)
}

async function handleApply() {
  applying.value = true
  try {
    emit('apply')
  } finally {
    // Parent will reset applying state
    setTimeout(() => {
      applying.value = false
    }, 500)
  }
}

// Reset applying state when dialog closes
watch(
  () => props.show,
  (newValue) => {
    if (!newValue) {
      applying.value = false
    }
  }
)
</script>
