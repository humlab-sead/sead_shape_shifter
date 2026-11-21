import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { nextTick, reactive, toRefs } from 'vue'
import type {
  DecisionBatchIssue,
  DecisionState,
  ReconciliationPreviewRow,
  SelectionCapabilities,
  SelectionRecord,
  SelectionSearchResult,
  WorkspaceDraft,
  WorkspaceDraftStatus,
} from '@/types/reconciliation'

import ReconciliationWorkspace from '../ReconciliationWorkspace.vue'

vi.mock('pinia', async () => {
  const actual = await vi.importActual<typeof import('pinia')>('pinia')

  return {
    ...actual,
    storeToRefs: (store: object) => toRefs(store),
  }
})

const capabilities: SelectionCapabilities = {
  version: 1,
  type: {
    type: 'feature_type',
    search_supported: true,
    identifier_search_supported: true,
    browse_supported: true,
    details_supported: true,
    export_verification_supported: false,
    id_base: 'https://w3id.org/sead/id/',
    id_path: 'feature_type',
    browse_max_rows: 500,
    browse_max_bytes: 1048576,
    interactive_search_max_results: 25,
    display_fields: [
      { name: 'name', source: 'record', label: 'Name', value_type: 'string', display: true },
      { name: 'target_id', source: 'record', label: 'ID', value_type: 'integer', display: true },
    ],
    text_filter_fields: ['name'],
    sort_fields: ['name', 'target_id'],
    field_filters: [
      { field: 'name', operator: 'contains_ci' },
      { field: 'target_id', operator: 'equals' },
    ],
  },
}

const reconciliationStore = reactive({
  loadSelectionCapabilities: vi.fn(async () => capabilities),
  searchSelection: vi.fn(
    async (): Promise<SelectionSearchResult> => ({ mode: 'ranked', items: [record(101, 'Bronze Age')] })
  ),
  browseSelection: vi.fn(async () => ({ items: [] as SelectionRecord[], completeness: 'complete' as const })),
  fetchSavedDecisionStates: vi.fn(async (): Promise<Record<string, DecisionState>> => ({})),
  decisionStatesFromPreview: vi.fn((rows: ReconciliationPreviewRow[]) => {
    const states: Record<string, unknown> = {}
    for (const row of rows) {
      if (!row.local_key_value || row.status === null || row.status === undefined) continue
      states[row.local_key_value] = {
        status: row.status,
        target_id: row.target_id ?? null,
        candidate_id: row.candidate_id ?? null,
        notes: row.notes ?? null,
      }
    }
    return states
  }),
  changedDecisionKeys: vi.fn(() => [] as string[]),
  saveDecisionBatch: vi.fn(),
  getDecisionBatchIssues: vi.fn((): DecisionBatchIssue[] => []),
  loadWorkspaceDraft: vi.fn(
    (
      _projectName: string,
      _entityName: string,
      _targetField: string
    ): { status: WorkspaceDraftStatus; draft: WorkspaceDraft | null } => ({ status: 'empty', draft: null })
  ),
  saveWorkspaceDraft: vi.fn(
    (_projectName: string, _entityName: string, _targetField: string, _draft: WorkspaceDraft) => true
  ),
  clearWorkspaceDraft: vi.fn(),
})

vi.mock('@/stores/reconciliation', () => ({
  useReconciliationStore: () => reconciliationStore,
}))

const vuetify = createVuetify({ components, directives })

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock)

function record(targetId: number, name: string, fields: Record<string, unknown> = {}): SelectionRecord {
  return {
    id: `https://w3id.org/sead/id/feature_type/${targetId}`,
    target_id: targetId,
    type: 'feature_type',
    name,
    fields,
    score: null,
  }
}

function previewRows(count = 10): ReconciliationPreviewRow[] {
  return Array.from({ length: count }, (_, index) => ({
    local_key_value: `K${index + 1}`,
    site_name: `Label ${index + 1}`,
    status: null,
    errors: [],
  }))
}

