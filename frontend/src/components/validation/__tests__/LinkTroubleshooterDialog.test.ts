import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import LinkTroubleshooterDialog from '../LinkTroubleshooterDialog.vue'
import { useLinkTroubleshooter } from '@/composables/useLinkTroubleshooter'
import { integrityTroubleshooterApi } from '@/api/integrityTroubleshooter'
import type {
  FormattedError,
  IntegrityTroubleshootResponse,
  LinkTroubleshootRequest,
  LinkTroubleshootResponse,
  LinkTroubleshootTrial,
  ValidationError,
} from '@/types'

vi.mock('@/composables/useLinkTroubleshooter', () => ({
  useLinkTroubleshooter: vi.fn(),
}))

vi.mock('@/api/integrityTroubleshooter', () => ({
  integrityTroubleshooterApi: { inspect: vi.fn() },
}))

const vuetify = createVuetify({ components, directives })

const openRequests: LinkTroubleshootRequest[] = []
const runCalls: Array<{ local: string[]; remote: string[]; page: number; pageSize: number; rowFilter: string }> = []
let openedResponse = makeResponse()
let nextRunResponse = makeResponse()

const mockOpen = vi.fn<ReturnType<typeof useLinkTroubleshooter>['open']>()
const mockRun = vi.fn<ReturnType<typeof useLinkTroubleshooter>['run']>()
const mockReset = vi.fn<ReturnType<typeof useLinkTroubleshooter>['reset']>()

const state: ReturnType<typeof useLinkTroubleshooter> = {
  loading: ref(false),
  error: ref<FormattedError | null>(null),
  result: ref<LinkTroubleshootResponse | null>(null),
  localKeys: ref<string[]>([]),
  remoteKeys: ref<string[]>([]),
  page: ref(1),
  pageSize: ref(50),
  rowFilter: ref<'all' | 'unmatched' | 'multiply_matched'>('unmatched'),
  open: mockOpen,
  run: mockRun,
  reset: mockReset,
}

function makeResponse(
  options: {
    status?: 'reproduced' | 'not_reproduced' | 'ineligible'
    diagnosticStatus?: 'complete' | 'failed' | 'incomplete' | 'not_run'
    trialStatus?: 'complete' | 'failed' | 'incomplete'
    configuredRemoteKeys?: string[]
    trial?: LinkTroubleshootTrial | null
  } = {}
): LinkTroubleshootResponse {
  const trialStatus = options.trialStatus ?? 'complete'
  const trial =
    options.trial === undefined
      ? {
          status: trialStatus,
          reason: trialStatus === 'complete' ? 'complete' : 'row_limit_exceeded',
          message: trialStatus === 'complete' ? 'Trial completed.' : 'Trial details are unavailable.',
          local_keys: ['saved_code'],
          remote_keys: options.configuredRemoteKeys ?? ['saved_value'],
          totals:
            trialStatus === 'complete'
              ? {
                  input_a_rows: 3,
                  output_rows: 2,
                  unmatched_a_rows: 1,
                  multiply_matched_a_rows: 0,
                }
              : null,
          issues: [],
          rows:
            trialStatus === 'complete'
              ? [
                  {
                    input_position: 0,
                    key_values: ['A'],
                    matched: true,
                    remote_match_count: 1,
                    output_row_contribution: 1,
                  },
                ]
              : [],
          pagination:
            trialStatus === 'complete'
              ? {
                  page: 1,
                  page_size: 50,
                  filtered_row_count: 60,
                  returned_row_count: 1,
                  has_next: true,
                }
              : null,
        }
      : options.trial

  return {
    status: options.status ?? 'reproduced',
    reason:
      options.status === 'not_reproduced'
        ? 'warning_changed'
        : options.status === 'ineligible'
          ? 'signature_mismatch'
          : 'reproduced',
    message:
      options.status === 'reproduced' || options.status === undefined
        ? 'The warning was reproduced.'
        : 'The warning is stale.',
    relationship: {
      local_entity: 'orders',
      remote_entity: 'customers',
      fk_index: 0,
      join_type: 'inner',
      link_pass: 'initial',
      constraints: { allow_row_decrease: true },
    },
    key_options: { local: ['saved_code', 'system_id'], remote: ['saved_value', 'system_id'] },
    configured_keys: { local_keys: ['saved_code'], remote_keys: options.configuredRemoteKeys ?? ['saved_value'] },
    baseline: {
      input_a_rows: 3,
      output_rows: 2,
      unmatched_a_rows: options.diagnosticStatus === 'failed' || options.diagnosticStatus === 'incomplete' ? null : 1,
      multiply_matched_a_rows: 0,
      diagnostic_status: options.diagnosticStatus ?? 'complete',
      diagnostic_reason:
        options.diagnosticStatus === 'failed'
          ? 'baseline_counts_mismatch'
          : options.diagnosticStatus === 'incomplete'
            ? 'row_limit_exceeded'
            : null,
      diagnostic_message:
        options.diagnosticStatus === 'failed' || options.diagnosticStatus === 'incomplete'
          ? 'Configured-key diagnostics are unavailable.'
          : null,
      issues: [],
    },
    trial,
  }
}

