import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import IntegrityTroubleshooterBody from '../IntegrityTroubleshooterBody.vue'
import { integrityTroubleshooterApi } from '@/api/integrityTroubleshooter'
import type {
  IntegrityTroubleshootPageRequest,
  IntegrityTroubleshootRequest,
  IntegrityTroubleshootResponse,
  ValidationError,
} from '@/types'
import { downloadCsv } from '@/utils/csv'

vi.mock('@/api/integrityTroubleshooter', () => ({
  integrityTroubleshooterApi: { inspect: vi.fn(), page: vi.fn(), close: vi.fn() },
}))

// Keep the real CSV building so the test asserts the exported text, and replace
// only the browser download, which jsdom cannot observe.
vi.mock('@/utils/csv', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/utils/csv')>()
  return { ...actual, downloadCsv: vi.fn() }
})

const vuetify = createVuetify({ components, directives })

// The real grid renders rows through AG Grid, which does not run in jsdom.
// This stub keeps the same read-only contract: columns, rows, and row clicks.
const TroubleshooterDataGridStub = defineComponent({
  name: 'TroubleshooterDataGrid',
  props: {
    columns: { type: Array, required: true },
    rows: { type: Array, required: true },
    height: { type: String, default: '320px' },
    loading: { type: Boolean, default: false },
    selectable: { type: Boolean, default: false },
  },
  emits: ['row-click'],
  template: `
    <div data-testid="grid-stub">
      <div class="grid-header">
        <span v-for="column in columns" :key="column.field">{{ column.header }}</span>
      </div>
      <button
        v-for="(row, index) in rows"
        :key="index"
        type="button"
        class="grid-row"
        :data-row="index"
        @click="$emit('row-click', row)"
      >
        <span v-for="column in columns" :key="column.field">{{ row[column.field] }}</span>
      </button>
    </div>
  `,
})

const requests: IntegrityTroubleshootRequest[] = []
const pageRequests: IntegrityTroubleshootPageRequest[] = []
const inspect = () => vi.mocked(integrityTroubleshooterApi.inspect)
const readPage = () => vi.mocked(integrityTroubleshooterApi.page)
const close = () => vi.mocked(integrityTroubleshooterApi.close)

function warning(overrides: Partial<ValidationError> = {}): ValidationError {
  return {
    severity: 'warning',
    entity: 'orders',
    message: "2 foreign key value(s) not found in 'customers'",
    code: 'FK_DATA_INTEGRITY',
    metadata: { fk_index: 0, fk_signature: 'saved-signature', orphan_count: 2 },
    ...overrides,
  }
}

function response(overrides: Partial<IntegrityTroubleshootResponse> = {}): IntegrityTroubleshootResponse {
  return {
    status: 'reproduced',
    reason: 'reproduced',
    message: 'The current full-data unmatched count matches the warning.',
    source: 'current full normalization',
    context_id: 'context-one',
    expires_at: '2026-01-01T00:15:00Z',
    relationship: {
      local_entity: 'orders',
      remote_entity: 'customers',
      fk_index: 0,
      join_type: 'inner',
      constraints: { allow_row_decrease: true },
    },
    configured_keys: { local_keys: ['customer_code'], remote_keys: ['code'] },
    recorded_orphan_count: 2,
    current_orphan_count: 2,
    values: {
      distinct_value_count: 2,
      values: [
        { key_values: ['MISSING-A'], local_row_count: 1, token: 'token-a' },
        { key_values: ['MISSING-B'], local_row_count: 3, token: 'token-b' },
      ],
    },
    selected: null,
    ...overrides,
  }
}

type SelectedRows = NonNullable<IntegrityTroubleshootResponse['selected']>

function selectedRows(overrides: Partial<SelectedRows> = {}): SelectedRows {
  return {
    status: 'selected',
    reason: null,
    message: null,
    key_values: ['MISSING-A'],
    total_row_count: 1,
    columns: ['customer_code', 'name'],
    columns_truncated: false,
    rows: [{ customer_code: 'MISSING-A', name: 'Orphan order' }],
    ...overrides,
  }
}

