import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import IntegrityTroubleshooterBody from '../IntegrityTroubleshooterBody.vue'
import { integrityTroubleshooterApi } from '@/api/integrityTroubleshooter'
import type { IntegrityTroubleshootRequest, IntegrityTroubleshootResponse, ValidationError } from '@/types'

vi.mock('@/api/integrityTroubleshooter', () => ({
  integrityTroubleshooterApi: { inspect: vi.fn() },
}))

const vuetify = createVuetify({ components, directives })

const requests: IntegrityTroubleshootRequest[] = []
const inspect = () => vi.mocked(integrityTroubleshooterApi.inspect)

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
      page: 1,
      page_size: 50,
      distinct_value_count: 2,
      returned_value_count: 2,
      has_next: false,
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
    returned_row_count: 1,
    columns: ['customer_code', 'name'],
    columns_truncated: false,
    rows: [{ customer_code: 'MISSING-A', name: 'Orphan order' }],
    ...overrides,
  }
}

/** Queue one recorded response per inspection request, in call order. */
function queueResponses(...responses: IntegrityTroubleshootResponse[]): void {
  for (const value of responses) {
    inspect().mockImplementationOnce(async (_projectName, request) => {
      requests.push(request)
      return value
    })
  }
}

function mountBody(message: ValidationError = warning()) {
  return mount(IntegrityTroubleshooterBody, {
    props: { projectName: 'project-a', message },
    global: {
      plugins: [vuetify],
      stubs: {
        VPagination: {
          props: ['length', 'modelValue'],
          emits: ['update:modelValue'],
          template: `<button type="button" aria-label="Next page" @click="$emit('update:modelValue', modelValue + 1)">Next page</button>`,
        },
      },
    },
  })
}

