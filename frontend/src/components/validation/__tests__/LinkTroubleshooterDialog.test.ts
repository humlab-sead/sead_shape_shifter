import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { computed, nextTick, ref } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import LinkTroubleshooterDialog from '../LinkTroubleshooterDialog.vue'
import { useLinkTroubleshooter } from '@/composables/useLinkTroubleshooter'
import { integrityTroubleshooterApi } from '@/api/integrityTroubleshooter'
import type {
  FormattedError,
  IntegrityTroubleshootResponse,
  LinkExperimentContextRequest,
  LinkExperimentContextResponse,
  LinkTroubleshootComparison,
  LinkTroubleshootDetail,
  LinkTroubleshootExceptionGroup,
  LinkTroubleshootExceptionRow,
  LinkTroubleshootJoinType,
  LinkTroubleshootTrialSettings,
  ValidationError,
} from '@/types'

vi.mock('@/composables/useLinkTroubleshooter', () => ({
  useLinkTroubleshooter: vi.fn(),
}))

vi.mock('@/api/integrityTroubleshooter', () => ({
  integrityTroubleshooterApi: { inspect: vi.fn() },
}))

const vuetify = createVuetify({ components, directives })

interface RunCall {
  local: string[]
  remote: string[]
  how: LinkTroubleshootJoinType | null
  allowNullKeys: boolean | null
  nullKeysEqual: boolean | null
}

const openRequests: LinkExperimentContextRequest[] = []
const runCalls: RunCall[] = []
const closeCalls: string[] = []
let nextTrial: LinkTroubleshootComparison = makeComparison()
let nextTrialKeys = { local: ['saved_code'], remote: ['saved_value'] }
let originalControls = {
  local: [] as string[],
  remote: [] as string[],
  how: null as LinkTroubleshootJoinType | null,
  allow: null as boolean | null,
  equal: null as boolean | null,
}

const mockOpen = vi.fn<ReturnType<typeof useLinkTroubleshooter>['open']>()
const mockRun = vi.fn<ReturnType<typeof useLinkTroubleshooter>['run']>()
const mockReset = vi.fn<ReturnType<typeof useLinkTroubleshooter>['reset']>()
const mockClose = vi.fn<ReturnType<typeof useLinkTroubleshooter>['close']>()

const state: ReturnType<typeof useLinkTroubleshooter> = {
  loading: ref(false),
  error: ref<FormattedError | null>(null),
  context: ref<LinkExperimentContextResponse | null>(null),
  trial: ref<LinkTroubleshootComparison | null>(null),
  trialLocalKeys: ref<string[]>([]),
  trialRemoteKeys: ref<string[]>([]),
  trialStale: ref(false),
  refreshed: ref(false),
  localKeys: ref<string[]>([]),
  remoteKeys: ref<string[]>([]),
  how: ref<LinkTroubleshootJoinType | null>(null),
  allowNullKeys: ref<boolean | null>(null),
  nullKeysEqual: ref<boolean | null>(null),
  page: ref(1),
  pageSize: ref(50),
  group: ref<'unmatched' | 'multiply_matched'>('unmatched'),
  side: ref<'baseline' | 'trial'>('baseline'),
  canRunTrial: computed(
    () =>
      Boolean(state.context.value?.context_id) &&
      state.localKeys.value.length > 0 &&
      state.localKeys.value.length === state.remoteKeys.value.length
  ),
  open: mockOpen,
  run: mockRun,
  reset: mockReset,
  close: mockClose,
}

function makeSettings(overrides: Partial<LinkTroubleshootTrialSettings> = {}): LinkTroubleshootTrialSettings {
  return {
    join_type: { requested: null, source: 'inherited', effective: 'inner' },
    allow_null_keys: { requested: null, source: 'inherited' },
    null_keys_equal: { requested: null, source: 'inherited' },
    resolved_null_policy: { enforce_strict_null_keys: true, prevent_null_key_matches: false },
    ...overrides,
  }
}

