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

        <v-alert
          v-if="workspaceTopic"
          type="info"
          variant="tonal"
          class="mt-4"
          data-testid="reconciliation-help-workspace"
        >
          <div class="text-subtitle-2 font-weight-bold mb-1">{{ workspaceTopic.title }}</div>
          <p class="mb-2">{{ workspaceTopic.description }}</p>
          <div v-for="group in workspaceTopic.groups" :key="group.title" class="mb-2">
            <div class="font-weight-medium">{{ group.title }}</div>
            <ul class="workspace-help-list">
              <li v-for="tip in group.tips" :key="tip">{{ tip }}</li>
            </ul>
          </div>
          <div v-if="workspaceTopic.shortcuts?.length">
            <div class="font-weight-medium">Shortcuts</div>
            <div v-for="shortcut in workspaceTopic.shortcuts" :key="shortcut.keys" class="text-body-2">
              <strong>{{ shortcut.keys }}</strong> — {{ shortcut.action }}
            </div>
          </div>
        </v-alert>

        <h3 class="text-subtitle-1 font-weight-bold mt-4 mb-2">Quick workflow</h3>
        <ol class="workflow-list">
          <li v-for="step in reconciliationHelp.workflow" :key="step.label">
            <strong>{{ step.label }}.</strong> {{ step.description }}
          </li>
        </ol>

        <v-alert type="info" variant="tonal" class="mt-4">
          Accepting a candidate does not change the current ID until you use Export to Mapping. Manual links are saved
          directly and are trusted, but are not checked against SEAD.
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
import { computed } from 'vue'
import { reconciliationHelp } from './reconciliationHelp'
import { reconciliationWorkspaceTopic } from '@/help/helpRegistry'
import type { SelectionMode } from '@/types/reconciliation'

interface Props {
  modelValue: boolean
  /** When set, the dialog adds the review workspace topic for that mode. */
  workspaceMode?: SelectionMode | null
}

const props = withDefaults(defineProps<Props>(), { workspaceMode: null })

const workspaceTopic = computed(() => (props.workspaceMode ? reconciliationWorkspaceTopic(props.workspaceMode) : null))

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

.workspace-help-list {
  margin: 0.25rem 0 0;
  padding-left: 1.1rem;
}
</style>