function candidateMessage(overrides: Partial<ValidationError> = {}): ValidationError {
  return {
    severity: 'warning',
    entity: 'orders',
    message: 'Link changed the row count.',
    code: 'ROW_COUNT_MISMATCH',
    metadata: {
      fk_index: 0,
      fk_signature: 'saved-signature',
      link_pass: 'initial',
      join_type: 'inner',
      remote_entity: 'customers',
    },
    ...overrides,
  }
}

function integrityMessage(overrides: Partial<ValidationError> = {}): ValidationError {
  return {
    severity: 'warning',
    entity: 'orders',
    message: "2 foreign key value(s) not found in 'customers'",
    code: 'FK_DATA_INTEGRITY',
    metadata: { fk_index: 0, fk_signature: 'saved-signature', orphan_count: 2 },
    ...overrides,
  }
}

function integrityResponse(overrides: Partial<IntegrityTroubleshootResponse> = {}): IntegrityTroubleshootResponse {
  return {
    status: 'reproduced',
    reason: 'reproduced',
    message: 'The current full-data unmatched count matches the warning.',
    source: 'current full normalization',
    relationship: {
      local_entity: 'orders',
      remote_entity: 'customers',
      fk_index: 0,
      join_type: 'inner',
      constraints: {},
    },
    configured_keys: { local_keys: ['customer_code'], remote_keys: ['code'] },
    recorded_orphan_count: 2,
    current_orphan_count: 2,
    values: {
      page: 1,
      page_size: 50,
      distinct_value_count: 1,
      returned_value_count: 1,
      has_next: false,
      values: [{ key_values: ['MISSING-A'], local_row_count: 1, token: 'token-a' }],
    },
    selected: null,
    ...overrides,
  }
}

function mountDialog(
  response: LinkTroubleshootResponse = makeResponse(),
  message: ValidationError = candidateMessage()
) {
  openedResponse = response
  nextRunResponse = response
  mockOpen.mockImplementation(async (request) => {
    openRequests.push(request)
    state.result.value = openedResponse
    state.localKeys.value = [...(openedResponse.configured_keys?.local_keys ?? [])]
    state.remoteKeys.value = [...(openedResponse.configured_keys?.remote_keys ?? [])]
    return openedResponse
  })
  mockRun.mockImplementation(async () => {
    runCalls.push({
      local: [...state.localKeys.value],
      remote: [...state.remoteKeys.value],
      page: state.page.value,
      pageSize: Number(state.pageSize.value),
      rowFilter: state.rowFilter.value,
    })
    state.result.value = nextRunResponse
    return nextRunResponse
  })

  return mount(LinkTroubleshooterDialog, {
    props: { modelValue: true, projectName: 'project-a', message },
    global: {
      plugins: [vuetify],
      stubs: {
        VDialog: { template: '<div data-testid="dialog"><slot /></div>' },
        VSelect: {
          props: ['items', 'label', 'modelValue'],
          emits: ['update:modelValue'],
          template: `
            <label>
              <span>{{ label }}</span>
              <select
                :aria-label="label"
                :data-selected="modelValue"
                :value="modelValue"
                @change="$emit('update:modelValue', $event.target.value)"
              >
                <option
                  v-for="item in items"
                  :key="typeof item === 'object' ? item.value : item"
                  :value="typeof item === 'object' ? item.value : item"
                >
                  {{ typeof item === 'object' ? item.title : item }}
                </option>
              </select>
            </label>
          `,
        },
        VPagination: {
          props: ['length', 'modelValue'],
          emits: ['update:modelValue'],
          template: `<button type="button" aria-label="Next page" @click="$emit('update:modelValue', modelValue + 1)">Next page</button>`,
        },
      },
    },
  })
}