function makeRow(
  position: number,
  values: Array<unknown | { value: unknown; truncated?: boolean; original_length?: number | null }>
): LinkTroubleshootExceptionRow {
  return {
    input_position: position,
    key_values: values.map((entry) => {
      if (entry !== null && typeof entry === 'object' && 'value' in entry) {
        const bounded = entry as { value: unknown; truncated?: boolean; original_length?: number | null }
        return {
          value: bounded.value,
          truncated: bounded.truncated ?? false,
          original_length: bounded.original_length ?? null,
        }
      }
      return { value: entry, truncated: false, original_length: null }
    }),
    remote_match_count: 0,
    output_row_contribution: 0,
  }
}

function makeGroup(overrides: Partial<LinkTroubleshootExceptionGroup> = {}): LinkTroubleshootExceptionGroup {
  return {
    total_count: 0,
    returned_count: 0,
    row_cap: 100,
    row_cap_reached: false,
    budget_exhausted: false,
    rows: [],
    ...overrides,
  }
}

function makeDetail(overrides: Partial<LinkTroubleshootDetail> = {}): LinkTroubleshootDetail {
  return {
    detail_truncated: false,
    findings: { total_count: 0, returned_count: 0, truncated: false, issues: [] },
    unmatched: makeGroup(),
    multiply_matched: makeGroup(),
    ...overrides,
  }
}

function makeContext(
  options: {
    status?: 'reproduced' | 'not_reproduced' | 'ineligible'
    contextId?: string | null
    diagnosticStatus?: 'complete' | 'failed' | 'incomplete' | 'not_run'
    settings?: LinkTroubleshootTrialSettings | null
    constraints?: Record<string, unknown>
    detail?: LinkTroubleshootDetail
    configuredRemoteKeys?: string[]
  } = {}
): LinkExperimentContextResponse {
  const status = options.status ?? 'reproduced'
  const contextId = options.contextId === undefined ? 'context-1' : options.contextId
  const diagnosticStatus = options.diagnosticStatus ?? 'complete'
  const complete = diagnosticStatus === 'complete'
  return {
    context_id: contextId,
    status,
    reason: status === 'reproduced' ? 'reproduced' : status === 'ineligible' ? 'signature_mismatch' : 'warning_changed',
    message: status === 'reproduced' ? 'The warning was reproduced.' : 'The warning is stale.',
    expires_at: contextId ? '2026-01-01T12:15:00Z' : null,
    relationship: {
      local_entity: 'orders',
      remote_entity: 'customers',
      fk_index: 0,
      join_type: 'inner',
      link_pass: 'initial',
      constraints: options.constraints ?? { allow_row_decrease: true },
    },
    key_options: { local: ['saved_code', 'system_id'], remote: ['saved_value', 'system_id'] },
    configured_keys: { local_keys: ['saved_code'], remote_keys: options.configuredRemoteKeys ?? ['saved_value'] },
    baseline:
      status === 'reproduced' && contextId !== null
        ? {
            input_a_rows: complete ? 3 : null,
            output_rows: complete ? 2 : null,
            unmatched_a_rows: complete ? 1 : null,
            multiply_matched_a_rows: complete ? 0 : null,
            diagnostic_status: diagnosticStatus,
            diagnostic_reason:
              diagnosticStatus === 'complete'
                ? null
                : diagnosticStatus === 'failed'
                  ? 'baseline_counts_mismatch'
                  : 'row_limit_exceeded',
            diagnostic_message: diagnosticStatus === 'complete' ? null : 'Configured-key diagnostics are unavailable.',
            issues: [],
            settings: options.settings === undefined ? makeSettings() : options.settings,
            detail: options.detail ?? makeDetail(),
          }
        : null,
  }
}