function batchResult(keys: string[]) {
  return {
    saved: keys.map((key) => ({
      local_key_value: key,
      status: 'accepted' as const,
      target_id: 101,
      candidate_id: 'https://w3id.org/sead/id/feature_type/101',
      notes: null,
      last_modified: '2026-11-20T00:00:00Z',
    })),
    counts: {
      saved: keys.length,
      accepted: keys.length,
      local_only: 0,
      specification: { accepted: keys.length, local_only: 0, proposed: 0, rejected: 0, total: keys.length },
    },
  }
}

interface MountOptions {
  rows?: ReconciliationPreviewRow[]
  descriptor?: { version: number; typesPath: string } | null
  attachTo?: Element
  projectName?: string
}

/** Vuetify dialogs teleport to the document body, so read them from there. */
function dialogElement(testId: string): HTMLElement | null {
  return document.body.querySelector<HTMLElement>(`[data-testid="${testId}"]`)
}

function clickDialog(testId: string) {
  dialogElement(testId)?.click()
}

/** Wait for Vuetify overlay activation, which schedules work outside microtasks. */
async function settleOverlay() {
  await flushPromises()
  await new Promise((resolve) => setTimeout(resolve, 80))
  await nextTick()
  await flushPromises()
}

async function mountWorkspace(options: MountOptions = {}) {
  const wrapper = mount(ReconciliationWorkspace, {
    global: {
      plugins: [vuetify],
    },
    ...(options.attachTo ? { attachTo: options.attachTo } : {}),
    props: {
      projectName: options.projectName ?? 'project',
      entityName: 'site',
      targetField: 'site_name',
      serviceType: 'feature_type',
      previewRows: options.rows ?? previewRows(),
      selectionDescriptor:
        options.descriptor === undefined ? { version: 1, typesPath: '/records/types' } : options.descriptor,
    },
  })

  await nextTick()
  await flushPromises()
  return wrapper
}

async function searchAndSelect(wrapper: Awaited<ReturnType<typeof mountWorkspace>>, query = 'bronze') {
  const input = wrapper.find('[data-testid="workspace-search-input"] input')
  await input.setValue(query)
  await input.trigger('keydown', { key: 'Enter' })
  await flushPromises()
  await wrapper.find('[data-testid="workspace-result-101"]').trigger('click')
}

