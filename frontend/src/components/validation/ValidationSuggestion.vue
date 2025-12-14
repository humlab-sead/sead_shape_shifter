<template>
  <v-card v-if="hasAutoFixableIssues" variant="outlined" color="info" class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon icon="mdi-lightbulb-on" class="mr-2" color="info" />
      <span>Suggested Fixes</span>
      <v-chip size="small" class="ml-2">
        {{ autoFixableCount }} auto-fixable
      </v-chip>
    </v-card-title>

    <v-card-text>
      <p class="text-body-2 mb-4">
        The following issues can be automatically fixed. Review the suggestions and apply them individually or all at once.
      </p>

      <v-list>
        <v-list-item
          v-for="(issue, index) in autoFixableIssues"
          :key="index"
          class="mb-2"
        >
          <template #prepend>
            <v-icon
              :icon="issue.severity === 'error' ? 'mdi-alert-circle' : 'mdi-alert'"
              :color="issue.severity === 'error' ? 'error' : 'warning'"
            />
          </template>

          <v-list-item-title class="mb-1">{{ issue.message }}</v-list-item-title>

          <v-list-item-subtitle v-if="issue.entity || issue.field" class="mb-2">
            <v-chip
              v-if="issue.entity"
              size="x-small"
              variant="outlined"
              prepend-icon="mdi-cube"
              class="mr-1"
            >
              {{ issue.entity }}
            </v-chip>
            <v-chip
              v-if="issue.field"
              size="x-small"
              variant="outlined"
              prepend-icon="mdi-table-column"
              class="mr-1"
            >
              {{ issue.field }}
            </v-chip>
          </v-list-item-subtitle>

          <v-alert
            v-if="issue.suggestion"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-2 mb-2"
          >
            <div class="d-flex align-center justify-space-between">
              <div class="text-body-2">
                <strong>Suggestion:</strong> {{ issue.suggestion }}
              </div>
              <v-tooltip text="Preview and apply automated fix with backup" location="bottom">
                <template v-slot:activator="{ props }">
                  <v-btn
                    v-bind="props"
                    size="small"
                    variant="flat"
                    color="info"
                    prepend-icon="mdi-wrench"
                    :disabled="applyingFixes"
                    @click="handleApplySingle(issue, index)"
                  >
                    Apply Fix
                  </v-btn>
                </template>
              </v-tooltip>
            </div>
          </v-alert>
        </v-list-item>
      </v-list>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        variant="outlined"
        prepend-icon="mdi-close"
        @click="emit('dismiss')"
      >
        Dismiss
      </v-btn>
      <v-btn
        color="info"
        variant="flat"
        prepend-icon="mdi-auto-fix"
        :loading="applyingFixes"
        :disabled="autoFixableCount === 0"
        @click="handleApplyAll"
      >
        Apply All Fixes
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ValidationError } from '@/types'

interface Props {
  issues: ValidationError[]
}

interface Emits {
  (e: 'apply-fix', issue: ValidationError, index: number): void
  (e: 'apply-all'): void
  (e: 'dismiss'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const applyingFixes = ref(false)

const autoFixableIssues = computed(() => {
  return props.issues.filter((issue) => issue.auto_fixable === true)
})

const hasAutoFixableIssues = computed(() => {
  return autoFixableIssues.value.length > 0
})

const autoFixableCount = computed(() => {
  return autoFixableIssues.value.length
})

async function handleApplySingle(issue: ValidationError, index: number) {
  emit('apply-fix', issue, index)
}

async function handleApplyAll() {
  applyingFixes.value = true
  try {
    emit('apply-all')
  } finally {
    // Keep loading state, parent will reset when done
    setTimeout(() => {
      applyingFixes.value = false
    }, 500)
  }
}
</script>