function makeComparison(overrides: Partial<LinkTroubleshootComparison> = {}): LinkTroubleshootComparison {
  return {
    status: 'complete',
    reason: 'complete',
    message: 'Trial completed.',
    settings: makeSettings(),
    totals: { input_a_rows: 3, output_rows: 3, unmatched_a_rows: 1, multiply_matched_a_rows: 0 },
    detail: makeDetail(),
    ...overrides,
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

function applyContextToState(response: LinkExperimentContextResponse): void {
  state.context.value = response
  state.trial.value = null
  state.trialLocalKeys.value = []
  state.trialRemoteKeys.value = []
  state.trialStale.value = false
  state.refreshed.value = false
  state.error.value = null
  state.localKeys.value = [...(response.configured_keys?.local_keys ?? [])]
  state.remoteKeys.value = [...(response.configured_keys?.remote_keys ?? [])]
  const settings = response.baseline?.settings ?? null
  const constraints = response.relationship?.constraints ?? {}
  const explicit = (key: string): boolean | null => {
    const value = constraints[key]
    return typeof value === 'boolean' ? value : null
  }
  state.how.value = settings
    ? (settings.join_type.requested ?? settings.join_type.effective)
    : response.relationship?.join_type === 'left'
      ? 'left'
      : 'inner'
  state.allowNullKeys.value = settings ? settings.allow_null_keys.requested : explicit('allow_null_keys')
  state.nullKeysEqual.value = settings ? settings.null_keys_equal.requested : explicit('null_keys_equal')
  state.page.value = 1
  state.pageSize.value = 50
  state.group.value = 'unmatched'
  state.side.value = 'baseline'
  originalControls = {
    local: [...state.localKeys.value],
    remote: [...state.remoteKeys.value],
    how: state.how.value,
    allow: state.allowNullKeys.value,
    equal: state.nullKeysEqual.value,
  }
}

function clearState(): void {
  state.context.value = null
  state.trial.value = null
  state.trialLocalKeys.value = []
  state.trialRemoteKeys.value = []
  state.refreshed.value = false
  state.error.value = null
  state.localKeys.value = []
  state.remoteKeys.value = []
  state.how.value = null
  state.allowNullKeys.value = null
  state.nullKeysEqual.value = null
  state.page.value = 1
  state.pageSize.value = 50
  state.group.value = 'unmatched'
  state.side.value = 'baseline'
}

function mountDialog(
  context: LinkExperimentContextResponse = makeContext(),
  message: ValidationError = candidateMessage()
) {
  mockOpen.mockImplementation(async (request) => {
    openRequests.push(request)
    applyContextToState(context)
    return context
  })
  mockRun.mockImplementation(async () => {
    runCalls.push({
      local: [...state.localKeys.value],
      remote: [...state.remoteKeys.value],
      how: state.how.value,
      allowNullKeys: state.allowNullKeys.value,
      nullKeysEqual: state.nullKeysEqual.value,
    })
    state.trial.value = nextTrial
    state.trialLocalKeys.value = [...nextTrialKeys.local]
    state.trialRemoteKeys.value = [...nextTrialKeys.remote]
    state.trialStale.value = false
    return nextTrial
  })
  mockReset.mockImplementation(() => {
    state.trial.value = null
    state.trialStale.value = false
    state.error.value = null
    state.refreshed.value = false
    state.localKeys.value = [...originalControls.local]
    state.remoteKeys.value = [...originalControls.remote]
    state.how.value = originalControls.how
    state.allowNullKeys.value = originalControls.allow
    state.nullKeysEqual.value = originalControls.equal
    state.page.value = 1
    state.pageSize.value = 50
    state.group.value = 'unmatched'
    state.side.value = 'baseline'
  })
  mockClose.mockImplementation(async () => {
    closeCalls.push('closed')
    clearState()
  })

  return mount(LinkTroubleshooterDialog, {
    props: { modelValue: true, projectName: 'project-a', message },
    global: {
      plugins: [vuetify],
      stubs: {
        VDialog: { template: '<div data-testid="dialog"><slot /></div>' },
        VSelect: {
          props: ['items', 'label', 'modelValue', 'ariaLabel'],
          emits: ['update:modelValue'],
          template: `
            <label>
              <span>{{ label }}</span>
              <select
                :aria-label="ariaLabel ?? label"
                :data-selected="JSON.stringify(modelValue)"
                :value="JSON.stringify(modelValue)"
                @change="$emit('update:modelValue', JSON.parse($event.target.value))"
              >
                <option
                  v-for="item in items"
                  :key="JSON.stringify(typeof item === 'object' ? item.value : item)"
                  :value="JSON.stringify(typeof item === 'object' ? item.value : item)"
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
        // Tooltip text is rendered in an overlay in the browser, so the stub
        // renders the help text inline to keep it assertable.
        VTooltip: {
          template: '<div data-testid="tooltip"><slot name="activator" :props="{}" /><slot /></div>',
        },
      },
    },
  })
}

async function selectOption(wrapper: ReturnType<typeof mountDialog>, label: string, value: unknown): Promise<void> {
  await wrapper.find(`select[aria-label="${label}"]`).setValue(JSON.stringify(value))
  await flushPromises()
}

async function selectSide(wrapper: ReturnType<typeof mountDialog>, value: 'baseline' | 'trial'): Promise<void> {
  await wrapper.find(`button[data-side="${value}"]`).trigger('click')
  await flushPromises()
}

function statValue(wrapper: ReturnType<typeof mountDialog>, key: 'source_rows' | 'output_rows'): string {
  return wrapper.find(`[data-stat="${key}"] .link-result-stat-value`).text()
}

function buttonByText(wrapper: ReturnType<typeof mountDialog>, text: string) {
  return wrapper.findAll('button').find((button) => button.text().trim() === text)
}

describe('LinkTroubleshooterDialog', () => {
  beforeEach(() => {
    openRequests.length = 0
    runCalls.length = 0
    closeCalls.length = 0
    nextTrial = makeComparison()
    nextTrialKeys = { local: ['saved_code'], remote: ['saved_value'] }
    clearState()
    state.loading.value = false
    mockOpen.mockReset()
    mockRun.mockReset()
    mockReset.mockReset()
    mockClose.mockReset()
    vi.mocked(useLinkTroubleshooter).mockReturnValue(state)
    vi.mocked(integrityTroubleshooterApi.inspect).mockReset()
    vi.mocked(integrityTroubleshooterApi.inspect).mockResolvedValue(integrityResponse())
  })

  it('shows the saved relationship as read-only and initializes controls from settings', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    expect(wrapper.text()).toContain('orders → customers')
    expect(wrapper.text()).toContain('Initial · Allow row decrease')
    expect(wrapper.find('section[aria-label="Saved relationship"]').exists()).toBe(false)
    expect(wrapper.find('select[aria-label="Key pair 1 local key (orders)"]').attributes('data-selected')).toBe(
      JSON.stringify('saved_code')
    )
    expect(wrapper.find('select[aria-label="Key pair 1 remote key (customers)"]').attributes('data-selected')).toBe(
      JSON.stringify('saved_value')
    )
    expect(wrapper.find('select[aria-label="Join type"]').attributes('data-selected')).toBe(JSON.stringify('inner'))
    expect(wrapper.find('select[aria-label="Allow missing join keys"]').attributes('data-selected')).toBe('null')
    expect(wrapper.find('select[aria-label="Match null join-key parts"]').attributes('data-selected')).toBe('null')
    expect(wrapper.text()).toContain('Saved: inherited; effective inner')
    expect(wrapper.text()).toContain('Allow missing join keys: inherited')
    expect(wrapper.text()).toContain('Strict null checks are enforced')
    // Help text and result totals live in tooltips, not in the dialog body.
    const tooltipText = wrapper.findAll('[data-testid="tooltip"]').map((tooltip) => tooltip.text())
    expect(tooltipText).toHaveLength(3)
    expect(tooltipText.join(' ')).toContain('Lets rows with a missing (null) key value still join.')
    expect(tooltipText.join(' ')).toContain('Treats two missing (null) key values as equal')
    expect(tooltipText.join(' ')).toContain('Allow missing join keys: inherited')
    expect(tooltipText.join(' ')).toContain('Strict null checks are enforced')
    expect(tooltipText.join(' ')).toContain('Totals cover the full link input.')
    expect(wrapper.find('button[aria-label="About result totals"]').exists()).toBe(true)
    expect(wrapper.findAll('p').some((paragraph) => paragraph.text() === 'Totals cover the full link input.')).toBe(
      false
    )
    const joinNote = wrapper.find('.join-note')
    const affectedRowToolbar = wrapper.find('.affected-row-toolbar')
    expect(joinNote.text()).toBe('The saved inner join removes unmatched source rows.')
    expect(affectedRowToolbar.text().indexOf(joinNote.text())).toBeLessThan(
      affectedRowToolbar.text().indexOf('Unmatched')
    )
    expect(wrapper.findAll('button').some((button) => button.text().trim() === 'Save')).toBe(false)
  })

  it('summarizes cardinality, linking pass, and only the flags that are set', async () => {
    const wrapper = mountDialog(
      makeContext({
        constraints: {
          cardinality: 'many_to_one',
          allow_row_decrease: false,
          require_unique_right: true,
        },
      })
    )
    await flushPromises()

    const heading = wrapper.find('.link-troubleshooter-heading')
    expect(heading.text()).toContain('orders → customers')
    expect(heading.text()).toContain('Many-to-one · Initial · Require unique right')
    expect(heading.text()).not.toContain('Allow row decrease')
    expect(wrapper.text()).not.toContain('cardinality:')
  })

  it('shows explicit saved settings on the controls', async () => {
    const wrapper = mountDialog(
      makeContext({
        settings: makeSettings({
          join_type: { requested: 'left', source: 'explicit', effective: 'left' },
          allow_null_keys: { requested: true, source: 'explicit' },
          null_keys_equal: { requested: false, source: 'explicit' },
        }),
      })
    )
    await flushPromises()

    expect(wrapper.find('select[aria-label="Join type"]').attributes('data-selected')).toBe(JSON.stringify('left'))
    expect(wrapper.find('select[aria-label="Allow missing join keys"]').attributes('data-selected')).toBe('true')
    expect(wrapper.find('select[aria-label="Match null join-key parts"]').attributes('data-selected')).toBe('false')
    expect(wrapper.text()).toContain('Saved: left (explicit); effective left')
    expect(wrapper.text()).toContain('Allow missing join keys: yes (explicit)')
  })

  it('shows the entity pair from the warning metadata while the first request loads', async () => {
    mockOpen.mockImplementationOnce(() => new Promise<LinkExperimentContextResponse | null>(() => undefined))
    const wrapper = mountDialog()

    expect(wrapper.text()).toContain('orders → customers')
    expect(wrapper.text()).not.toContain('Unknown entity')
  })

  it('runs a trial only when requested and sends the current controls', async () => {
    const wrapper = mountDialog(makeContext({ configuredRemoteKeys: ['system_id'] }))
    await flushPromises()

    expect(openRequests[0]).toEqual({
      issue_type: 'row_count_mismatch',
      local_entity: 'orders',
      metadata: candidateMessage().metadata,
    })
    expect(wrapper.find('select[aria-label="Key pair 1 remote key (customers)"]').attributes('data-selected')).toBe(
      JSON.stringify('system_id')
    )
    expect(wrapper.text()).not.toContain('Run a trial to compare')

    await selectOption(wrapper, 'Join type', 'left')
    await selectOption(wrapper, 'Allow missing join keys', true)
    await selectOption(wrapper, 'Match null join-key parts', false)
    expect(runCalls).toHaveLength(0)

    await buttonByText(wrapper, 'Run trial')!.trigger('click')
    await flushPromises()

    expect(runCalls[0]).toEqual({
      local: ['saved_code'],
      remote: ['system_id'],
      how: 'left',
      allowNullKeys: true,
      nullKeysEqual: false,
    })
    // The completed trial becomes the shown result without a second request.
    expect(wrapper.find('button[data-side="trial"]').attributes('aria-pressed')).toBe('true')
    expect(statValue(wrapper, 'source_rows')).toBe('3')
    expect(statValue(wrapper, 'output_rows')).toBe('3')
  })

  it('keeps the previous trial result visible when trial settings change', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    await buttonByText(wrapper, 'Run trial')!.trigger('click')
    await flushPromises()
    await selectOption(wrapper, 'Join type', 'left')
    state.trialStale.value = true
    await nextTick()

    expect(wrapper.find('select[aria-label="Join type"]').attributes('data-selected')).toBe(JSON.stringify('left'))
    expect(wrapper.text()).toContain('Settings changed — rerun the trial.')

    // One result is shown at a time, so the stale trial stays on screen instead
    // of a second comparison table.
    expect(wrapper.find('section[aria-label="Baseline and trial comparison"]').exists()).toBe(false)
    expect(wrapper.find('button[data-side="trial"]').attributes('aria-pressed')).toBe('true')
    expect(statValue(wrapper, 'output_rows')).toBe('3')
  })

  it('makes no request when the result source, group, page size, or page changes', async () => {
    const makeRows = (prefix: string) =>
      Array.from({ length: 51 }, (_, index) => makeRow(index, [`${prefix}-${index}`]))
    const wrapper = mountDialog(
      makeContext({
        detail: makeDetail({
          unmatched: makeGroup({ total_count: 51, returned_count: 51, rows: makeRows('BASE') }),
        }),
      })
    )
    await flushPromises()

    nextTrial = makeComparison({
      detail: makeDetail({
        multiply_matched: makeGroup({ total_count: 51, returned_count: 51, rows: makeRows('TRIAL') }),
      }),
    })
    await buttonByText(wrapper, 'Run trial')!.trigger('click')
    await flushPromises()
    expect(runCalls).toHaveLength(1)

    await selectSide(wrapper, 'trial')
    await wrapper.find('button[data-group="multiply_matched"]').trigger('click')
    await selectOption(wrapper, 'Rows per page', 25)
    await wrapper.find('button[aria-label="Next page"]').trigger('click')
    await flushPromises()

    expect(runCalls).toHaveLength(1)
    expect(openRequests).toHaveLength(1)
  })

  it('renders bounded exception rows with full counts and truncation labels', async () => {
    const detail = makeDetail({
      detail_truncated: true,
      unmatched: makeGroup({
        total_count: 150,
        returned_count: 2,
        row_cap: 100,
        row_cap_reached: true,
        budget_exhausted: true,
        rows: [makeRow(4, [{ value: 'LONG', truncated: true, original_length: 12 }]), makeRow(5, ['MISSING'])],
      }),
    })
    const wrapper = mountDialog(makeContext({ detail }))
    await flushPromises()

    expect(wrapper.text()).toContain('Showing 2 of 2 returned rows; 150 affected source rows in total.')
    expect(wrapper.text()).toContain('Only the first 100 exception rows are returned.')
    expect(wrapper.text()).toContain('The response size limit stopped further exception rows.')
    expect(wrapper.text()).toContain('Some findings or key values in this response were shortened.')

    const section = wrapper.find('section[aria-label="Exception rows"]')
    const cells = section
      .findAll('tbody tr')[0]
      ?.findAll('td')
      .map((cell) => cell.text())
    expect(cells).toEqual(['5', 'LONG…', '0', '0'])
  })

  it('switches between baseline and trial exception groups locally', async () => {
    const wrapper = mountDialog(
      makeContext({
        detail: makeDetail({
          unmatched: makeGroup({ total_count: 2, returned_count: 2, rows: [makeRow(1, ['BASE'])] }),
          multiply_matched: makeGroup({ total_count: 1, returned_count: 1, rows: [makeRow(2, ['MULTI'])] }),
        }),
      })
    )
    await flushPromises()

    nextTrialKeys = { local: ['saved_code'], remote: ['saved_value'] }
    nextTrial = makeComparison({
      detail: makeDetail({
        unmatched: makeGroup({ total_count: 1, returned_count: 1, rows: [makeRow(4, ['TRIAL'])] }),
      }),
    })
    await buttonByText(wrapper, 'Run trial')!.trigger('click')
    await flushPromises()

    // A completed trial is shown immediately, so its rows replace the saved rows.
    expect(wrapper.find('section[aria-label="Exception rows"]').text()).toContain('TRIAL')
    expect(wrapper.find('section[aria-label="Exception rows"] tbody tr').text()).toContain('5')

    await selectSide(wrapper, 'baseline')
    expect(wrapper.find('section[aria-label="Exception rows"]').text()).toContain('BASE')

    await wrapper.find('button[data-group="multiply_matched"]').trigger('click')
    expect(wrapper.find('section[aria-label="Exception rows"]').text()).toContain('MULTI')

    await selectSide(wrapper, 'trial')
    await wrapper.find('button[data-group="unmatched"]').trigger('click')
    expect(wrapper.find('section[aria-label="Exception rows"]').text()).toContain('TRIAL')
  })

  it('resets exception pagination when filters or trial rows change', async () => {
    const makeRows = (prefix: string, start: number, count: number) =>
      Array.from({ length: count }, (_, index) => makeRow(start + index, [`${prefix}-${index + 1}`]))
    const wrapper = mountDialog(
      makeContext({
        detail: makeDetail({
          unmatched: makeGroup({ total_count: 26, returned_count: 26, rows: makeRows('BASE', 0, 26) }),
        }),
      })
    )
    await flushPromises()

    nextTrial = makeComparison({
      detail: makeDetail({
        unmatched: makeGroup({ total_count: 26, returned_count: 26, rows: makeRows('TRIAL', 50, 26) }),
        multiply_matched: makeGroup({
          total_count: 1,
          returned_count: 1,
          rows: [makeRow(80, ['TRIAL-MULTI'])],
        }),
      }),
    })
    await buttonByText(wrapper, 'Run trial')!.trigger('click')
    await flushPromises()

    const firstRowText = () => wrapper.find('section[aria-label="Exception rows"] tbody tr').text()
    const nextPage = wrapper.find('button[aria-label="Next page"]')

    // The completed trial is shown first; pagination checks start on the saved link.
    await selectSide(wrapper, 'baseline')

    await selectOption(wrapper, 'Rows per page', 25)
    await nextPage.trigger('click')
    expect(firstRowText()).toContain('BASE-26')

    await selectOption(wrapper, 'Rows per page', 50)
    expect(firstRowText()).toContain('BASE-1')

    await selectOption(wrapper, 'Rows per page', 25)
    await nextPage.trigger('click')
    expect(firstRowText()).toContain('BASE-26')

    await selectSide(wrapper, 'trial')
    expect(firstRowText()).toContain('TRIAL-1')
    await nextPage.trigger('click')
    expect(firstRowText()).toContain('TRIAL-26')

    await wrapper.find('button[data-group="multiply_matched"]').trigger('click')
    expect(firstRowText()).toContain('TRIAL-MULTI')
    await wrapper.find('button[data-group="unmatched"]').trigger('click')
    await nextPage.trigger('click')
    expect(firstRowText()).toContain('TRIAL-26')

    nextTrial = makeComparison({
      detail: makeDetail({
        unmatched: makeGroup({ total_count: 1, returned_count: 1, rows: [makeRow(99, ['TRIAL-SHORT'])] }),
      }),
    })
    await buttonByText(wrapper, 'Run trial')!.trigger('click')
    await flushPromises()

    expect(firstRowText()).toContain('TRIAL-SHORT')
  })

  it('resets to the retained baseline and original controls without running a trial', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    state.localKeys.value = ['system_id']
    await nextTick()

    await buttonByText(wrapper, 'Reset to saved')!.trigger('click')
    await flushPromises()

    expect(mockReset).toHaveBeenCalledTimes(1)
    expect(mockRun).not.toHaveBeenCalled()
    expect(wrapper.find('select[aria-label="Key pair 1 local key (orders)"]').attributes('data-selected')).toBe(
      JSON.stringify('saved_code')
    )
    expect(state.context.value?.context_id).toBe('context-1')
  })

  it('announces refreshed inputs after expiry', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    state.refreshed.value = true
    await nextTick()

    expect(wrapper.text()).toContain('The retained inputs expired and were reproduced again from current data.')
    expect(wrapper.text()).toContain('Run a new trial')
  })

  it('shows dashes and no guessed settings for an incomplete baseline', async () => {
    const wrapper = mountDialog(
      makeContext({ diagnosticStatus: 'incomplete', settings: null, constraints: { allow_row_decrease: true } })
    )
    await flushPromises()

    expect(wrapper.text()).toContain('This diagnostic has no resolved settings report.')
    expect(statValue(wrapper, 'source_rows')).toBe('—')
    expect(statValue(wrapper, 'output_rows')).toBe('—')
    expect(wrapper.find('select[aria-label="Allow missing join keys"]').attributes('data-selected')).toBe('null')
  })

  it('shows a failed trial alert without totals', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    nextTrial = makeComparison({
      status: 'failed',
      reason: 'invalid_keys',
      message: 'Trial details are unavailable.',
      totals: null,
      detail: null,
    })
    await buttonByText(wrapper, 'Run trial')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Trial failed:')
    expect(wrapper.text()).toContain('invalid_keys')
    // A failed trial has no totals, so the shown result reads as unavailable.
    expect(wrapper.find('button[data-side="trial"]').attributes('aria-pressed')).toBe('true')
    expect(statValue(wrapper, 'source_rows')).toBe('—')
    expect(statValue(wrapper, 'output_rows')).toBe('—')
  })

  it.each(['not_reproduced', 'ineligible'] as const)('hides trial controls for a %s baseline', async (status) => {
    const wrapper = mountDialog(makeContext({ status, contextId: null }))
    await flushPromises()

    expect(wrapper.text()).toContain(status)
    expect(wrapper.text()).toContain('The warning is stale.')
    expect(wrapper.find('select[aria-label="A key"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Run trial')
  })

  it('shows a local message and makes no request for a non-candidate warning', async () => {
    const wrapper = mountDialog(makeContext(), candidateMessage({ code: 'OTHER_WARNING' }))
    await flushPromises()

    expect(wrapper.text()).toContain('This warning cannot be troubleshot.')
    expect(openRequests).toHaveLength(0)
  })

  it('opens the read-only integrity body without sending a row-count request', async () => {
    const wrapper = mountDialog(makeContext(), integrityMessage())
    await flushPromises()

    expect(openRequests).toHaveLength(0)
    expect(mockOpen).not.toHaveBeenCalled()
    expect(mockClose).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Complete distinct unmatched value count: 1')
    expect(wrapper.text()).toContain('orders → customers')
    expect(wrapper.find('select[aria-label="A key"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Run trial')
    expect(wrapper.text()).not.toContain('Trial key pairs')
  })

  it('explains a malformed integrity warning without sending either request', async () => {
    const wrapper = mountDialog(
      makeContext(),
      integrityMessage({ metadata: { fk_signature: 'saved-signature', orphan_count: 2 } })
    )
    await flushPromises()

    expect(wrapper.text()).toContain('does not record which saved link')
    expect(openRequests).toHaveLength(0)
    expect(vi.mocked(integrityTroubleshooterApi.inspect)).not.toHaveBeenCalled()
  })

  it('releases the row-count context when switching to an integrity warning', async () => {
    const wrapper = mountDialog()
    await flushPromises()
    expect(openRequests).toHaveLength(1)

    await wrapper.setProps({ message: integrityMessage() })
    await flushPromises()

    expect(openRequests).toHaveLength(1)
    expect(mockClose).toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('Trial key pairs')
    expect(wrapper.text()).toContain('Complete distinct unmatched value count: 1')
  })

  it('clears state and releases the context when the dialog closes', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    await buttonByText(wrapper, 'Close')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false])

    await wrapper.setProps({ modelValue: false })
    await flushPromises()

    expect(mockClose).toHaveBeenCalledTimes(1)
    expect(state.context.value).toBeNull()
    expect(state.localKeys.value).toEqual([])
  })
})
