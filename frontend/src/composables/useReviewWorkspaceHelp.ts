/**
 * Shared state that tells the sidebar help panel when the review workspace is
 * open and which selection mode (search or browse) it is showing.
 *
 * The review workspace lives deep in the router tree, while the help panel
 * lives in the app navigation drawer, so the two share a small module-level
 * state instead of passing props through every layer.
 */

import { computed, readonly, ref } from 'vue'
import type { SelectionMode } from '@/types/reconciliation'

const activeCount = ref(0)
const activeMode = ref<SelectionMode>('search')

/**
 * Mark the review workspace as open and return a release function.
 *
 * The count keeps the help active while overlapping workspaces mount and
 * unmount, such as when the reviewer switches specifications.
 */
export function activateReviewWorkspaceHelp(mode: SelectionMode): () => void {
  activeCount.value += 1
  activeMode.value = mode
  let released = false
  return () => {
    if (released) return
    released = true
    activeCount.value = Math.max(0, activeCount.value - 1)
  }
}

/** Keep the sidebar help in step with the mode shown in the workspace. */
export function setReviewWorkspaceHelpMode(mode: SelectionMode): void {
  activeMode.value = mode
}

export function useReviewWorkspaceHelpState() {
  return {
    reviewWorkspaceHelpActive: computed(() => activeCount.value > 0),
    reviewWorkspaceHelpMode: readonly(activeMode),
  }
}
