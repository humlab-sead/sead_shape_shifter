<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-title class="d-flex align-center bg-grey-lighten-4">
      <v-icon class="mr-2">mdi-chart-box</v-icon>
      Reconciliation Quality Statistics
      <v-spacer />
      <v-btn
        icon="mdi-refresh"
        variant="text"
        size="small"
        @click="emit('refresh')"
        title="Refresh statistics"
      />
    </v-card-title>

    <v-card-text class="pa-4">
      <v-row>
        <!-- Total Queries -->
        <v-col cols="12" sm="6" md="3">
          <v-card variant="tonal" color="primary">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-bold">{{ totalQueries }}</div>
              <div class="text-caption text-grey-darken-1">Total Queries</div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Auto-Accept Rate -->
        <v-col cols="12" sm="6" md="3">
          <v-card variant="tonal" color="success">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-bold">{{ autoAcceptRate }}%</div>
              <div class="text-caption text-grey-darken-1">Auto-Accept Rate</div>
              <v-progress-linear
                :model-value="autoAcceptRate"
                color="success"
                height="6"
                class="mt-2"
              />
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Average Confidence -->
        <v-col cols="12" sm="6" md="3">
          <v-card variant="tonal" color="info">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-bold">{{ avgConfidence }}%</div>
              <div class="text-caption text-grey-darken-1">Avg. Confidence</div>
              <v-chip
                size="small"
                :color="getConfidenceColor(avgConfidence)"
                variant="flat"
                class="mt-2"
              >
                {{ getConfidenceLabel(avgConfidence) }}
              </v-chip>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Completion Percentage -->
        <v-col cols="12" sm="6" md="3">
          <v-card variant="tonal" color="warning">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-bold">{{ completionRate }}%</div>
              <div class="text-caption text-grey-darken-1">Completion Rate</div>
              <v-progress-linear
                :model-value="completionRate"
                color="warning"
                height="6"
                class="mt-2"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Detailed Breakdown -->
      <v-row class="mt-2">
        <v-col cols="12" md="6">
          <v-card variant="outlined">
            <v-card-title class="text-subtitle-1">
              <v-icon size="small" class="mr-2">mdi-chart-pie</v-icon>
              Status Breakdown
            </v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item>
                  <template v-slot:prepend>
                    <v-avatar color="success" size="32">
                      <span class="text-caption">{{ stats.autoMatched }}</span>
                    </v-avatar>
                  </template>
                  <v-list-item-title>Auto-Accepted</v-list-item-title>
                  <v-list-item-subtitle>
                    Confidence ≥ {{ autoAcceptThreshold }}%
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-chip size="small" variant="text">
                      {{ ((stats.autoMatched / totalQueries) * 100).toFixed(1) }}%
                    </v-chip>
                  </template>
                </v-list-item>

                <v-list-item>
                  <template v-slot:prepend>
                    <v-avatar color="warning" size="32">
                      <span class="text-caption">{{ stats.needsReview }}</span>
                    </v-avatar>
                  </template>
                  <v-list-item-title>Needs Review</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ reviewThreshold }}% ≤ Confidence < {{ autoAcceptThreshold }}%
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-chip size="small" variant="text">
                      {{ ((stats.needsReview / totalQueries) * 100).toFixed(1) }}%
                    </v-chip>
                  </template>
                </v-list-item>

                <v-list-item>
                  <template v-slot:prepend>
                    <v-avatar color="error" size="32">
                      <span class="text-caption">{{ stats.unmatched }}</span>
                    </v-avatar>
                  </template>
                  <v-list-item-title>Unmatched</v-list-item-title>
                  <v-list-item-subtitle>
                    Confidence < {{ reviewThreshold }}%
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-chip size="small" variant="text">
                      {{ ((stats.unmatched / totalQueries) * 100).toFixed(1) }}%
                    </v-chip>
                  </template>
                </v-list-item>

                <v-list-item v-if="stats.willNotMatch > 0">
                  <template v-slot:prepend>
                    <v-avatar color="grey" size="32">
                      <span class="text-caption">{{ stats.willNotMatch }}</span>
                    </v-avatar>
                  </template>
                  <v-list-item-title>Won't Match (Local-Only)</v-list-item-title>
                  <v-list-item-subtitle>
                    Manually marked as local identifiers
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-chip size="small" variant="text">
                      {{ ((stats.willNotMatch / totalQueries) * 100).toFixed(1) }}%
                    </v-chip>
                  </template>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <v-card variant="outlined">
            <v-card-title class="text-subtitle-1">
              <v-icon size="small" class="mr-2">mdi-gauge</v-icon>
              Quality Metrics
            </v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>High Confidence</v-list-item-title>
                  <v-list-item-subtitle>Confidence ≥ 90%</v-list-item-subtitle>
                  <template v-slot:append>
                    <v-chip size="small" color="success" variant="tonal">
                      {{ highConfidenceCount }} ({{ ((highConfidenceCount / totalQueries) * 100).toFixed(1) }}%)
                    </v-chip>
                  </template>
                </v-list-item>

                <v-list-item>
                  <v-list-item-title>Medium Confidence</v-list-item-title>
                  <v-list-item-subtitle>70% ≤ Confidence < 90%</v-list-item-subtitle>
                  <template v-slot:append>
                    <v-chip size="small" color="warning" variant="tonal">
                      {{ mediumConfidenceCount }} ({{ ((mediumConfidenceCount / totalQueries) * 100).toFixed(1) }}%)
                    </v-chip>
                  </template>
                </v-list-item>

                <v-list-item>
                  <v-list-item-title>Low Confidence</v-list-item-title>
                  <v-list-item-subtitle>Confidence < 70%</v-list-item-subtitle>
                  <template v-slot:append>
                    <v-chip size="small" color="error" variant="tonal">
                      {{ lowConfidenceCount }} ({{ ((lowConfidenceCount / totalQueries) * 100).toFixed(1) }}%)
                    </v-chip>
                  </template>
                </v-list-item>

                <v-divider class="my-2" />

                <v-list-item>
                  <v-list-item-title class="font-weight-bold">Quality Score</v-list-item-title>
                  <template v-slot:append>
                    <v-chip
                      size="large"
                      :color="getQualityScoreColor(qualityScore)"
                      variant="flat"
                    >
                      {{ qualityScore }}/100
                    </v-chip>
                  </template>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ReconciliationPreviewRow, EntityResolutionSet } from '@/types'

