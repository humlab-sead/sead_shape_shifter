<template>
  <v-dialog
    :model-value="modelValue"
    max-width="840"
    scrollable
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card data-testid="reconciliation-help-dialog">
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" color="primary">mdi-help-circle-outline</v-icon>
        <span>Reconcile &amp; Review help</span>
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" aria-label="Close reconciliation help" @click="close" />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <p>{{ reconciliationHelp.description }}</p>

        <h3 class="text-subtitle-1 font-weight-bold mt-4 mb-2">Quick workflow</h3>
        <ol class="workflow-list">
          <li v-for="step in reconciliationHelp.workflow" :key="step.label">
            <strong>{{ step.label }}.</strong> {{ step.description }}
          </li>
        </ol>

        <v-alert type="info" variant="tonal" class="mt-4">
          An accepted decision does not change the effective ID until it is exported. Manual links are saved directly
          and are trusted, but are not checked against SEAD.
        </v-alert>

        <v-expansion-panels variant="accordion" multiple class="mt-4">
          <v-expansion-panel>
            <v-expansion-panel-title>Grid columns</v-expansion-panel-title>
            <v-expansion-panel-text>
              <dl class="help-list">
                <div v-for="item in reconciliationHelp.columns" :key="item.label" class="help-item">
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.description }}</dd>
                </div>
              </dl>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <v-expansion-panel>
            <v-expansion-panel-title>Toolbar controls and filters</v-expansion-panel-title>
            <v-expansion-panel-text>
              <dl class="help-list">
                <div v-for="item in reconciliationHelp.controls" :key="item.label" class="help-item">
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.description }}</dd>
                </div>
              </dl>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <v-expansion-panel>
            <v-expansion-panel-title>Row action buttons</v-expansion-panel-title>
            <v-expansion-panel-text>
              <dl class="help-list">
                <div v-for="item in reconciliationHelp.rowActions" :key="item.label" class="help-item">
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.description }}</dd>
                </div>
              </dl>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-btn
          data-testid="reconciliation-help-guide"
          href="/help?doc=USER_GUIDE#reconciliation-workflow"
          variant="text"
          prepend-icon="mdi-book-open-variant"
        >
          Full reconciliation guide
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { reconciliationHelp } from './reconciliationHelp'

interface Props {
  modelValue: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function close() {
  emit('update:modelValue', false)
}
</script>

<style scoped>
.workflow-list {
  padding-left: 1.25rem;
}

.workflow-list li + li {
  margin-top: 0.5rem;
}

.help-list {
  margin: 0;
}

.help-item + .help-item {
  margin-top: 0.75rem;
}

.help-item dt {
  font-weight: 600;
}

.help-item dd {
  margin-left: 0;
}
</style>