describe('IntegrityTroubleshooterBody', () => {
  beforeEach(() => {
    requests.length = 0
    inspect().mockReset()
    queueResponses(response())
  })

  it('opens page one with the unchanged warning identity and shows current inspected data', async () => {
    const wrapper = mountBody()
    await flushPromises()

    expect(requests[0]).toEqual({
      issue_type: 'FK_DATA_INTEGRITY',
      local_entity: 'orders',
      metadata: { fk_index: 0, fk_signature: 'saved-signature', orphan_count: 2 },
      page: 1,
    })
    expect(wrapper.text()).toContain('reproduced')
    expect(wrapper.text()).toContain('current full normalization')
    expect(wrapper.text()).toContain('current data, not the saved warning')
    expect(wrapper.text()).toContain('Complete distinct unmatched count: 2')
    expect(wrapper.text()).toContain('Returned on this page: 2')
    expect(wrapper.text()).toContain('A: orders')
    expect(wrapper.text()).toContain('B: customers')
    expect(wrapper.text()).toContain('A: customer_code')
    expect(wrapper.text()).toContain('B: code')
    expect(wrapper.text()).toContain('MISSING-A')
    expect(wrapper.text()).toContain('allow_row_decrease: true')
  })

  it('separates the recorded warning count from the current count', async () => {
    inspect().mockReset()
    queueResponses(response({ status: 'not_reproduced', reason: 'count_changed', current_orphan_count: 5 }))

    const wrapper = mountBody()
    await flushPromises()

    const rows = wrapper.findAll('section[aria-label="Unmatched value counts"] tbody tr')
    expect(rows[0]?.findAll('td')[1]?.text()).toBe('2')
    expect(rows[1]?.findAll('td')[1]?.text()).toBe('5')
    expect(wrapper.text()).toContain('count_changed')
    // Current values stay visible because the current data still has unmatched values.
    expect(wrapper.find('section[aria-label="Unmatched values"]').exists()).toBe(true)
  })

  it('shows the backend refusal for a stale saved link without value controls', async () => {
    inspect().mockReset()
    queueResponses(
      response({
        status: 'ineligible',
        reason: 'signature_mismatch',
        message: 'The warning does not resolve to one saved link (signature_mismatch)',
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
    expect(wrapper.find('.integrity-select-value').exists()).toBe(false)
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
          page: 1,
          page_size: 50,
          distinct_value_count: 1,
          returned_value_count: 1,
          has_next: false,
          values: [{ key_values: [null, 'X-1'], local_row_count: 2, token: 'token-composite' }],
        },
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    expect(wrapper.find('section[aria-label="Unmatched values"] tbody tr').text()).toContain('—, X-1')
  })

  it('renders one unmatched-value row per value with its local row count', async () => {
    const wrapper = mountBody()
    await flushPromises()

    const section = wrapper.find('section[aria-label="Unmatched values"]')
    expect(section.find('thead').text()).toContain('Unmatched key')
    expect(section.find('thead').text()).toContain('Local rows')

    const rows = section.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0]?.findAll('td').map((cell) => cell.text())).toEqual(['MISSING-A', '1', 'Show local rows'])
    expect(rows[1]?.findAll('td').map((cell) => cell.text())).toEqual(['MISSING-B', '3', 'Show local rows'])
    expect(section.findAll('.integrity-select-value')).toHaveLength(2)
  })

  it('pages with the current page number and clears the selection', async () => {
    inspect().mockReset()
    queueResponses(
      response({
        values: {
          page: 1,
          page_size: 50,
          distinct_value_count: 120,
          returned_value_count: 1,
          has_next: true,
          values: [{ key_values: ['MISSING-A'], local_row_count: 1, token: 'token-a' }],
        },
        selected: selectedRows(),
      }),
      response({
        values: {
          page: 2,
          page_size: 50,
          distinct_value_count: 120,
          returned_value_count: 0,
          has_next: true,
          values: [],
        },
        selected: null,
      })
    )

    const wrapper = mountBody()
    await flushPromises()
    expect(wrapper.find('section[aria-label="Selected value rows"]').exists()).toBe(true)

    await wrapper.find('button[aria-label="Next page"]').trigger('click')
    await flushPromises()

    expect(requests[1]).toEqual({
      issue_type: 'FK_DATA_INTEGRITY',
      local_entity: 'orders',
      metadata: { fk_index: 0, fk_signature: 'saved-signature', orphan_count: 2 },
      page: 2,
    })
    expect(wrapper.text()).toContain('No unmatched values on this page.')
    expect(wrapper.find('section[aria-label="Selected value rows"]').exists()).toBe(false)
  })

  it('selects a value with its server token on the current page', async () => {
    inspect().mockReset()
    queueResponses(
      response({
        values: {
          page: 1,
          page_size: 50,
          distinct_value_count: 120,
          returned_value_count: 1,
          has_next: true,
          values: [{ key_values: ['MISSING-A'], local_row_count: 1, token: 'token-a' }],
        },
      }),
      response({
        values: {
          page: 2,
          page_size: 50,
          distinct_value_count: 120,
          returned_value_count: 1,
          has_next: true,
          values: [{ key_values: ['MISSING-Z'], local_row_count: 1, token: 'token-z' }],
        },
      }),
      response({
        values: {
          page: 2,
          page_size: 50,
          distinct_value_count: 120,
          returned_value_count: 1,
          has_next: true,
          values: [{ key_values: ['MISSING-Z'], local_row_count: 1, token: 'token-z' }],
        },
        selected: selectedRows({ key_values: ['MISSING-Z'], rows: [{ customer_code: 'MISSING-Z', name: 'Z' }] }),
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    await wrapper.find('button[aria-label="Next page"]').trigger('click')
    await flushPromises()
    expect(requests[1]?.page).toBe(2)

    await wrapper.find('.integrity-select-value').trigger('click')
    await flushPromises()

    expect(requests[2]).toEqual({
      issue_type: 'FK_DATA_INTEGRITY',
      local_entity: 'orders',
      metadata: { fk_index: 0, fk_signature: 'saved-signature', orphan_count: 2 },
      page: 2,
      selected_value_token: 'token-z',
    })
  })

  it('shows bounded rows with named columns and the truncation notice', async () => {
    inspect().mockReset()
    const rows = Array.from({ length: 20 }, (_, index) => ({
      customer_code: `MISSING-${index}`,
      name: `Row ${index}`,
    }))
    queueResponses(
      response({
        selected: selectedRows({
          total_row_count: 40,
          returned_row_count: 20,
          columns: ['customer_code', 'name'],
          columns_truncated: true,
          rows,
        }),
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    const section = wrapper.find('section[aria-label="Selected value rows"]')
    expect(section.text()).toContain('Complete matching local rows: 40')
    expect(section.text()).toContain('Returned rows: 20')
    expect(section.text()).toContain('Only the first 2 columns are shown.')
    expect(section.find('thead').text()).toContain('customer_code')
    expect(section.findAll('tbody tr')).toHaveLength(20)
    // Only response-provided columns are rendered.
    expect(section.find('thead').text()).not.toContain('system_id')
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
          returned_row_count: null,
          columns: [],
          rows: [],
        }),
      })
    )

    const wrapper = mountBody()
    await flushPromises()

    const section = wrapper.find('section[aria-label="Selected value rows"]')
    expect(section.find('.integrity-selection-unavailable').text()).toContain('value_no_longer_unmatched')
    expect(section.find('table').exists()).toBe(false)
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
        return response({ message: 'Second warning inspected.' })
      })

    const wrapper = mountBody()
    await wrapper.setProps({ message: warning({ message: 'Second integrity warning' }) })
    await flushPromises()

    resolveFirst?.(response({ message: 'First warning inspected.' }))
    await flushPromises()

    expect(wrapper.text()).toContain('Second warning inspected.')
    expect(wrapper.text()).not.toContain('First warning inspected.')
  })
})