describe('ReconciliationWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.querySelectorAll('.v-overlay-container').forEach((element) => element.remove())
    reconciliationStore.loadSelectionCapabilities.mockImplementation(async () => capabilities)
    reconciliationStore.searchSelection.mockImplementation(async () => ({
      mode: 'ranked' as const,
      items: [record(101, 'Bronze Age')],
    }))
    reconciliationStore.browseSelection.mockImplementation(async () => ({
      items: [],
      completeness: 'complete' as const,
    }))
    reconciliationStore.fetchSavedDecisionStates.mockImplementation(async () => ({}))
    reconciliationStore.changedDecisionKeys.mockImplementation(() => [])
    reconciliationStore.getDecisionBatchIssues.mockImplementation(() => [])
    reconciliationStore.loadWorkspaceDraft.mockImplementation(() => ({ status: 'empty' as const, draft: null }))
    reconciliationStore.saveWorkspaceDraft.mockImplementation(() => true)
  })

  it('reviews ten rows without candidate matching and saves them in one batch', async () => {
    reconciliationStore.saveDecisionBatch.mockImplementation(async (_project, _entity, _field, drafts) =>
      batchResult(drafts.map((draft: { local_key_value: string }) => draft.local_key_value))
    )
    const wrapper = await mountWorkspace()

    expect(reconciliationStore.loadSelectionCapabilities).toHaveBeenCalledWith('project', 'site', 'site_name')
    expect(wrapper.find('[data-testid="workspace-queue-count"]').text()).toBe('10')

    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    await nextTick()

    for (let index = 0; index < 10; index += 1) {
      await searchAndSelect(wrapper)
      await wrapper.find('[data-testid="workspace-stage-next"]').trigger('click')
      await nextTick()
    }

    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('10')
    await wrapper.find('[data-testid="workspace-save"]').trigger('click')
    await flushPromises()

    expect(reconciliationStore.saveDecisionBatch).toHaveBeenCalledTimes(1)
    const drafts = reconciliationStore.saveDecisionBatch.mock.calls[0]![3]
    expect(drafts).toHaveLength(10)
    expect(drafts[0]).toEqual({
      local_key_value: 'K1',
      displayed_values: { site_name: 'Label 1' },
      status: 'accepted',
      target_id: 101,
      candidate_id: 'https://w3id.org/sead/id/feature_type/101',
      notes: null,
    })
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('0')
    expect(wrapper.find('[data-testid="workspace-save-summary"]').exists()).toBe(true)
  })

  it('stages, skips, and moves rows with labelled controls and modified shortcuts', async () => {
    const wrapper = await mountWorkspace({ rows: previewRows(3) })

    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    expect(wrapper.find('[data-testid="workspace-stage-next"]').attributes('disabled')).toBeDefined()

    await searchAndSelect(wrapper)
    await wrapper.find('[data-testid="workspace-stage-next"]').trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('key: K2')

    await wrapper.find('[data-testid="workspace-skip"]').trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('key: K3')

    await wrapper.find('[data-testid="workspace-previous"]').trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('key: K2')

    const root = wrapper.find('[data-testid="reconciliation-workspace"]')
    await root.trigger('keydown', { key: 'ArrowRight', altKey: true })
    await nextTick()
    expect(wrapper.text()).toContain('key: K3')

    // Bare keys never stage a decision.
    await root.trigger('keydown', { key: 'n' })
    await nextTick()
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('1')
  })

  it('moves visible focus with the active row during keyboard navigation', async () => {
    const wrapper = await mountWorkspace({ rows: previewRows(3), attachTo: document.body })
    try {
      const firstRow = wrapper.find<HTMLElement>('[data-testid="workspace-row-0"]')
      await firstRow.trigger('click')
      await nextTick()
      expect(document.activeElement).toBe(firstRow.element)

      await wrapper
        .find('[data-testid="reconciliation-workspace"]')
        .trigger('keydown', { key: 'ArrowRight', altKey: true })
      await nextTick()

      const secondRow = wrapper.find<HTMLElement>('[data-testid="workspace-row-1"]')
      expect(wrapper.text()).toContain('key: K2')
      expect(document.activeElement).toBe(secondRow.element)
    } finally {
      wrapper.unmount()
    }
  })

  it('stages the selected result with Alt+Enter from search and result focus', async () => {
    const wrapper = await mountWorkspace({ rows: previewRows(3) })
    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    await searchAndSelect(wrapper)

    const searchInput = wrapper.find('[data-testid="workspace-search-input"] input')
    await searchInput.trigger('keydown', { key: 'Enter', altKey: true })
    await flushPromises()

    expect(reconciliationStore.searchSelection).toHaveBeenCalledTimes(1)
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('1')
    expect(wrapper.text()).toContain('key: K2')

    await searchAndSelect(wrapper)
    await wrapper.find('[data-testid="workspace-result-101"]').trigger('keydown', { key: 'Enter', altKey: true })
    await nextTick()

    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('2')
    expect(wrapper.text()).toContain('key: K3')
  })

  it('ignores composition input and never stages from a bare letter', async () => {
    const wrapper = await mountWorkspace({ rows: previewRows(2) })
    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    await searchAndSelect(wrapper)

    const root = wrapper.find('[data-testid="reconciliation-workspace"]')
    await root.trigger('keydown', { key: 'Enter', altKey: true, isComposing: true })
    await nextTick()
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('0')
  })

  it('debounces typeahead and submits immediately on Enter without a duplicate request', async () => {
    const wrapper = await mountWorkspace({ rows: previewRows(2) })
    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    const input = wrapper.find('[data-testid="workspace-search-input"] input')

    vi.useFakeTimers()
    try {
      await input.setValue('bro')
      await vi.advanceTimersByTimeAsync(299)
      expect(reconciliationStore.searchSelection).not.toHaveBeenCalled()

      await vi.advanceTimersByTimeAsync(1)
      expect(reconciliationStore.searchSelection).toHaveBeenCalledTimes(1)

      await input.setValue('bronze')
      await input.trigger('keydown', { key: 'Enter' })
      await vi.advanceTimersByTimeAsync(400)
      expect(reconciliationStore.searchSelection).toHaveBeenCalledTimes(2)
    } finally {
      vi.useRealTimers()
    }
  })

  it('discards a stale success and a stale failure from an earlier request', async () => {
    const wrapper = await mountWorkspace({ rows: previewRows(2) })
    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    const input = wrapper.find('[data-testid="workspace-search-input"] input')

    let resolveFirst: ((value: SelectionSearchResult) => void) | undefined
    reconciliationStore.searchSelection
      .mockImplementationOnce(() => new Promise<SelectionSearchResult>((resolve) => (resolveFirst = resolve)))
      .mockImplementationOnce(async () => ({ mode: 'ranked' as const, items: [record(202, 'Iron Age')] }))

    await input.setValue('bron')
    await input.trigger('keydown', { key: 'Enter' })
    await input.setValue('bronze')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(wrapper.find('[data-testid="workspace-result-202"]').exists()).toBe(true)

    resolveFirst?.({ mode: 'ranked', items: [record(101, 'Bronze Age')] })
    await flushPromises()
    expect(wrapper.find('[data-testid="workspace-result-202"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="workspace-result-101"]').exists()).toBe(false)

    // A late failure must not replace current results either.
    let rejectFirst: ((reason: unknown) => void) | undefined
    reconciliationStore.searchSelection
      .mockImplementationOnce(() => new Promise<SelectionSearchResult>((_resolve, reject) => (rejectFirst = reject)))
      .mockImplementationOnce(async () => ({ mode: 'ranked' as const, items: [record(303, 'Medieval')] }))
    await input.setValue('m')
    await input.trigger('keydown', { key: 'Enter' })
    await input.setValue('me')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    rejectFirst?.(new Error('late failure'))
    await flushPromises()

    expect(wrapper.find('[data-testid="workspace-search-error"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="workspace-result-303"]').exists()).toBe(true)
  })

  it('shows the validation message for malformed ids and distinguishes unknown ids', async () => {
    const wrapper = await mountWorkspace({ rows: previewRows(2) })
    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    const input = wrapper.find('[data-testid="workspace-search-input"] input')

    const invalidInputError = Object.assign(new Error('Request failed with status code 400'), {
      response: {
        data: { detail: { error_code: 'RECORD_SELECTION_INVALID_INPUT', message: 'Enter a whole number.' } },
      },
    })
    reconciliationStore.searchSelection.mockRejectedValueOnce(invalidInputError)
    await input.setValue('id: abc')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    const invalidMessage = wrapper.find('[data-testid="workspace-search-invalid"]')
    expect(invalidMessage.exists()).toBe(true)
    expect(invalidMessage.text()).toContain('Enter a whole number.')
    expect(invalidMessage.text()).not.toContain('Request failed with status code 400')
    expect(wrapper.find('[data-testid="workspace-search-error"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="workspace-search-results"]').exists()).toBe(false)

    reconciliationStore.searchSelection.mockResolvedValueOnce({ mode: 'exact', items: [] })
    await input.setValue('id: 987654')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(wrapper.find('[data-testid="workspace-search-empty"]').exists()).toBe(true)
    // A miss never stages a New decision on its own.
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('0')
  })

  it('filters and sorts the complete browse list locally with literal characters', async () => {
    reconciliationStore.browseSelection.mockResolvedValueOnce({
      completeness: 'complete',
      items: [record(3, '100% Bronze'), record(1, 'Iron_Age'), record(2, 'Iron_Age'), record(4, 'Late Bronze')],
    })
    const wrapper = await mountWorkspace({ rows: previewRows(2) })
    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')

    const browseButton = wrapper.findAll('button').find((button) => button.text() === 'Browse')
    await browseButton?.trigger('click')
    await flushPromises()

    expect(reconciliationStore.browseSelection).toHaveBeenCalledTimes(1)
    const sortedIds = wrapper
      .findAll('[data-testid="workspace-browse-results"] [data-testid^="workspace-result-"]')
      .map((item) => item.attributes('data-testid'))
    // Label ascending, numeric target ID as the tie-breaker.
    expect(sortedIds).toEqual(['workspace-result-3', 'workspace-result-1', 'workspace-result-2', 'workspace-result-4'])

    const filter = wrapper.find('[data-testid="workspace-browse-filter"] input')
    await filter.setValue('%')
    await nextTick()
    expect(wrapper.find('[data-testid="workspace-browse-results"]').text()).toContain('100% Bronze')
    expect(wrapper.find('[data-testid="workspace-browse-results"]').text()).not.toContain('Late Bronze')

    await filter.setValue('_')
    await nextTick()
    expect(wrapper.findAll('[data-testid^="workspace-result-"]')).toHaveLength(2)

    await filter.setValue('')
    await nextTick()
    expect(wrapper.find('[data-testid="workspace-browse-summary"]').text()).toContain('4 of 4')
  })

  it('clears a selected record when it is hidden by the active browse filter', async () => {
    reconciliationStore.browseSelection.mockResolvedValueOnce({
      completeness: 'complete',
      items: [record(101, 'Bronze Age'), record(102, 'Iron Age')],
    })
    const wrapper = await mountWorkspace({ rows: previewRows(2) })
    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')

    const modeButtons = wrapper.find('[data-testid="workspace-mode-toggle"]')
    await modeButtons
      .findAll('button')
      .find((button) => button.text() === 'Browse')
      ?.trigger('click')
    await flushPromises()

    const filter = wrapper.find('[data-testid="workspace-browse-filter"] input')
    await filter.setValue('Iron')
    await nextTick()

    await modeButtons
      .findAll('button')
      .find((button) => button.text() === 'Search')
      ?.trigger('click')
    const searchInput = wrapper.find('[data-testid="workspace-search-input"] input')
    await searchInput.setValue('bronze')
    await searchInput.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    await wrapper.find('[data-testid="workspace-result-101"]').trigger('click')

    expect(wrapper.find('[data-testid="workspace-stage-next"]').attributes('disabled')).toBeUndefined()

    await modeButtons
      .findAll('button')
      .find((button) => button.text() === 'Browse')
      ?.trigger('click')
    await nextTick()
    expect(wrapper.find('[data-testid="workspace-stage-next"]').attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="workspace-result-102"]').trigger('click')
    expect(wrapper.find('[data-testid="workspace-stage-next"]').attributes('disabled')).toBeUndefined()

    const activeFilter = wrapper.find('[data-testid="workspace-browse-filter"] input')
    await activeFilter.setValue('Bronze')
    await nextTick()
    expect(wrapper.find('[data-testid="workspace-stage-next"]').attributes('disabled')).toBeDefined()
  })

  it('reports a too-large browse list without showing partial items', async () => {
    reconciliationStore.browseSelection.mockRejectedValueOnce({
      response: { data: { detail: { error_code: 'RECORD_SELECTION_TOO_LARGE', message: 'too large' } } },
    })
    const wrapper = await mountWorkspace({ rows: previewRows(2) })
    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')

    const browseButton = wrapper.findAll('button').find((button) => button.text() === 'Browse')
    await browseButton?.trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="workspace-browse-too-large"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="workspace-browse-results"]').exists()).toBe(false)
  })

  it('keeps every draft when the batch is rejected', async () => {
    reconciliationStore.saveDecisionBatch.mockRejectedValueOnce({
      response: { data: { detail: { message: 'The decision batch was rejected', issues: [] } } },
    })
    reconciliationStore.getDecisionBatchIssues.mockReturnValueOnce([
      { local_key_value: 'K1', code: 'row_changed', message: 'Column changed since it was displayed.' },
    ])
    const wrapper = await mountWorkspace({ rows: previewRows(2) })

    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    await searchAndSelect(wrapper, 'bronze')
    await wrapper.find('[data-testid="workspace-stage-next"]').trigger('click')
    await nextTick()

    await wrapper.find('[data-testid="workspace-save"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="workspace-save-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="workspace-save-issues"]').text()).toContain('K1')
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('1')
  })

  it('warns before replacing a changed decision and saves once only after confirmation', async () => {
    reconciliationStore.changedDecisionKeys.mockImplementation(() => ['K1'])
    reconciliationStore.fetchSavedDecisionStates.mockResolvedValue({
      K1: { status: 'accepted', target_id: 55, candidate_id: 'id/55', notes: null },
    })
    reconciliationStore.saveDecisionBatch.mockImplementation(async (_project, _entity, _field, drafts) =>
      batchResult(drafts.map((draft: { local_key_value: string }) => draft.local_key_value))
    )

    const rows = previewRows(2)
    rows[0]!.status = 'accepted'
    rows[0]!.target_id = 44
    // A saved row is back in Needs review only while it carries an unsaved draft.
    reconciliationStore.loadWorkspaceDraft.mockImplementation(() => ({
      status: 'restored' as const,
      draft: {
        focusedKey: 'K1',
        mode: 'search' as const,
        searchQuery: '',
        browseText: '',
        browseFieldFilters: {},
        sortField: 'name',
        sortDirection: 'asc' as const,
        rows: {
          K1: {
            query: '',
            notes: '',
            decision: {
              status: 'accepted' as const,
              id: 'https://w3id.org/sead/id/feature_type/99',
              target_id: 99,
              name: 'Restaged target',
            },
            displayedValues: { site_name: 'Label 1' },
          },
        },
      },
    }))
    const wrapper = await mountWorkspace({ rows })

    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('1')

    await wrapper.find('[data-testid="workspace-save"]').trigger('click')
    await settleOverlay()

    expect(reconciliationStore.changedDecisionKeys).toHaveBeenCalledWith(expect.anything(), expect.anything(), ['K1'])
    const dialog = wrapper.findComponent({ name: 'VDialog' })
    expect(dialog.props('modelValue')).toBe(true)
    expect(document.body.textContent).toContain('K1')
    expect(reconciliationStore.saveDecisionBatch).not.toHaveBeenCalled()

    clickDialog('workspace-conflict-cancel')
    await settleOverlay()
    expect(dialog.props('modelValue')).toBe(false)
    expect(reconciliationStore.saveDecisionBatch).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('1')

    await wrapper.find('[data-testid="workspace-save"]').trigger('click')
    await settleOverlay()
    expect(dialog.props('modelValue')).toBe(true)
    clickDialog('workspace-conflict-confirm')
    await flushPromises()

    expect(reconciliationStore.saveDecisionBatch).toHaveBeenCalledTimes(1)
  })

  it('does not warn when an unrelated decision changed', async () => {
    reconciliationStore.changedDecisionKeys.mockImplementation(() => [])
    reconciliationStore.saveDecisionBatch.mockImplementation(async (_project, _entity, _field, drafts) =>
      batchResult(drafts.map((draft: { local_key_value: string }) => draft.local_key_value))
    )
    const wrapper = await mountWorkspace({ rows: previewRows(2) })

    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    await searchAndSelect(wrapper, 'bronze')
    await wrapper.find('[data-testid="workspace-stage-next"]').trigger('click')
    await nextTick()

    await wrapper.find('[data-testid="workspace-save"]').trigger('click')
    await flushPromises()

    expect(wrapper.findComponent({ name: 'VDialog' }).props('modelValue')).toBe(false)
    expect(reconciliationStore.saveDecisionBatch).toHaveBeenCalledTimes(1)
  })

  it('does not save when the pre-save comparison cannot be read', async () => {
    reconciliationStore.fetchSavedDecisionStates.mockRejectedValueOnce(new Error('catalog unavailable'))
    const wrapper = await mountWorkspace({ rows: previewRows(2) })

    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    await searchAndSelect(wrapper, 'bronze')
    await wrapper.find('[data-testid="workspace-stage-next"]').trigger('click')
    await nextTick()

    await wrapper.find('[data-testid="workspace-save"]').trigger('click')
    await flushPromises()

    expect(reconciliationStore.saveDecisionBatch).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="workspace-save-error"]').text()).toContain('catalog unavailable')
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('1')
  })

  it('restores only scoped unsaved drafts, not a selection or result list', async () => {
    const restored: WorkspaceDraft = {
      focusedKey: 'K2',
      mode: 'search',
      searchQuery: 'bronze',
      browseText: '',
      browseFieldFilters: {},
      sortField: 'name',
      sortDirection: 'asc',
      rows: {
        K2: {
          query: 'bronze',
          notes: 'same label',
          decision: { status: 'local-only' },
          displayedValues: { site_name: 'Label 2' },
        },
      },
    }
    reconciliationStore.loadWorkspaceDraft.mockImplementation(() => ({ status: 'restored' as const, draft: restored }))
    const wrapper = await mountWorkspace({ rows: previewRows(3) })

    expect(wrapper.find('[data-testid="workspace-restore-notice"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('1')
    expect(wrapper.text()).toContain('key: K2')
    expect(wrapper.find('[data-testid="workspace-search-results"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="workspace-selection"]').text()).toContain('Staged New')
  })

  it('restores focus to an unstaged row while preserving drafts on other rows', async () => {
    const restored: WorkspaceDraft = {
      focusedKey: 'K3',
      mode: 'search',
      searchQuery: '',
      browseText: '',
      browseFieldFilters: {},
      sortField: 'name',
      sortDirection: 'asc',
      rows: {
        K2: {
          query: '',
          notes: '',
          decision: { status: 'local-only' },
          displayedValues: { site_name: 'Label 2' },
        },
      },
    }
    reconciliationStore.loadWorkspaceDraft.mockImplementation(() => ({ status: 'restored' as const, draft: restored }))
    const wrapper = await mountWorkspace({ rows: previewRows(3) })

    expect(wrapper.find('[data-testid="workspace-no-active-row"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('key: K3')
    expect(wrapper.find('[data-testid="workspace-row-2"]').classes()).toContain('v-list-item--active')
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('1')
  })

  it('reports an unreadable draft instead of applying it', async () => {
    reconciliationStore.loadWorkspaceDraft.mockImplementation(() => ({ status: 'invalid' as const, draft: null }))
    const wrapper = await mountWorkspace({ rows: previewRows(2) })

    expect(wrapper.find('[data-testid="workspace-restore-notice"]').text()).toContain('could not be read')
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('0')
  })

  it('reports when the browser cannot persist a draft', async () => {
    reconciliationStore.saveWorkspaceDraft.mockImplementation(() => false)
    const wrapper = await mountWorkspace({ rows: previewRows(2) })

    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    await nextTick()

    expect(wrapper.find('[data-testid="workspace-storage-warning"]').exists()).toBe(true)
  })

  it('falls back to the legacy grid when the service publishes no selection extension', async () => {
    const wrapper = await mountWorkspace({ descriptor: null })

    expect(reconciliationStore.loadSelectionCapabilities).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="workspace-fallback"]').exists()).toBe(true)

    await wrapper.find('[data-testid="workspace-use-legacy"]').trigger('click')
    expect(wrapper.emitted('fallback')).toHaveLength(1)
  })

  it('falls back when capability discovery fails', async () => {
    reconciliationStore.loadSelectionCapabilities.mockRejectedValueOnce({
      response: {
        data: { detail: { error_code: 'RECORD_SELECTION_UNAVAILABLE', message: 'The service is offline.' } },
      },
    })
    const wrapper = await mountWorkspace()

    expect(wrapper.find('[data-testid="workspace-fallback"]').text()).toContain('The service is offline.')
    expect(wrapper.find('[data-testid="workspace-use-legacy"]').exists()).toBe(true)
  })

  it('does not offer reviewable actions for rows without a business key', async () => {
    const rows = previewRows(2)
    rows[1] = { ...rows[1], local_key_value: null }
    const wrapper = await mountWorkspace({ rows })

    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    await wrapper.find('[data-testid="workspace-skip"]').trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('No business key')
    expect(wrapper.text()).toContain('key: K1')
  })
})

/**
 * VM-9 cross-project scope check.
 *
 * Two controlled projects share the same entity, target field, and business
 * key, so only the project name differs. A draft staged in one project must not
 * appear in the other, and returning to the first project must restore its own
 * draft. The draft store below applies the same scope rule the real store uses,
 * so the assertion covers the component's forwarding of `projectName`.
 */
describe('ReconciliationWorkspace cross-project scope (VM-9)', () => {
  const scopes = new Map<string, WorkspaceDraft>()
  const scopeId = (projectName: string, entityName: string, targetField: string) =>
    JSON.stringify([projectName, entityName, targetField])

  beforeEach(() => {
    vi.clearAllMocks()
    scopes.clear()
    document.querySelectorAll('.v-overlay-container').forEach((element) => element.remove())
    reconciliationStore.loadSelectionCapabilities.mockImplementation(async () => capabilities)
    reconciliationStore.searchSelection.mockImplementation(async () => ({
      mode: 'ranked' as const,
      items: [record(101, 'Bronze Age')],
    }))
    reconciliationStore.browseSelection.mockImplementation(async () => ({
      items: [],
      completeness: 'complete' as const,
    }))
    reconciliationStore.fetchSavedDecisionStates.mockImplementation(async () => ({}))
    reconciliationStore.changedDecisionKeys.mockImplementation(() => [])
    reconciliationStore.getDecisionBatchIssues.mockImplementation(() => [])
    reconciliationStore.saveWorkspaceDraft.mockImplementation(
      (projectName: string, entityName: string, targetField: string, draft: WorkspaceDraft) => {
        scopes.set(scopeId(projectName, entityName, targetField), draft)
        return true
      }
    )
    reconciliationStore.loadWorkspaceDraft.mockImplementation(
      (projectName: string, entityName: string, targetField: string) => {
        const draft = scopes.get(scopeId(projectName, entityName, targetField))
        return draft ? { status: 'restored' as const, draft } : { status: 'empty' as const, draft: null }
      }
    )
  })

  /** Stage one decision for key K1 in the workspace mounted for `projectName`. */
  async function stageDecisionIn(projectName: string) {
    const wrapper = await mountWorkspace({ rows: previewRows(3), projectName })
    await wrapper.find('[data-testid="workspace-row-0"]').trigger('click')
    await searchAndSelect(wrapper)
    const input = wrapper.find('[data-testid="workspace-search-input"] input')
    await input.trigger('keydown', { key: 'Enter', altKey: true })
    await flushPromises()
    expect(wrapper.find('[data-testid="workspace-save"]').text()).toContain('1')
    return wrapper
  }

  it('never lets one project inherit another project draft or selection', async () => {
    const alpha = await stageDecisionIn('vm9-alpha')
    try {
      // The draft was persisted under the alpha scope only.
      expect(scopes.size).toBe(1)
      expect([...scopes.keys()]).toEqual([JSON.stringify(['vm9-alpha', 'site', 'site_name'])])

      // Opening the same entity, field, and keys under another project starts empty.
      const beta = await mountWorkspace({ rows: previewRows(3), projectName: 'vm9-beta' })
      try {
        expect(reconciliationStore.loadWorkspaceDraft).toHaveBeenCalledWith('vm9-beta', 'site', 'site_name')
        expect(beta.find('[data-testid="workspace-save"]').text()).toContain('0')
        expect(beta.text()).not.toContain('Restored 1 unsaved decision')
        expect(beta.text()).not.toContain('Bronze Age')
      } finally {
        beta.unmount()
      }

      // Returning to the first project restores its own draft.
      const alphaAgain = await mountWorkspace({ rows: previewRows(3), projectName: 'vm9-alpha' })
      try {
        expect(alphaAgain.text()).toContain('Restored 1 unsaved decision')
        expect(alphaAgain.find('[data-testid="workspace-save"]').text()).toContain('1')
        // A restored draft never reinstates the target selection or result list.
        expect(alphaAgain.text()).not.toContain('Bronze Age')
      } finally {
        alphaAgain.unmount()
      }
    } finally {
      alpha.unmount()
    }
  })
})
