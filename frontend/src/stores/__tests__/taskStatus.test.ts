import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import { useTaskStatusStore } from '../taskStatus'
import { TaskPriority, TaskStatus } from '@/composables/useTaskStatus'

vi.mock('@/composables/useTaskStatus', async () => {
  const actual = await vi.importActual<typeof import('@/composables/useTaskStatus')>('@/composables/useTaskStatus')

  return {
    ...actual,
    useTaskStatus: vi.fn(() => ({
      taskStatus: ref(null),
      loading: ref(false),
      error: ref<string | null>(null),
      fetchTaskStatus: vi.fn().mockResolvedValue(undefined),
      markComplete: vi.fn().mockResolvedValue(true),
      markIgnored: vi.fn().mockResolvedValue(true),
      markOngoing: vi.fn().mockResolvedValue(true),
      markTodo: vi.fn().mockResolvedValue(true),
      resetStatus: vi.fn().mockResolvedValue(true),
      toggleFlagged: vi.fn().mockResolvedValue(true),
    })),
  }
})

describe('useTaskStatusStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('updates local note presence without refreshing all task status', () => {
    const store = useTaskStatusStore()

    store.taskStatus = {
      project_name: 'demo',
      entities: {
        sample_entity: {
          entity_name: 'sample_entity',
          status: TaskStatus.TODO,
          priority: TaskPriority.READY,
          required: true,
          exists: true,
          validation_passed: true,
          preview_available: true,
          flagged: false,
          has_note: false,
          blocked_by: [],
          issues: [],
        },
      },
      completion_stats: {
        total: 1,
        done: 0,
        ongoing: 0,
        ignored: 0,
        todo: 1,
        flagged: 0,
        required_total: 1,
        required_done: 0,
        required_ongoing: 0,
        required_todo: 1,
        completion_percentage: 0,
      },
    }

    store.setEntityHasNote('sample_entity', true)
    expect(store.getEntityStatus('sample_entity')?.has_note).toBe(true)

    store.setEntityHasNote('sample_entity', false)
    expect(store.getEntityStatus('sample_entity')?.has_note).toBe(false)
  })

  it('ignores note updates for unknown entities', () => {
    const store = useTaskStatusStore()

    store.taskStatus = {
      project_name: 'demo',
      entities: {},
      completion_stats: {
        total: 0,
        done: 0,
        ongoing: 0,
        ignored: 0,
        todo: 0,
        flagged: 0,
        required_total: 0,
        required_done: 0,
        required_ongoing: 0,
        required_todo: 0,
        completion_percentage: 0,
      },
    }

    expect(() => store.setEntityHasNote('missing_entity', true)).not.toThrow()
    expect(store.getEntityStatus('missing_entity')).toBeUndefined()
  })
})