import { ref } from 'vue'
import type {
  FormattedError,
  LinkTroubleshootRequest,
  LinkTroubleshootResponse,
  LinkTroubleshootRowFilter,
} from '@/types'
import { linkTroubleshooterApi } from '@/api/linkTroubleshooter'
import { formatErrorMessage } from '@/utils/errors'

type LinkTroubleshootIdentity = Pick<LinkTroubleshootRequest, 'issue_type' | 'local_entity' | 'metadata'>

export function useLinkTroubleshooter(projectName: string) {
  const loading = ref(false)
  const error = ref<FormattedError | null>(null)
  const result = ref<LinkTroubleshootResponse | null>(null)
  const localKeys = ref<string[]>([])
  const remoteKeys = ref<string[]>([])
  const page = ref(1)
  const pageSize = ref(50)
  const rowFilter = ref<LinkTroubleshootRowFilter>('all')
  let identity: LinkTroubleshootIdentity | null = null
  let requestVersion = 0

  async function open(request: LinkTroubleshootRequest): Promise<LinkTroubleshootResponse | null> {
    identity = {
      issue_type: request.issue_type,
      local_entity: request.local_entity,
      metadata: request.metadata,
    }
    localKeys.value = []
    remoteKeys.value = []
    page.value = 1
    pageSize.value = 50
    rowFilter.value = 'all'
    return sendRequest(identity)
  }

  async function run(): Promise<LinkTroubleshootResponse | null> {
    if (!identity) {
      return null
    }

    return sendRequest({
      ...identity,
      local_keys: [...localKeys.value],
      remote_keys: [...remoteKeys.value],
      page: page.value,
      page_size: pageSize.value,
      row_filter: rowFilter.value,
    })
  }

  function reset(): void {
    requestVersion += 1
    loading.value = false
    error.value = null
    result.value = null
    localKeys.value = []
    remoteKeys.value = []
    page.value = 1
    pageSize.value = 50
    rowFilter.value = 'all'
    identity = null
  }

  async function sendRequest(request: LinkTroubleshootRequest): Promise<LinkTroubleshootResponse | null> {
    const version = ++requestVersion
    loading.value = true
    error.value = null
    result.value = null

    try {
      const response = await linkTroubleshooterApi.run(projectName, request)
      if (version !== requestVersion) {
        return null
      }

      result.value = response
      if (request.local_keys === undefined && request.remote_keys === undefined && response.configured_keys) {
        localKeys.value = [...response.configured_keys.local_keys]
        remoteKeys.value = [...response.configured_keys.remote_keys]
      }
      return response
    } catch (caughtError: unknown) {
      if (version === requestVersion) {
        error.value = formatErrorMessage(caughtError)
        result.value = null
        console.error('Link troubleshooter request failed:', caughtError)
      }
      return null
    } finally {
      if (version === requestVersion) {
        loading.value = false
      }
    }
  }

  return {
    loading,
    error,
    result,
    localKeys,
    remoteKeys,
    page,
    pageSize,
    rowFilter,
    open,
    run,
    reset,
  }
}
