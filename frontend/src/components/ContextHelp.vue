<template>
  <div v-if="!rail" class="context-help">
    <v-expansion-panels variant="accordion" :model-value="expanded ? [0] : []">
      <v-expansion-panel>
        <v-expansion-panel-title @click="toggleExpanded">
          <div class="d-flex align-center">
            <v-icon size="small" class="mr-2">mdi-help-circle-outline</v-icon>
            <span class="text-body-2 font-weight-medium">Context Help</span>
          </div>
        </v-expansion-panel-title>

        <v-expansion-panel-text>
          <div v-if="helpContent" class="help-content">
            <div v-if="helpContent.title" class="text-subtitle-2 font-weight-bold mb-2">
              {{ helpContent.title }}
            </div>

            <div v-if="helpContent.description" class="text-caption mb-3">
              {{ helpContent.description }}
            </div>

            <div
              v-if="workspaceStatusVisible"
              class="workspace-status mt-3"
              data-testid="context-help-workspace-status"
            >
              <div class="text-caption font-weight-medium mb-1 text-medium-emphasis">Workspace status</div>
              <div
                v-if="reviewWorkspaceNotices.storageError"
                class="help-notice help-notice--warning"
                data-testid="context-help-storage-warning"
              >
                {{ reviewWorkspaceNotices.storageError }}
              </div>
              <div
                v-if="reviewWorkspaceNotices.restoreNotice"
                class="help-notice help-notice--info"
                data-testid="context-help-restore-notice"
              >
                <span>{{ reviewWorkspaceNotices.restoreNotice }}</span>
                <button
                  type="button"
                  class="help-notice-dismiss"
                  data-testid="context-help-restore-dismiss"
                  @click="dismissReviewWorkspaceRestoreNotice"
                >
                  Dismiss
                </button>
              </div>
            </div>

            <div v-if="helpContent.groups && helpContent.groups.length > 0" class="groups-section mt-3">
              <div v-for="group in helpContent.groups" :key="group.title" class="help-group">
                <div class="text-caption font-weight-medium mb-1 text-medium-emphasis">{{ group.title }}</div>
                <div v-for="(tip, index) in group.tips" :key="index" class="tip-item">
                  <span class="tip-bullet">•</span>
                  <span class="tip-text" v-html="tip" />
                </div>
              </div>
            </div>

            <div v-if="helpContent.tips && helpContent.tips.length > 0" class="tips-section mt-3">
              <div class="text-caption font-weight-medium mb-1 text-medium-emphasis">Tips</div>
              <div v-for="(tip, index) in helpContent.tips" :key="index" class="tip-item">
                <span class="tip-bullet">•</span>
                <span class="tip-text" v-html="tip" />
              </div>
            </div>

            <div v-if="helpContent.rowActions?.length" class="row-actions-section mt-3">
              <div class="text-caption font-weight-medium mb-1 text-medium-emphasis">Row action icons</div>
              <div v-for="action in helpContent.rowActions" :key="action.label" class="row-action-item">
                <v-icon
                  v-if="action.icon"
                  :icon="action.icon"
                  size="small"
                  class="row-action-icon"
                  aria-hidden="true"
                />
                <div>
                  <div class="font-weight-medium">{{ action.label }}</div>
                  <div class="text-caption">{{ action.description }}</div>
                </div>
              </div>
            </div>

            <div v-if="helpContent.shortcuts && helpContent.shortcuts.length > 0" class="shortcuts-section mt-3">
              <div class="text-caption font-weight-medium mb-1 text-medium-emphasis">Shortcuts</div>
              <div v-for="(shortcut, index) in helpContent.shortcuts" :key="index" class="shortcut-item">
                <div class="shortcut-keys">{{ shortcut.keys }}</div>
                <div class="shortcut-action">{{ shortcut.action }}</div>
              </div>
            </div>
          </div>

          <div v-else class="text-caption text-grey">No help available for this view.</div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { dismissReviewWorkspaceRestoreNotice, useReviewWorkspaceHelpState } from '@/composables/useReviewWorkspaceHelp'
import { resolveHelpTopic } from '@/help/helpRegistry'

interface Props {
  rail?: boolean
}

defineProps<Props>()

const route = useRoute()
const { reviewWorkspaceHelpActive, reviewWorkspaceHelpMode, reviewWorkspaceNotices } = useReviewWorkspaceHelpState()

/** Show the status block only while the workspace is open and has something to report. */
const workspaceStatusVisible = computed(
  () =>
    reviewWorkspaceHelpActive.value &&
    Boolean(reviewWorkspaceNotices.value.storageError || reviewWorkspaceNotices.value.restoreNotice)
)

/** Browser key that remembers whether the reviewer keeps the panel open. */
const HELP_EXPANDED_STORAGE_KEY = 'shapeshifter.contextHelp.expanded'

function readStoredExpanded(): boolean {
  try {
    const stored = globalThis.localStorage?.getItem(HELP_EXPANDED_STORAGE_KEY)
    return stored === null || stored === undefined ? true : stored === 'true'
  } catch {
    return true
  }
}

function storeExpanded(value: boolean): void {
  try {
    globalThis.localStorage?.setItem(HELP_EXPANDED_STORAGE_KEY, String(value))
  } catch {
    // Blocked storage keeps the panel usable for this session only.
  }
}

const expanded = ref(readStoredExpanded() || reviewWorkspaceHelpActive.value)

function toggleExpanded() {
  expanded.value = !expanded.value
  storeExpanded(expanded.value)
}

watch(reviewWorkspaceHelpActive, (active) => {
  // Opening the workspace is when workspace help matters most.
  if (active) expanded.value = true
})

const helpContent = computed(() =>
  resolveHelpTopic({
    routeName: route.name as string,
    tab: typeof route.query.tab === 'string' ? route.query.tab : null,
    workspaceActive: reviewWorkspaceHelpActive.value,
    workspaceMode: reviewWorkspaceHelpMode.value,
  })
)
</script>

<style scoped>
.context-help {
  margin: 0.5rem;
}

.help-content {
  font-size: 0.8125rem;
  line-height: 1.4;
}

.tips-section,
.shortcuts-section,
.row-actions-section {
  margin-top: 0.75rem;
}

.help-group + .help-group {
  margin-top: 0.75rem;
}

.help-notice {
  margin-bottom: 0.375rem;
  padding: 0.375rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  line-height: 1.3;
}

.help-notice--info {
  background: rgba(var(--v-theme-info), 0.12);
}

.help-notice--warning {
  background: rgba(var(--v-theme-warning), 0.16);
}

.help-notice-dismiss {
  display: block;
  margin-top: 0.25rem;
  padding: 0;
  border: none;
  background: none;
  color: rgb(var(--v-theme-primary));
  font-size: 0.6875rem;
  cursor: pointer;
  text-decoration: underline;
}

.row-action-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  line-height: 1.3;
}

.row-action-icon {
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.tip-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 0.375rem;
  font-size: 0.75rem;
  line-height: 1.3;
}

.tip-bullet {
  color: rgb(var(--v-theme-primary));
  margin-right: 0.375rem;
  flex-shrink: 0;
  font-weight: bold;
}

.tip-text {
  flex: 1;
  word-wrap: break-word;
  overflow-wrap: break-word;
  hyphens: auto;
}

.shortcut-item {
  display: flex;
  flex-direction: column;
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  line-height: 1.3;
}

.shortcut-keys {
  font-weight: 600;
  color: rgb(var(--v-theme-secondary));
  font-family: 'Courier New', monospace;
  font-size: 0.6875rem;
  margin-bottom: 0.125rem;
}

.shortcut-action {
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.8;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
</style>
