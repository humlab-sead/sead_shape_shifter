<template>
  <v-expansion-panels v-model="panel" variant="accordion">
    <v-expansion-panel value="config">
      <v-expansion-panel-title>
        <div class="d-flex align-center">
          <v-icon icon="mdi-cog" class="mr-2" />
          <span class="font-weight-medium">Data Validation Options</span>
        </div>
      </v-expansion-panel-title>

      <v-expansion-panel-text>
        <v-form @submit.prevent="handleRun">
          <!-- Entity Selection -->
          <div class="mb-4">
            <v-label class="text-body-2 font-weight-medium mb-2"> Validate Specific Entities (optional) </v-label>
            <v-combobox
              v-model="selectedEntities"
              :items="availableEntities"
              multiple
              chips
              closable-chips
              clearable
              placeholder="All entities (leave empty to validate all)"
              hint="Select specific entities to validate, or leave empty for all"
              persistent-hint
            >
              <template #chip="{ item, props: chipProps }">
                <v-chip v-bind="chipProps" prepend-icon="mdi-cube" :text="item.title" />
              </template>
            </v-combobox>
          </div>

          <!-- Sample Size -->
          <div class="mb-4">
            <v-label class="text-body-2 font-weight-medium mb-2"> Sample Size </v-label>
            <v-slider v-model="sampleSize" :min="10" :max="10000" :step="10" thumb-label="always" color="info">
              <template #append>
                <v-text-field
                  v-model.number="sampleSize"
                  type="number"
                  :min="10"
                  :max="10000"
                  density="compact"
                  style="width: 100px"
                  hide-details
                  variant="outlined"
                />
              </template>
            </v-slider>
            <p class="text-caption text-grey mt-1">Number of rows to sample for validation (default: 1000)</p>
          </div>

          <!-- Validator Selection -->
          <div class="mb-4">
            <v-label class="text-body-2 font-weight-medium mb-2"> Validators to Run </v-label>
            <v-checkbox
              v-model="enabledValidators"
              label="Column Exists"
              value="column_exists"
              density="compact"
              hide-details
            >
              <template #label>
                <div>
                  <div class="font-weight-medium">Column Exists</div>
                  <div class="text-caption text-grey">Check if configured columns exist in the data</div>
                </div>
              </template>
            </v-checkbox>

            <v-checkbox
              v-model="enabledValidators"
              label="Natural Key Uniqueness"
              value="natural_key_uniqueness"
              density="compact"
              hide-details
            >
              <template #label>
                <div>
                  <div class="font-weight-medium">Natural Key Uniqueness</div>
                  <div class="text-caption text-grey">Check for duplicate natural keys in the data</div>
                </div>
              </template>
            </v-checkbox>

            <v-checkbox
              v-model="enabledValidators"
              label="Non-Empty Result"
              value="non_empty_result"
              density="compact"
              hide-details
            >
              <template #label>
                <div>
                  <div class="font-weight-medium">Non-Empty Result</div>
                  <div class="text-caption text-grey">Warn when entities return no data</div>
                </div>
              </template>
            </v-checkbox>

            <v-checkbox
              v-model="enabledValidators"
              label="Foreign Key Data"
              value="foreign_key_data"
              density="compact"
              hide-details
              disabled
            >
              <template #label>
                <div>
                  <div class="font-weight-medium">Foreign Key Data</div>
                  <div class="text-caption text-grey">Validate foreign key relationships in data (coming soon)</div>
                </div>
              </template>
            </v-checkbox>
          </div>

          <!-- Actions -->
          <div class="d-flex justify-end gap-2">
            <v-btn variant="outlined" prepend-icon="mdi-refresh" @click="handleReset"> Reset to Defaults </v-btn>
            <v-btn type="submit" color="info" variant="flat" prepend-icon="mdi-play" :loading="loading">
              Run Validation
            </v-btn>
          </div>
        </v-form>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  availableEntities?: string[]
  loading?: boolean
}

interface ValidationConfig {
  entities?: string[]
  sampleSize?: number
  validators?: string[]
}

interface Emits {
  (e: 'run', config: ValidationConfig): void
}

withDefaults(defineProps<Props>(), {
  availableEntities: () => [],
  loading: false,
})

const emit = defineEmits<Emits>()

// State
const panel = ref<string | undefined>('config')
const selectedEntities = ref<string[]>([])
const sampleSize = ref(1000)
const enabledValidators = ref(['column_exists', 'natural_key_uniqueness', 'non_empty_result'])

// Methods
function handleReset() {
  selectedEntities.value = []
  sampleSize.value = 1000
  enabledValidators.value = ['column_exists', 'natural_key_uniqueness', 'non_empty_result']
}

function handleRun() {
  const config: ValidationConfig = {}

  if (selectedEntities.value.length > 0) {
    config.entities = selectedEntities.value
  }

  if (sampleSize.value !== 1000) {
    config.sampleSize = sampleSize.value
  }

  if (enabledValidators.value.length < 3) {
    config.validators = enabledValidators.value
  }

  emit('run', config)
}
</script>
