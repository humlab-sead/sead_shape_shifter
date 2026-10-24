import { onScopeDispose, ref } from 'vue'
import { entitiesApi } from '@/api/entities'
import type {
  ColumnReferenceCompleteRequest,
  ColumnReferenceResolveResponse,
  ColumnReferenceResolveRequest,
} from '@/api/entities'

const REQUEST_DEBOUNCE_MS = 300

export interface ColumnReferenceContext {
  projectName: string
  entityName: string
  entityDraft: Record<string, unknown>
  editedFieldPath: string
  preferredEntity?: string
}

export function isSimpleColumnReference(value: string): boolean {
  return /^@value:\s*[A-Za-z0-9_-]+(?:[.:][A-Za-z0-9_-]+)*$/.test(value.trim())
}

function cloneEntityDraft(entityDraft: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(entityDraft)) as Record<string, unknown>
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

export function useColumnReferences() {
  const candidates = ref<string[]>([])
  const completionLoading = ref(false)
  const completionError = ref<string | null>(null)
  const inspection = ref<ColumnReferenceResolveResponse | null>(null)
  const inspectionDirective = ref<string | null>(null)
  const inspectionLoading = ref(false)
  const inspectionError = ref<string | null>(null)
  let completionVersion = 0
  let inspectionVersion = 0
  let completionTimer: ReturnType<typeof setTimeout> | null = null

  const fetchCandidates = async (
    version: number,
    projectName: string,
    entityName: string,
    request: ColumnReferenceCompleteRequest
  ): Promise<void> => {
    if (version !== completionVersion) return

    try {
      const result = await entitiesApi.completeColumnReferences(projectName, entityName, request)
      if (version === completionVersion) {
        candidates.value = result.candidates
      }
    } catch (error) {
      if (version === completionVersion) {
        completionError.value = getErrorMessage(error, 'Failed to load reference choices')
      }
    } finally {
      if (version === completionVersion) {
        completionLoading.value = false
      }
    }
  }

  function clearCompletion(): void {
    completionVersion += 1
    if (completionTimer !== null) {
      clearTimeout(completionTimer)
      completionTimer = null
    }
    candidates.value = []
    completionLoading.value = false
    completionError.value = null
  }

  function clearInspection(): void {
    inspectionVersion += 1
    inspection.value = null
    inspectionDirective.value = null
    inspectionLoading.value = false
    inspectionError.value = null
  }

  function scheduleCompletion(context: ColumnReferenceContext, prefix: string): void {
    clearCompletion()
    const version = completionVersion
    clearInspection()

    const normalizedPrefix = prefix.trim()
    if (!context.projectName || !context.entityName || !normalizedPrefix.startsWith('@value')) return

    completionLoading.value = true
    const request: ColumnReferenceCompleteRequest = {
      entity_draft: cloneEntityDraft(context.entityDraft),
      prefix: normalizedPrefix,
      edited_field_path: context.editedFieldPath,
      preferred_entity: context.preferredEntity,
    }
    completionTimer = setTimeout(() => {
      completionTimer = null
      void fetchCandidates(version, context.projectName, context.entityName, request)
    }, REQUEST_DEBOUNCE_MS)
  }

  async function resolveReference(context: ColumnReferenceContext, directive: string): Promise<void> {
    const version = ++inspectionVersion
    inspection.value = null
    inspectionDirective.value = directive
    inspectionLoading.value = false
    inspectionError.value = null

    if (!context.projectName || !context.entityName || !isSimpleColumnReference(directive)) return

    inspectionLoading.value = true
    const request: ColumnReferenceResolveRequest = {
      entity_draft: cloneEntityDraft(context.entityDraft),
      directive,
    }

    try {
      const result = await entitiesApi.resolveColumnReference(context.projectName, context.entityName, request)
      if (version === inspectionVersion) {
        inspection.value = result
      }
    } catch (error) {
      if (version === inspectionVersion) {
        inspectionError.value = getErrorMessage(error, 'Failed to inspect this reference')
      }
    } finally {
      if (version === inspectionVersion) {
        inspectionLoading.value = false
      }
    }
  }

  function clear(): void {
    clearCompletion()
    clearInspection()
  }

  onScopeDispose(clear)

  return {
    candidates,
    completionLoading,
    completionError,
    inspection,
    inspectionDirective,
    inspectionLoading,
    inspectionError,
    scheduleCompletion,
    resolveReference,
    clearCompletion,
    clearInspection,
    clear,
  }
}
