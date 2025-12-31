<template>
  <v-dialog v-model="dialog" max-width="900">
    <template v-slot:activator="{ props }">
      <v-btn
        v-bind="props"
        size="small"
        color="primary"
        variant="text"
        prepend-icon="mdi-test-tube"
        :disabled="disabled"
      >
        Test Join
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-test-tube" class="mr-2" />
        Test Foreign Key Join
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="dialog = false" />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <!-- Foreign Key Info -->
        <v-alert type="info" variant="tonal" class="mb-4">
          <div class="text-subtitle-2 mb-1">Testing Join:</div>
          <div>
            <strong>{{ entityName }}</strong> →
            <strong>{{ foreignKey.entity }}</strong>
          </div>
          <div class="text-caption mt-1">
            Keys: {{ foreignKey.local_keys.join(', ') }} →
            {{ foreignKey.remote_keys.join(', ') }}
          </div>
          <div class="text-caption">
            Type: {{ foreignKey.how || 'left' }}
          </div>
        </v-alert>

        <!-- Test Project -->
        <div class="mb-4">
          <v-select
            v-model="sampleSize"
            :items="sampleSizeOptions"
            label="Sample Size"
            hint="Number of rows to test"
            persistent-hint
            density="compact"
            :disabled="loading"
          />
        </div>

        <!-- Test Button -->
        <div class="mb-4">
          <v-btn
            color="primary"
            :loading="loading"
            @click="runTest"
            prepend-icon="mdi-play"
            block
          >
            Run Join Test
          </v-btn>
        </div>

        <!-- Results -->
        <div v-if="testResult">
          <!-- Overall Status -->
          <v-alert
            :type="testPassed ? 'success' : 'warning'"
            variant="tonal"
            class="mb-4"
          >
            <div class="d-flex align-center">
              <v-icon
                :icon="testPassed ? 'mdi-check-circle' : 'mdi-alert-circle'"
                class="mr-2"
              />
              <span class="text-subtitle-1">
                {{ testPassed ? 'Join Test Passed' : 'Join Test Issues Detected' }}
              </span>
              <v-spacer />
              <v-chip size="small" variant="text">
                {{ testResult.execution_time_ms }}ms
              </v-chip>
            </div>
          </v-alert>

          <!-- Statistics -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1">
              <v-icon icon="mdi-chart-bar" class="mr-2" size="small" />
              Join Statistics
            </v-card-title>
            <v-card-text>
              <v-row dense>
                <v-col cols="6">
                  <div class="text-caption text-grey">Total Rows</div>
                  <div class="text-h6">{{ testResult.statistics.total_rows }}</div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption text-grey">Match Rate</div>
                  <div class="text-h6" :class="`text-${matchPercentageColor}`">
                    {{ matchPercentageText }}
                  </div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption text-grey">Matched Rows</div>
                  <div class="text-subtitle-1 text-success">
                    {{ testResult.statistics.matched_rows }}
                  </div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption text-grey">Unmatched Rows</div>
                  <div class="text-subtitle-1" :class="testResult.statistics.unmatched_rows > 0 ? 'text-warning' : ''">
                    {{ testResult.statistics.unmatched_rows }}
                  </div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption text-grey">Null Keys</div>
                  <div class="text-subtitle-1" :class="testResult.statistics.null_key_rows > 0 ? 'text-warning' : ''">
                    {{ testResult.statistics.null_key_rows }}
                  </div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption text-grey">Duplicate Matches</div>
                  <div class="text-subtitle-1" :class="testResult.statistics.duplicate_matches > 0 ? 'text-info' : ''">
                    {{ testResult.statistics.duplicate_matches }}
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- Cardinality -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1">
              <v-icon icon="mdi-relation" class="mr-2" size="small" />
              Cardinality Analysis
            </v-card-title>
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <span class="text-body-2 mr-2">Expected:</span>
                <v-chip size="small" variant="tonal">
                  {{ testResult.cardinality.expected }}
                </v-chip>
                <v-icon
                  :icon="testResult.cardinality.matches ? 'mdi-check' : 'mdi-arrow-right'"
                  class="mx-2"
                  :color="testResult.cardinality.matches ? 'success' : 'warning'"
                />
                <span class="text-body-2 mr-2">Actual:</span>
                <v-chip
                  size="small"
                  :color="cardinalityStatusColor"
                  variant="tonal"
                >
                  {{ testResult.cardinality.actual }}
                </v-chip>
              </div>
              <div class="text-caption text-grey">
                {{ testResult.cardinality.explanation }}
              </div>
            </v-card-text>
          </v-card>

          <!-- Warnings -->
          <v-card v-if="hasWarnings" variant="outlined" class="mb-4" color="warning">
            <v-card-title class="text-subtitle-1">
              <v-icon icon="mdi-alert" class="mr-2" size="small" />
              Warnings ({{ testResult.warnings.length }})
            </v-card-title>
            <v-card-text>
              <ul class="pl-4">
                <li v-for="(warning, index) in testResult.warnings" :key="index" class="text-body-2 mb-1">
                  {{ warning }}
                </li>
              </ul>
            </v-card-text>
          </v-card>

          <!-- Recommendations -->
          <v-card v-if="hasRecommendations" variant="outlined" class="mb-4" color="info">
            <v-card-title class="text-subtitle-1">
              <v-icon icon="mdi-lightbulb-on" class="mr-2" size="small" />
              Recommendations ({{ testResult.recommendations.length }})
            </v-card-title>
            <v-card-text>
              <ul class="pl-4">
                <li v-for="(rec, index) in testResult.recommendations" :key="index" class="text-body-2 mb-1">
                  {{ rec }}
                </li>
              </ul>
            </v-card-text>
          </v-card>

          <!-- Unmatched Rows Sample -->
          <v-expansion-panels v-if="testResult.unmatched_sample.length > 0">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon icon="mdi-table-search" class="mr-2" size="small" />
                  <span>Unmatched Rows Sample ({{ testResult.unmatched_sample.length }})</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-table density="compact">
                  <thead>
                    <tr>
                      <th class="text-left">Key Values</th>
                      <th class="text-left">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, index) in testResult.unmatched_sample" :key="index">
                      <td>
                        <v-chip
                          v-for="(value, vIndex) in row.local_key_values"
                          :key="vIndex"
                          size="x-small"
                          class="mr-1"
                        >
                          {{ value }}
                        </v-chip>
                      </td>
                      <td class="text-caption text-grey">{{ row.reason }}</td>
                    </tr>
                  </tbody>
                </v-table>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>

        <!-- Error -->
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
          {{ error }}
        </v-alert>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="dialog = false">
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useForeignKeyTester } from '@/composables/useForeignKeyTester'

interface ForeignKey {
  entity: string
  local_keys: string[]
  remote_keys: string[]
  how?: string
}

interface Props {
  configName: string
  entityName: string
  foreignKey: ForeignKey
  foreignKeyIndex: number
  disabled?: boolean
}

const props = defineProps<Props>()

const dialog = ref(false)
const sampleSize = ref(100)
const sampleSizeOptions = [10, 50, 100, 200, 500, 1000]

const {
  loading,
  error,
  testResult,
  testForeignKey,
  testPassed,
  matchPercentageColor,
  cardinalityStatusColor,
  hasWarnings,
  hasRecommendations,
  matchPercentageText
} = useForeignKeyTester()

const runTest = async () => {
  await testForeignKey(props.configName, props.entityName, props.foreignKeyIndex, sampleSize.value)
}
</script>

<style scoped>
.text-caption {
  line-height: 1.4;
}
</style>