describe('LinkTroubleshooterDialog', () => {
  beforeEach(() => {
    openRequests.length = 0
    runCalls.length = 0
    state.loading.value = false
    state.error.value = null
    state.result.value = null
    state.localKeys.value = []
    state.remoteKeys.value = []
    state.page.value = 1
    state.pageSize.value = 50
    state.rowFilter.value = 'unmatched'
    mockOpen.mockReset()
    mockRun.mockReset()
    mockReset.mockReset()
    mockReset.mockImplementation(() => {
      state.result.value = null
      state.error.value = null
      state.localKeys.value = []
      state.remoteKeys.value = []
      state.page.value = 1
      state.pageSize.value = 50
      state.rowFilter.value = 'unmatched'
    })
    vi.mocked(useLinkTroubleshooter).mockReturnValue(state)
    vi.mocked(integrityTroubleshooterApi.inspect).mockReset()
    vi.mocked(integrityTroubleshooterApi.inspect).mockResolvedValue(integrityResponse())
  })

  it('shows the saved relationship as read-only and initializes configured key pairs', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    expect(wrapper.text()).toContain('orders → customers')
    expect(wrapper.text()).toContain('Join: inner')
    expect(wrapper.text()).toContain('Link pass: initial')
    expect(wrapper.text()).toContain('allow_row_decrease: true')
    expect(wrapper.find('[aria-label="Saved relationship"] input').exists()).toBe(false)
    expect(wrapper.find('select[aria-label="A key"]').attributes('data-selected')).toBe('saved_code')
    expect(wrapper.find('select[aria-label="B key"]').attributes('data-selected')).toBe('saved_value')
    expect(wrapper.findAll('button').some((button) => button.text().trim() === 'Save')).toBe(false)
  })

  it('shows the entity pair from the warning metadata while the first request loads', async () => {
    mockOpen.mockImplementationOnce(() => new Promise<LinkTroubleshootResponse | null>(() => undefined))
    const wrapper = mountDialog()

    expect(wrapper.text()).toContain('orders → customers')
    expect(wrapper.text()).not.toContain('Unknown entity')
  })

  it('keeps a configured system_id key selected for the initial trial', async () => {
    const wrapper = mountDialog(makeResponse({ configuredRemoteKeys: ['system_id'] }))
    await flushPromises()

    expect(wrapper.find('select[aria-label="B key"]').attributes('data-selected')).toBe('system_id')
    expect(openRequests[0]).toEqual({
      issue_type: 'row_count_mismatch',
      local_entity: 'orders',
      metadata: candidateMessage().metadata,
    })

    const runButton = wrapper.findAll('button').find((button) => button.text().includes('Run trial'))
    expect(runButton).toBeDefined()
    await runButton!.trigger('click')
    await flushPromises()

    expect(runCalls[0]).toEqual({
      local: ['saved_code'],
      remote: ['system_id'],
      page: 1,
      pageSize: 50,
      rowFilter: 'unmatched',
    })
  })

  it.each(['not_reproduced', 'ineligible'] as const)('hides trial controls for a %s baseline', async (status) => {
    const wrapper = mountDialog(makeResponse({ status, trial: null }))
    await flushPromises()

    expect(wrapper.text()).toContain(status)
    expect(wrapper.text()).toContain('The warning is stale.')
    expect(wrapper.find('select[aria-label="A key"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Run trial')
    expect(wrapper.find('table').exists()).toBe(false)
  })

  it('renders the A-row diagnostics columns and key values', async () => {
    const trial: LinkTroubleshootTrial = {
      status: 'complete',
      reason: 'complete',
      message: 'Trial completed.',
      local_keys: ['saved_code', 'saved_value'],
      remote_keys: ['saved_value', 'system_id'],
      totals: { input_a_rows: 2, output_rows: 1, unmatched_a_rows: 1, multiply_matched_a_rows: 0 },
      issues: [],
      rows: [
        { input_position: 4, key_values: ['A-1', 7], matched: true, remote_match_count: 1, output_row_contribution: 1 },
      ],
      pagination: { page: 1, page_size: 50, filtered_row_count: 1, returned_row_count: 1, has_next: false },
    }
    const wrapper = mountDialog(makeResponse({ trial }))
    await flushPromises()

    const section = wrapper.find('section[aria-label="A-row diagnostics"]')
    expect(section.find('thead').text()).toContain('A key: saved_code')
    expect(section.find('thead').text()).toContain('A key: saved_value')
    expect(section.find('thead').text()).toContain('Matched')

    const cells = section
      .findAll('tbody tr')[0]
      ?.findAll('td')
      .map((cell) => cell.text())
    expect(cells).toEqual(['5', 'A-1', '7', 'Yes', '1', '1'])
  })

  it('shows the filter empty state when no A rows are returned', async () => {
    const trial: LinkTroubleshootTrial = {
      status: 'complete',
      reason: 'complete',
      message: 'Trial completed.',
      local_keys: ['saved_code'],
      remote_keys: ['saved_value'],
      totals: { input_a_rows: 0, output_rows: 0, unmatched_a_rows: 0, multiply_matched_a_rows: 0 },
      issues: [],
      rows: [],
      pagination: { page: 1, page_size: 50, filtered_row_count: 0, returned_row_count: 0, has_next: false },
    }
    const wrapper = mountDialog(makeResponse({ trial }))
    await flushPromises()

    expect(wrapper.find('section[aria-label="A-row diagnostics"]').text()).toContain('No rows match this filter.')
  })

  it('shows full totals and sends the same keys when filters, page size, and pages change', async () => {
    const first = makeResponse()
    const pageTwo = makeResponse()
    if (pageTwo.trial?.pagination) {
      pageTwo.trial.pagination.page = 2
    }
    const wrapper = mountDialog(first)
    await flushPromises()

    nextRunResponse = pageTwo
    const initialTotals = first.trial?.totals
    await wrapper.find('select[aria-label="Filter rows"]').setValue('multiply_matched')
    await flushPromises()
    expect(runCalls[0]).toEqual({
      local: ['saved_code'],
      remote: ['saved_value'],
      page: 1,
      pageSize: 50,
      rowFilter: 'multiply_matched',
    })
    expect(wrapper.text()).toContain('Complete totals cover the full link input.')
    expect(wrapper.text()).toContain('Input A rows')
    expect(wrapper.text()).toContain('Output rows')

    await wrapper.find('select[aria-label="Rows per page"]').setValue('25')
    await flushPromises()
    expect(runCalls[1]).toEqual({
      local: ['saved_code'],
      remote: ['saved_value'],
      page: 1,
      pageSize: 25,
      rowFilter: 'multiply_matched',
    })

    await wrapper.find('button[aria-label="Next page"]').trigger('click')
    await flushPromises()

    expect(runCalls[2]).toEqual({
      local: ['saved_code'],
      remote: ['saved_value'],
      page: 2,
      pageSize: 25,
      rowFilter: 'multiply_matched',
    })
    expect(state.result.value?.trial?.pagination?.page).toBe(2)
    expect(state.result.value?.trial?.totals).toEqual(initialTotals)
  })

  it.each(['failed', 'incomplete'] as const)(
    'keeps %s configured-key diagnostics separate from a complete requested trial',
    async (status) => {
      const wrapper = mountDialog(makeResponse({ diagnosticStatus: status }))
      await flushPromises()

      expect(wrapper.text()).toContain(status)
      expect(wrapper.text()).toContain(status === 'failed' ? 'baseline_counts_mismatch' : 'row_limit_exceeded')
      expect(wrapper.text()).toContain('Configured-key diagnostics are unavailable.')
      const unmatchedRow = wrapper.findAll('section[aria-label="Baseline and trial comparison"] tbody tr')[2]
      expect(unmatchedRow?.findAll('td')[1]?.text()).toBe('—')
      expect(unmatchedRow?.findAll('td')[2]?.text()).toBe('1')
    }
  )

  it.each(['failed', 'incomplete'] as const)(
    'shows a %s trial alert without totals or A-row details',
    async (status) => {
      const wrapper = mountDialog(makeResponse({ trialStatus: status }))
      await flushPromises()

      expect(wrapper.text()).toContain(`Trial ${status}:`)
      expect(wrapper.text()).toContain('row_limit_exceeded')
      expect(wrapper.find('section[aria-label="A-row diagnostics"]').exists()).toBe(false)
      expect(wrapper.findAll('table')).toHaveLength(1)
    }
  )

  it('resets on close and starts a fresh request when reopened', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    const closeButton = wrapper.findAll('button').find((button) => button.text() === 'Close')
    expect(closeButton).toBeDefined()
    await closeButton!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false])

    await wrapper.setProps({ modelValue: false })
    await flushPromises()
    expect(mockReset).toHaveBeenCalled()
    expect(state.result.value).toBeNull()

    openedResponse = makeResponse()
    await wrapper.setProps({ modelValue: true })
    await flushPromises()
    expect(openRequests).toHaveLength(2)
    expect(state.localKeys.value).toEqual(['saved_code'])
    expect(state.remoteKeys.value).toEqual(['saved_value'])
  })

  it('shows a local message and makes no request for a non-candidate warning', async () => {
    const wrapper = mountDialog(makeResponse(), candidateMessage({ code: 'OTHER_WARNING' }))
    await flushPromises()

    expect(wrapper.text()).toContain('This warning cannot be troubleshot.')
    expect(openRequests).toHaveLength(0)
  })

  it('opens the read-only integrity body without sending a row-count request', async () => {
    const wrapper = mountDialog(makeResponse(), integrityMessage())
    await flushPromises()

    expect(openRequests).toHaveLength(0)
    expect(mockOpen).not.toHaveBeenCalled()
    expect(mockReset).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Complete distinct unmatched count: 1')
    expect(wrapper.text()).toContain('orders → customers')
    expect(wrapper.find('select[aria-label="A key"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Run trial')
    expect(wrapper.text()).not.toContain('Trial key pairs')
  })

  it('explains a malformed integrity warning without sending either request', async () => {
    const wrapper = mountDialog(
      makeResponse(),
      integrityMessage({ metadata: { fk_signature: 'saved-signature', orphan_count: 2 } })
    )
    await flushPromises()

    expect(wrapper.text()).toContain('does not record which saved link')
    expect(openRequests).toHaveLength(0)
    expect(vi.mocked(integrityTroubleshooterApi.inspect)).not.toHaveBeenCalled()
  })

  it('clears row-count trial state when switching from a row-count warning to an integrity warning', async () => {
    const wrapper = mountDialog()
    await flushPromises()
    expect(openRequests).toHaveLength(1)

    await wrapper.setProps({ message: integrityMessage() })
    await flushPromises()

    expect(openRequests).toHaveLength(1)
    expect(wrapper.text()).not.toContain('Trial key pairs')
    expect(wrapper.text()).toContain('Complete distinct unmatched count: 1')
  })
})