/** Queue one response per inspection or page request, in call order. */
function queueResponses(...responses: IntegrityTroubleshootResponse[]): void {
  const queuedResponses = [...responses]
  const takeResponse = (): IntegrityTroubleshootResponse => {
    const value = queuedResponses.shift()
    if (!value) {
      throw new Error('No integrity troubleshooter response was queued')
    }
    return value
  }
  inspect().mockImplementation(async (_projectName, request) => {
    requests.push(request)
    return takeResponse()
  })
  readPage().mockImplementation(async (_projectName, _contextId, request) => {
    pageRequests.push(request)
    return takeResponse()
  })
}

function mountBody(message: ValidationError = warning()) {
  return mount(IntegrityTroubleshooterBody, {
    props: { projectName: 'project-a', message },
    global: {
      plugins: [vuetify],
      stubs: {
        TroubleshooterDataGrid: TroubleshooterDataGridStub,
        VTooltip: {
          template: '<div data-testid="tooltip"><slot name="activator" :props="{}" /><slot /></div>',
        },
      },
    },
  })
}

describe('IntegrityTroubleshooterBody', () => {
  beforeEach(() => {
    requests.length = 0
    pageRequests.length = 0
    inspect().mockReset()
    readPage().mockReset()
    close().mockReset()
    close().mockResolvedValue(undefined)
    vi.mocked(downloadCsv).mockReset()
    queueResponses(response())
  })

  it('opens the inspection with the unchanged warning identity and shows current inspected data', async () => {
    const wrapper = mountBody()
    await flushPromises()

    expect(requests[0]).toEqual({
      issue_type: 'FK_DATA_INTEGRITY',
      local_entity: 'orders',
      metadata: { fk_index: 0, fk_signature: 'saved-signature', orphan_count: 2 },
    })
    expect(wrapper.find('[data-stat="recorded"] .integrity-finding-stat-value').text()).toBe('2')
    expect(wrapper.find('[data-stat="current"] .integrity-finding-stat-value').text()).toBe('2')
    expect(wrapper.find('button[aria-label="About integrity counts"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tooltip"]').text()).toContain('recorded count comes from the validation warning')
    const keyPairs = wrapper.find('section[aria-label="Configured keys"]')
    expect(keyPairs.text()).toContain('customer_code')
    expect(keyPairs.text()).toContain('code')
    expect(wrapper.text()).toContain('MISSING-A')
    expect(wrapper.find('section[aria-label="Configured relationship"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Configured link rules')
    expect(wrapper.text()).not.toContain('allow_row_decrease: true')
    expect(wrapper.emitted('relationship')).toEqual([[response().relationship]])
    // A reproduced warning is the expected outcome, so it gets no status banner.
    expect(wrapper.find('.integrity-status').exists()).toBe(false)
  })

  it('tells the user that the link is re-read from current data while it loads', async () => {
    inspect().mockReset()
    inspect().mockImplementationOnce(() => new Promise<IntegrityTroubleshootResponse>(() => undefined))

    const wrapper = mountBody()
    await flushPromises()

    expect(wrapper.find('.integrity-loading').text()).toContain('current data')
    expect(wrapper.text()).not.toContain('Inspected data source')
  })

  it('keeps the existing rows visible while a selected value loads', async () => {
    inspect().mockReset()
    readPage().mockReset()
    const firstRows = Array.from({ length: 100 }, (_, index) => ({
      customer_code: `MISSING-${index}`,
      name: `Row ${index}`,
    }))
    const nextRows = Array.from({ length: 100 }, (_, index) => ({
      customer_code: `OTHER-${index}`,
      name: `Row ${index + 100}`,
    }))
    let resolvePage: ((value: IntegrityTroubleshootResponse) => void) | undefined
    inspect().mockResolvedValue(
      response({
        selected: selectedRows({ total_row_count: 250, rows: firstRows }),
      })
    )
    readPage().mockImplementationOnce(async (_projectName, _contextId, request) => {
      pageRequests.push(request)
      return new Promise<IntegrityTroubleshootResponse>((resolve) => {
        resolvePage = resolve
      })
    })

    const wrapper = mountBody()
    await flushPromises()
    await wrapper.find('section[aria-label="Unmatched values"] .grid-row').trigger('click')
    await flushPromises()

    expect(wrapper.find('.integrity-page-loading').exists()).toBe(true)
    expect(wrapper.find('section[aria-label="Selected value rows"] .grid-row').text()).toContain('MISSING-0')
    expect(inspect()).toHaveBeenCalledTimes(1)
    expect(pageRequests).toEqual([{ selected_value_token: 'token-a' }])

    resolvePage?.(
      response({
        selected: selectedRows({
          total_row_count: 250,
          rows: nextRows,
        }),
      })
    )
    await flushPromises()

    expect(wrapper.find('.integrity-page-loading').exists()).toBe(false)
    expect(wrapper.find('section[aria-label="Selected value rows"] .grid-row').text()).toContain('OTHER-0')
    expect(inspect()).toHaveBeenCalledTimes(1)
  })

  it('compares recorded and current unmatched counts in separate cards', async () => {
    inspect().mockReset()
    queueResponses(response({ status: 'not_reproduced', reason: 'count_changed', current_orphan_count: 5 }))

    const wrapper = mountBody()
    await flushPromises()

    expect(wrapper.find('[data-stat="recorded"] .integrity-finding-stat-value').text()).toBe('2')
    expect(wrapper.find('[data-stat="current"] .integrity-finding-stat-value').text()).toBe('5')
    expect(wrapper.find('section[aria-label="Unmatched value counts"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('count_changed')
    expect(wrapper.text()).toContain('Count changed')
    // Current values stay visible because the current data still has unmatched values.
    expect(wrapper.find('section[aria-label="Unmatched values"]').exists()).toBe(true)
  })

  it('shows the backend refusal for a stale configured link without value controls', async () => {
    inspect().mockReset()
    queueResponses(
      response({
        status: 'ineligible',
        reason: 'signature_mismatch',
        message: 'The warning does not resolve to one configured link (signature_mismatch)',
        relationship: {
          local_entity: 'orders',
          remote_entity: null,
          fk_index: 0,
          join_type: null,
          constraints: {},
        },
        configured_keys: null,
        recorded_orphan_count: null,
        current_orphan_count: null,
        values: null,
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    expect(wrapper.text()).toContain('ineligible')
    expect(wrapper.text()).toContain('signature_mismatch')
    expect(wrapper.find('section[aria-label="Unmatched values"]').exists()).toBe(false)
  })

  it('shows a named non-reproduction reason without fabricating values', async () => {
    inspect().mockReset()
    queueResponses(
      response({
        status: 'not_reproduced',
        reason: 'normalization_failed',
        message: 'Full normalization did not finish.',
        current_orphan_count: null,
        values: null,
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    expect(wrapper.find('.integrity-status').exists()).toBe(true)
    expect(wrapper.text()).toContain('not_reproduced')
    expect(wrapper.text()).toContain('normalization_failed')
    expect(wrapper.text()).toContain('Full normalization did not finish.')
    expect(wrapper.find('section[aria-label="Unmatched values"]').exists()).toBe(false)
  })

  it('renders composite and null key values without inventing a value', async () => {
    inspect().mockReset()
    queueResponses(
      response({
        values: {
          distinct_value_count: 1,
          values: [{ key_values: [null, 'X-1'], local_row_count: 2, token: 'token-composite' }],
        },
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    expect(wrapper.find('section[aria-label="Unmatched values"] .grid-row').text()).toContain('—, X-1')
  })

  it('renders one unmatched-value row per value with its local row count', async () => {
    const wrapper = mountBody()
    await flushPromises()

    const section = wrapper.find('section[aria-label="Unmatched values"]')
    expect(section.find('.grid-header').text()).toContain('Unmatched key')
    expect(section.find('.grid-header').text()).toContain('Local rows')

    const rows = section.findAll('.grid-row')
    expect(rows).toHaveLength(2)
    expect(rows[0]?.text()).toBe('MISSING-A1')
    expect(rows[1]?.text()).toBe('MISSING-B3')
  })

  it('places both result grids side by side in one row', async () => {
    inspect().mockReset()
    queueResponses(response(), response({ selected: selectedRows() }))

    const wrapper = mountBody()
    await flushPromises()
    await wrapper.find('section[aria-label="Unmatched values"] .grid-row').trigger('click')
    await flushPromises()

    const panels = wrapper.find('.integrity-result-panels')
    expect(panels.exists()).toBe(true)
    const sections = panels.findAll(':scope > section')
    expect(sections.map((section) => section.attributes('aria-label'))).toEqual([
      'Unmatched values',
      'Selected value rows',
    ])
    // Both grids use the same fixed height now that they share one row.
    const grids = wrapper.findAllComponents(TroubleshooterDataGridStub)
    expect(grids).toHaveLength(2)
    for (const grid of grids) {
      expect(grid.props('height')).toBe('320px')
    }
  })

  it('exports every unmatched key to CSV with configured key names as columns', async () => {
    const wrapper = mountBody()
    await flushPromises()

    const exportButton = wrapper.findAll('button').find((button) => button.text().includes('Export unmatched keys'))
    expect(exportButton).toBeDefined()

    await exportButton!.trigger('click')

    expect(downloadCsv).toHaveBeenCalledTimes(1)
    const [filename, content] = vi.mocked(downloadCsv).mock.calls[0] ?? []
    expect(filename).toMatch(/^orders_unmatched_keys_\d+\.csv$/)
    expect(content).toBe('customer_code,Local rows\r\nMISSING-A,1\r\nMISSING-B,3')
  })

  it('splits a composite key into one CSV column per key part', async () => {
    inspect().mockReset()
    queueResponses(
      response({
        configured_keys: { local_keys: ['site_code', 'sample_code'], remote_keys: ['code'] },
        values: {
          distinct_value_count: 1,
          values: [{ key_values: ['S-1', null], local_row_count: 4, token: 'token-composite' }],
        },
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    const exportButton = wrapper.findAll('button').find((button) => button.text().includes('Export unmatched keys'))
    await exportButton!.trigger('click')

    const [, content] = vi.mocked(downloadCsv).mock.calls[0] ?? []
    expect(content).toBe('site_code,sample_code,Local rows\r\nS-1,,4')
  })

  it('offers no export when the current data has no unmatched values', async () => {
    inspect().mockReset()
    queueResponses(response({ values: { distinct_value_count: 0, values: [] } }))

    const wrapper = mountBody()
    await flushPromises()

    expect(wrapper.findAll('button').some((button) => button.text().includes('Export unmatched keys'))).toBe(false)
  })

  it('shows an explicit empty state when the current data has no unmatched values', async () => {
    inspect().mockReset()
    queueResponses(response({ values: { distinct_value_count: 0, values: [] } }))

    const wrapper = mountBody()
    await flushPromises()

    expect(wrapper.text()).toContain('No unmatched values in the current data.')
    expect(wrapper.find('section[aria-label="Unmatched values"] .grid-row').exists()).toBe(false)
  })

  it('selects a value with its server token and reads the retained context', async () => {
    inspect().mockReset()
    queueResponses(response(), response({ selected: selectedRows() }))

    const wrapper = mountBody()
    await flushPromises()

    await wrapper.find('section[aria-label="Unmatched values"] .grid-row').trigger('click')
    await flushPromises()

    expect(pageRequests).toEqual([{ selected_value_token: 'token-a' }])
    expect(wrapper.find('section[aria-label="Selected value rows"]').exists()).toBe(true)
    expect(requests).toHaveLength(1)
  })

  it('shows every local row with named columns and the truncation notice', async () => {
    inspect().mockReset()
    const rows = Array.from({ length: 20 }, (_, index) => ({
      customer_code: `MISSING-${index}`,
      name: `Row ${index}`,
    }))
    queueResponses(
      response({
        selected: selectedRows({
          total_row_count: 40,
          columns: ['customer_code', 'name'],
          columns_truncated: true,
          rows,
        }),
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    const section = wrapper.find('section[aria-label="Selected value rows"]')
    // The heading alone introduces the rows; the key and row count are not repeated.
    expect(section.find('h3').text()).toBe('Affected local rows')
    expect(section.text()).not.toContain('Unmatched key:')
    expect(section.text()).not.toContain('local rows use this key')
    expect(section.text()).toContain('Only the first 2 columns are shown.')
    expect(section.find('.grid-header').text()).toContain('customer_code')
    expect(section.findAll('.grid-row')).toHaveLength(20)
    // Only response-provided columns are rendered.
    expect(section.find('.grid-header').text()).not.toContain('system_id')
  })

  it('lists every affected local row for a selected value without paging controls', async () => {
    inspect().mockReset()
    const rows = Array.from({ length: 2_000 }, (_, index) => ({
      customer_code: `MISSING-${index}`,
      name: `Row ${index}`,
    }))
    queueResponses(response(), response({ selected: selectedRows({ total_row_count: 10_000, rows }) }))

    const wrapper = mountBody()
    await flushPromises()
    await wrapper.find('section[aria-label="Unmatched values"] .grid-row').trigger('click')
    await flushPromises()

    const section = wrapper.find('section[aria-label="Selected value rows"]')
    expect(section.findAll('.grid-row')).toHaveLength(2_000)
    expect(wrapper.find('button[aria-label="Next rows page"]').exists()).toBe(false)
    expect(wrapper.find('button[aria-label="Previous rows page"]').exists()).toBe(false)
  })

  it('reopens the inspection once when its page context expires', async () => {
    inspect().mockReset()
    readPage().mockReset()
    inspect()
      .mockResolvedValueOnce(response())
      .mockResolvedValueOnce(response({ selected: selectedRows() }))
    readPage().mockRejectedValueOnce({
      response: { status: 410, data: { detail: { reason: 'context_expired' } } },
    })

    const wrapper = mountBody()
    await flushPromises()
    await wrapper.find('section[aria-label="Unmatched values"] .grid-row').trigger('click')
    await flushPromises()

    expect(inspect()).toHaveBeenCalledTimes(2)
    expect(readPage()).toHaveBeenCalledTimes(1)
    expect(inspect().mock.calls[1]?.[1].selected_value_token).toBe('token-a')
    expect(wrapper.find('section[aria-label="Selected value rows"]').exists()).toBe(true)
  })

  it('shows the refusal when the selected value is no longer unmatched', async () => {
    inspect().mockReset()
    queueResponses(
      response({
        selected: selectedRows({
          status: 'unavailable',
          reason: 'value_no_longer_unmatched',
          message: 'The selected value no longer appears as an unmatched value in the current data.',
          total_row_count: null,
          columns: [],
          rows: [],
        }),
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    const section = wrapper.find('section[aria-label="Selected value rows"]')
    expect(section.find('.integrity-selection-unavailable').text()).toContain('value_no_longer_unmatched')
    expect(section.find('.grid-row').exists()).toBe(false)
  })

  it('surfaces a request failure instead of stale results', async () => {
    inspect().mockReset()
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    inspect().mockRejectedValue(new Error('Integrity inspection failed'))

    const wrapper = mountBody()
    await flushPromises()

    expect(wrapper.text()).toContain('Integrity inspection failed')
    expect(wrapper.find('section[aria-label="Unmatched values"]').exists()).toBe(false)
    expect(consoleError).toHaveBeenCalled()
    consoleError.mockRestore()
  })

  it('ignores a late response after the inspected warning changes', async () => {
    inspect().mockReset()
    let resolveFirst: ((value: IntegrityTroubleshootResponse) => void) | undefined
    const firstPromise = new Promise<IntegrityTroubleshootResponse>((resolve) => {
      resolveFirst = resolve
    })
    inspect()
      .mockImplementationOnce(async (_projectName, request) => {
        requests.push(request)
        return firstPromise
      })
      .mockImplementationOnce(async (_projectName, request) => {
        requests.push(request)
        return response({ status: 'not_reproduced', reason: 'second_response', message: 'Second warning inspected.' })
      })

    const wrapper = mountBody()
    await wrapper.setProps({ message: warning({ message: 'Second integrity warning' }) })
    await flushPromises()

    resolveFirst?.(
      response({ status: 'not_reproduced', reason: 'first_response', message: 'First warning inspected.' })
    )
    await flushPromises()

    expect(wrapper.text()).toContain('Second warning inspected.')
    expect(wrapper.text()).not.toContain('First warning inspected.')
  })
})
