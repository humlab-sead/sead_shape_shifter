/**
 * Which deployment-wide features the current user may use.
 *
 * The UI uses this to hide features. The backend checks authorization on every protected request.
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import { permissionsApi } from '@/api/permissions'

export const usePermissionsStore = defineStore('permissions', () => {
  const canReadLogs = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadPermissions() {
    loading.value = true
    error.value = null
    try {
      const permissions = await permissionsApi.getMyPermissions()
      canReadLogs.value = permissions.can_read_logs
    } catch (err) {
      canReadLogs.value = false
      error.value = err instanceof Error ? err.message : 'Failed to load permissions'
    } finally {
      loading.value = false
    }
  }

  return { canReadLogs, loading, error, loadPermissions }
})