interface Props {
  previewData: ReconciliationPreviewRow[]
  entitySpec: EntityResolutionSet | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  refresh: []
}>()

// Thresholds
const autoAcceptThreshold = computed(() => props.entitySpec?.auto_accept_threshold || 95)
const reviewThreshold = computed(() => props.entitySpec?.review_threshold || 70)

// Basic counts
const totalQueries = computed(() => props.previewData.length)

const stats = computed(() => {
  const autoMatched = props.previewData.filter(
    row => row.confidence != null && row.confidence >= autoAcceptThreshold.value
  ).length

  const needsReview = props.previewData.filter(
    row =>
      row.confidence != null &&
      row.confidence < autoAcceptThreshold.value &&
      row.confidence >= reviewThreshold.value
  ).length

  const unmatched = props.previewData.filter(
    row => row.confidence == null || row.confidence < reviewThreshold.value
  ).length

  const willNotMatch = props.previewData.filter(row => row.will_not_match === true).length

  return { autoMatched, needsReview, unmatched, willNotMatch }
})

// Confidence distribution
const highConfidenceCount = computed(() => {
  return props.previewData.filter(row => row.confidence != null && row.confidence >= 90).length
})

const mediumConfidenceCount = computed(() => {
  return props.previewData.filter(
    row => row.confidence != null && row.confidence >= 70 && row.confidence < 90
  ).length
})

const lowConfidenceCount = computed(() => {
  return props.previewData.filter(row => row.confidence != null && row.confidence < 70).length
})

// Rates and averages
const autoAcceptRate = computed(() => {
  if (totalQueries.value === 0) return 0
  return Math.round((stats.value.autoMatched / totalQueries.value) * 100)
})

const avgConfidence = computed(() => {
  const withConfidence = props.previewData.filter(row => row.confidence != null)
  if (withConfidence.length === 0) return 0
  
  const sum = withConfidence.reduce((acc, row) => acc + (row.confidence || 0), 0)
  return Math.round(sum / withConfidence.length)
})

const completionRate = computed(() => {
  if (totalQueries.value === 0) return 0
  const completed = props.previewData.filter(row => row.target_id != null || row.will_not_match).length
  return Math.round((completed / totalQueries.value) * 100)
})

// Quality score (weighted combination of metrics)
const qualityScore = computed(() => {
  // Weighted formula:
  // - Auto-accept rate: 40%
  // - Average confidence: 30%
  // - Completion rate: 30%
  const score = 
    (autoAcceptRate.value * 0.4) +
    (avgConfidence.value * 0.3) +
    (completionRate.value * 0.3)
  
  return Math.round(score)
})

// Helper functions
function getConfidenceColor(confidence: number): string {
  if (confidence >= 90) return 'success'
  if (confidence >= 70) return 'warning'
  if (confidence >= 50) return 'orange'
  return 'error'
}

function getConfidenceLabel(confidence: number): string {
  if (confidence >= 90) return 'Excellent'
  if (confidence >= 70) return 'Good'
  if (confidence >= 50) return 'Fair'
  return 'Poor'
}

function getQualityScoreColor(score: number): string {
  if (score >= 90) return 'success'
  if (score >= 70) return 'warning'
  if (score >= 50) return 'orange'
  return 'error'
}
</script>
