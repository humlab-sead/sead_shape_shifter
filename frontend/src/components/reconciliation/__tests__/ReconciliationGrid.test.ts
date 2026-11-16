import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import type { ColDef } from 'ag-grid-community'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import type { MappingEntityResponse, ReconciliationCandidate, ReconciliationPreviewRow } from '@/types'

vi.mock('ag-grid-vue3', () => ({
  AgGridVue: {
    name: 'AgGridVue',
    props: ['rowData', 'columnDefs', 'rowHeight'],
    template: `
      <div data-testid="grid-stub">
        <div data-testid="grid-columns">{{ columnDefs.map(column => column.headerName).join('|') }}</div>
        <div data-testid="grid-row-height">{{ rowHeight }}</div>
        <div v-for="row in rowData.slice().reverse()" :key="row.local_key_value" data-testid="grid-row">
          <span data-testid="row-class">{{ row.row_style_class }}</span>
          <span data-testid="row-status">{{ row.status_display }}</span>
          <span data-testid="row-confidence">{{ row.confidence_percent == null ? '' : Math.round(row.confidence_percent) + '%' }}</span>
          <span data-testid="row-errors">{{ row.errors_display || '—' }}</span>
          <span data-testid="current-id" :data-key="row.local_key_value">{{ row.current_id ?? '' }}</span>
          <span data-testid="current-id-source" :data-key="row.local_key_value">{{ row.current_id_source_label }}</span>
          <button :data-local-key="row.local_key_value" data-action="reject" aria-label="Reject this row"><span class="mdi mdi-close-circle-outline" aria-hidden="true"></span></button>
          <button :data-local-key="row.local_key_value" data-action="review">Review</button>
          <button :data-local-key="row.local_key_value" data-action="search" aria-label="Search for another candidate"><span class="mdi mdi-magnify" aria-hidden="true"></span></button>
          <button :data-local-key="row.local_key_value" data-action="local-only" aria-label="Mark this row as New"><span class="mdi mdi-plus-circle-outline" aria-hidden="true"></span></button>
          <button :data-local-key="row.local_key_value" data-action="manual-link" aria-label="Add a manual link for this row"><span class="mdi mdi-link-variant" aria-hidden="true"></span></button>
        </div>
      </div>
    `,
  },
}))

import ReconciliationGrid from '../ReconciliationGrid.vue'
import AlternativeSearchDialog from '../AlternativeSearchDialog.vue'
import PreviewMatchedDataDialog from '../PreviewMatchedDataDialog.vue'
import { RECONCILIATION_ACTION_ICONS } from '../reconciliationHelp'

const passthrough = (tag: string) =>
  defineComponent({
    inheritAttrs: false,
    setup(_props, { attrs, slots }) {
      return () => h(tag, attrs, slots.default?.())
    },
  })

const listItemStub = defineComponent({
  inheritAttrs: false,
  setup(_props, { attrs, slots }) {
    return () => h('div', attrs, [slots.prepend?.(), slots.default?.(), slots.append?.()])
  },
})

const stubs = {
  VToolbar: passthrough('div'),
  VChipGroup: passthrough('div'),
  VChip: passthrough('span'),
  VSpacer: passthrough('span'),
  VTextField: passthrough('input'),
  VBtn: passthrough('button'),
  VAlert: passthrough('div'),
  VDialog: passthrough('div'),
  VCard: passthrough('div'),
  VCardTitle: passthrough('div'),
  VCardSubtitle: passthrough('div'),
  VCardText: passthrough('div'),
  VCardActions: passthrough('div'),
  VList: passthrough('div'),
  VListItem: listItemStub,
  VListItemTitle: passthrough('div'),
  VListItemSubtitle: passthrough('div'),
  VAvatar: passthrough('span'),
  VTextarea: passthrough('textarea'),
  VIcon: passthrough('span'),
  VDivider: passthrough('hr'),
  VSwitch: passthrough('input'),
  VTable: passthrough('table'),
}

const vuetify = createVuetify({ components, directives })

function makeRow(localKeyValue: string) {
  return {
    local_key_value: localKeyValue,
    site_name: 'Same',
    status: 'proposed' as const,
    candidates: [
      { id: 'https://w3id.org/sead/id/site/101', name: 'Zero score', score: 0, type: [] },
      { id: 'https://w3id.org/sead/id/site/102', name: 'Review score', score: 82, type: [] },
      { id: 'https://w3id.org/sead/id/site/103', name: 'High score', score: 100, type: [] },
    ],
  }
}

function mountGrid(
  submitDecision = vi.fn().mockResolvedValue(undefined),
  previewData: ReconciliationPreviewRow[] = [makeRow('A')],
  mappingData: MappingEntityResponse | null = null
) {
  const row = previewData[0]!
  const wrapper = mount(ReconciliationGrid, {
    props: {
      entitySpec: {
        source: null,
        property_mappings: {},
        remote: { service_type: 'site' },
        auto_accept_threshold: 0.95,
        review_threshold: 0.7,
        mapping: [],
      },
      previewData,
      mappingData,
      projectName: 'project',
      entityName: 'site',
      targetField: 'site_name',
      submitDecision,
    },
    global: { plugins: [vuetify], stubs },
  })
  return { wrapper, row, submitDecision }
}

function rowWithoutCandidates(localKeyValue: string) {
  return {
    local_key_value: localKeyValue,
    site_name: 'Same',
    status: 'proposed' as const,
    candidates: [],
  }
}

describe('ReconciliationGrid', () => {
  it('submits reject and new actions with the row key and no target ID', async () => {
    const { wrapper, submitDecision } = mountGrid()

    await wrapper.get('button[data-action="reject"]').trigger('click')
    await flushPromises()
    expect(submitDecision).toHaveBeenLastCalledWith({ local_key_value: 'A', status: 'rejected' })

    await wrapper.get('button[data-action="local-only"]').trigger('click')
    expect(wrapper.text()).toContain('Mark row as New')
    expect(wrapper.text()).toContain('Mark as New')
    await wrapper.get('[data-testid="confirm-new"]').trigger('click')
    await flushPromises()
    expect(submitDecision).toHaveBeenLastCalledWith({ local_key_value: 'A', status: 'local-only' })
  })

  it('accepts only the candidate explicitly selected by the operator', async () => {
    const { wrapper, submitDecision } = mountGrid()

    await wrapper.get('button[data-action="review"]').trigger('click')
    expect(wrapper.text()).toContain('Review threshold: 70%')
    expect(wrapper.text()).toContain('High score: 95%')
    expect(wrapper.text()).toContain('0%')
    expect(wrapper.text()).toContain('82%')
    expect(wrapper.text()).toContain('100%')
    expect(wrapper.get('[data-testid="accept-candidate"]').attributes('disabled')).toBeDefined()

    const candidates = wrapper.findAll('[data-testid="candidate-option"]')
    expect(candidates).toHaveLength(3)
    await candidates[1]!.trigger('click')
    expect(wrapper.get('[data-testid="accept-candidate"]').attributes('disabled')).toBeUndefined()
    await wrapper.get('[data-testid="accept-candidate"]').trigger('click')
    await flushPromises()

    expect(submitDecision).toHaveBeenCalledWith({
      local_key_value: 'A',
      status: 'accepted',
      target_id: 102,
      candidate_id: 'https://w3id.org/sead/id/site/102',
    })
  })

  it('submits the exact alternative candidate URI selected in search', async () => {
    const { wrapper, submitDecision } = mountGrid()
    const alternative: ReconciliationCandidate = {
      id: 'https://authority.example.test/site/105',
      name: 'Alternative site',
      score: 76,
      type: [],
    }

    await wrapper.get('button[data-action="search"]').trigger('click')
    wrapper.findComponent(AlternativeSearchDialog).vm.$emit('accept', alternative)
    await flushPromises()

    expect(submitDecision).toHaveBeenCalledWith({
      local_key_value: 'A',
      status: 'accepted',
      target_id: 105,
      candidate_id: alternative.id,
    })
  })

  it('places Review after the other row actions', () => {
    const { wrapper } = mountGrid()
    const gridProps = wrapper.findComponent({ name: 'AgGridVue' }).props() as Record<string, unknown>
    const columnDefs = gridProps.columnDefs as ColDef[]
    const actionsColumn = columnDefs.find((column) => column.field === 'candidates')
    const renderer = actionsColumn?.cellRenderer
    if (typeof renderer !== 'function') throw new Error('Actions column renderer is unavailable')

    const html = String(renderer({ data: makeRow('A') } as Parameters<typeof renderer>[0]))
    expect(html.indexOf('data-action="review"')).toBeGreaterThan(html.indexOf('data-action="manual-link"'))
  })

  it('shows confidence as Score and leaves missing values empty', () => {
    const { wrapper } = mountGrid()
    const gridProps = wrapper.findComponent({ name: 'AgGridVue' }).props() as Record<string, unknown>
    const columnDefs = gridProps.columnDefs as ColDef[]
    const scoreColumn = columnDefs.find((column) => column.field === 'confidence_percent')
    expect(scoreColumn?.headerName).toBe('Score')

    const valueFormatter = scoreColumn?.valueFormatter
    if (typeof valueFormatter !== 'function') throw new Error('Score column formatter is unavailable')
    expect(valueFormatter({ value: null } as Parameters<typeof valueFormatter>[0])).toBe('')
    expect(valueFormatter({ value: 0 } as Parameters<typeof valueFormatter>[0])).toBe('0%')
    expect(wrapper.get('[data-testid="row-confidence"]').text()).toBe('')
  })

  it('renders icon row actions with accessible names and tooltips', () => {
    const { wrapper } = mountGrid()
    const gridProps = wrapper.findComponent({ name: 'AgGridVue' }).props() as Record<string, unknown>
    const columnDefs = gridProps.columnDefs as ColDef[]
    const actionsColumn = columnDefs.find((column) => column.field === 'candidates')
    const renderer = actionsColumn?.cellRenderer
    if (typeof renderer !== 'function') throw new Error('Actions column renderer is unavailable')

    const container = document.createElement('div')
    container.innerHTML = String(renderer({ data: makeRow('A') } as Parameters<typeof renderer>[0]))
    const actions = [
      { action: 'search', label: 'Search for another candidate', icon: RECONCILIATION_ACTION_ICONS.search },
      { action: 'reject', label: 'Reject this row', icon: RECONCILIATION_ACTION_ICONS.reject },
      { action: 'local-only', label: 'Mark this row as New', icon: RECONCILIATION_ACTION_ICONS.new },
      { action: 'manual-link', label: 'Add a manual link for this row', icon: RECONCILIATION_ACTION_ICONS.manualLink },
    ]

    for (const action of actions) {
      const button = container.querySelector<HTMLButtonElement>(`button[data-action="${action.action}"]`)
      expect(button?.type).toBe('button')
      expect(button?.getAttribute('aria-label')).toBe(action.label)
      expect(button?.getAttribute('data-tooltip')).toBe(action.label)
      expect(button?.textContent?.trim()).toBe('')
      expect(button?.querySelector(`.mdi.${action.icon}`)).not.toBeNull()
    }
  })

  it('shows one current ID with its mapping source and verification status', () => {
    const mappingData: MappingEntityResponse = {
      entity_name: 'site',
      local_key: 'site_code',
      public_id: 'site_id',
      entity_type: 'primary',
      links: {
        A: {
          target_id: 101,
          source: 'reconciliation',
          created_at: '2026-10-30T00:00:00Z',
          committed_at: '2026-10-30T00:00:00Z',
          verified_at: '2026-10-30T00:01:00Z',
          created_by: 'reconciliation',
        },
        B: {
          target_id: 102,
          source: 'reconciliation',
          created_at: '2026-10-30T00:00:00Z',
          committed_at: '2026-10-30T00:00:00Z',
          created_by: 'reconciliation',
        },
        C: {
          target_id: 103,
          source: 'manual',
          created_at: '2026-10-30T00:00:00Z',
          committed_at: '2026-10-30T00:00:00Z',
          created_by: 'user',
        },
      },
    }
    const rows = [
      { ...makeRow('A'), site_id: 11 },
      { ...makeRow('B'), site_id: 12 },
      { ...makeRow('C'), site_id: 13 },
      { ...makeRow('D'), site_id: 14, status: 'accepted' as const },
    ]
    const { wrapper } = mountGrid(vi.fn(), rows, mappingData)

    expect(wrapper.text()).toContain('Accepted · re-accept candidate')
    const columns = wrapper.get('[data-testid="grid-columns"]').text()
    expect(columns).toContain('Current ID')
    expect(columns).not.toContain('Saved row ID')
    expect(columns).not.toContain('Effective ID')
    expect(columns).not.toContain('Effective ID source')
    expect(wrapper.get('[data-testid="current-id"][data-key="A"]').text()).toBe('101')
    expect(wrapper.get('[data-testid="current-id-source"][data-key="A"]').text()).toBe('Reconciliation · verified')
    expect(wrapper.get('[data-testid="current-id"][data-key="B"]').text()).toBe('102')
    expect(wrapper.get('[data-testid="current-id-source"][data-key="B"]').text()).toBe('Reconciliation · unverified')
    expect(wrapper.get('[data-testid="current-id"][data-key="C"]').text()).toBe('103')
    expect(wrapper.get('[data-testid="current-id-source"][data-key="C"]').text()).toBe('Manual · not checked')
    expect(wrapper.get('[data-testid="current-id"][data-key="D"]').text()).toBe('14')
    expect(wrapper.get('[data-testid="current-id-source"][data-key="D"]').text()).toBe('Normalized row')
  })

  it('leaves Current ID blank when no mapped ID exists', () => {
    const mappingData: MappingEntityResponse = {
      entity_name: 'site',
      local_key: 'site_code',
      public_id: 'site_id',
      entity_type: 'primary',
      links: {},
    }
    const { wrapper } = mountGrid(vi.fn(), [makeRow('A')], mappingData)

    expect(wrapper.get('[data-testid="current-id"][data-key="A"]').text()).toBe('')

    const gridProps = wrapper.findComponent({ name: 'AgGridVue' }).props() as Record<string, unknown>
    const columnDefs = gridProps.columnDefs as ColDef[]
    const currentIdColumn = columnDefs.find((column) => column.field === 'current_id')
    const renderer = currentIdColumn?.cellRenderer
    if (typeof renderer !== 'function') throw new Error('Current ID column renderer is unavailable')

    const cell = renderer({ value: undefined, data: {} } as Parameters<typeof renderer>[0]) as HTMLElement
    expect(cell.querySelector('.current-id-value')?.textContent).toBe('')
  })

  it('displays the local-only decision as New', () => {
    const { wrapper } = mountGrid(vi.fn(), [{ ...makeRow('A'), status: 'local-only' }])

    expect(wrapper.get('[data-testid="row-status"]').text()).toBe('New')
  })

  it('renders state filters with labels, counts, colored icons, and accessible names', () => {
    const { wrapper } = mountGrid()
    const filters = [
      { id: 'proposed', label: 'Proposed', icon: 'mdi-lightbulb-outline', color: 'blue', count: 1 },
      { id: 'accepted', label: 'Accepted', icon: 'mdi-check-circle-outline', color: 'green', count: 0 },
      { id: 'rejected', label: 'Rejected', icon: 'mdi-close-circle-outline', color: 'grey', count: 0 },
      { id: 'local-only', label: 'New', icon: 'mdi-home-outline', color: 'purple', count: 0 },
      { id: 'unresolved', label: 'Unresolved', icon: 'mdi-help-circle-outline', color: 'amber', count: 0 },
      { id: 'errors', label: 'Errors', icon: 'mdi-alert-circle-outline', color: 'red', count: 0 },
    ]

    for (const filter of filters) {
      const chip = wrapper.get(`[data-testid="status-filter-${filter.id}"]`)
      expect(chip.text().trim()).toBe(`${filter.label} (${filter.count})`)
      expect(chip.attributes('title')).toBe(filter.label)
      expect(chip.attributes('aria-label')).toBe(`${filter.label} (${filter.count})`)
      expect(chip.attributes('color')).toBe(filter.color)
      expect(chip.get(`[icon="${filter.icon}"]`).attributes('aria-hidden')).toBe('true')
    }
  })

  it('renders decision statuses as icon-only cells with accessible labels and tooltips', () => {
    const { wrapper } = mountGrid()
    const grid = wrapper.findComponent({ name: 'AgGridVue' })
    const columnDefs = grid.props('columnDefs') as ColDef[]
    const statusColumn = columnDefs.find((column) => column.field === 'status_display')
    const renderer = statusColumn?.cellRenderer
    if (typeof renderer !== 'function') throw new Error('Decision status renderer is unavailable')

    const statuses = [
      { label: 'Proposed', icon: 'mdi-lightbulb-outline', color: 'blue' },
      { label: 'Accepted', icon: 'mdi-check-circle-outline', color: 'green' },
      { label: 'Rejected', icon: 'mdi-close-circle-outline', color: 'grey' },
      { label: 'New', icon: 'mdi-home-outline', color: 'purple' },
      { label: 'Unresolved', icon: 'mdi-help-circle-outline', color: 'amber' },
      { label: 'Needs attention', icon: 'mdi-alert-circle-outline', color: 'red' },
    ]

    for (const status of statuses) {
      const cell = renderer({ value: status.label } as Parameters<typeof renderer>[0]) as HTMLElement
      expect(cell.getAttribute('role')).toBe('img')
      expect(cell.getAttribute('aria-label')).toBe(status.label)
      expect(cell.title).toBe(status.label)
      expect(cell.textContent).toBe('')
      expect(cell.querySelector(`.mdi.${status.icon}.text-${status.color}`)).not.toBeNull()
    }
  })

  it('displays unresolved rows and row-specific errors separately', () => {
    const keylessRow = { site_name: 'Missing key', status: null, errors: ['Missing business key'], candidates: [] }
    const rows = [rowWithoutCandidates('A'), keylessRow, { ...makeRow('B'), errors: ['Invalid target value'] }]
    const { wrapper } = mountGrid(vi.fn(), rows)

    expect(wrapper.get('[data-testid="status-filter-unresolved"]').attributes('aria-label')).toBe('Unresolved (2)')
    expect(wrapper.get('[data-testid="status-filter-errors"]').attributes('aria-label')).toBe('Errors (2)')
    expect(wrapper.findAll('[data-testid="row-status"]').map((status) => status.text())).toContain('Unresolved')
    expect(wrapper.findAll('[data-testid="row-status"]').map((status) => status.text())).toContain('Unreviewable')
    expect(wrapper.findAll('[data-testid="row-status"]').map((status) => status.text())).toContain('Needs attention')
    expect(wrapper.findAll('[data-testid="row-errors"]').map((error) => error.text())).toContain('Invalid target value')
  })

  it('uses the clicked business key when the grid display order changes', async () => {
    const submitDecision = vi.fn().mockResolvedValue(undefined)
    const { wrapper } = mountGrid(submitDecision, [makeRow('A'), makeRow('B')])

    await wrapper.get('button[data-action="reject"]').trigger('click')
    await flushPromises()

    expect(submitDecision).toHaveBeenCalledWith({ local_key_value: 'B', status: 'rejected' })
  })

  it('shows a failed decision and does not change the preview row', async () => {
    const submitDecision = vi.fn().mockRejectedValue(new Error('Save failed'))
    const { wrapper, row } = mountGrid(submitDecision)

    await wrapper.get('button[data-action="reject"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="decision-error"]').text()).toContain('Save failed')
    expect(row?.status).toBe('proposed')
  })
})

describe('PreviewMatchedDataDialog', () => {
  it('shows confidence on a 0–100 scale and distinguishes unresolved, unreviewable, and error rows', () => {
    const wrapper = mount(PreviewMatchedDataDialog, {
      props: {
        modelValue: true,
        entitySpec: {
          source: null,
          property_mappings: { site_name: 'site_name' },
          remote: { service_type: 'site' },
          auto_accept_threshold: 0.95,
          review_threshold: 0.7,
          mapping: [],
        },
        previewData: [
          {
            local_key_value: 'zero',
            site_name: 'Zero score',
            status: 'accepted',
            target_id: 1,
            matched_name: 'Zero',
            confidence: 0,
          },
          {
            local_key_value: 'review',
            site_name: 'Review score',
            status: 'accepted',
            target_id: 2,
            matched_name: 'Review',
            confidence: 0.82,
          },
          {
            local_key_value: 'high',
            site_name: 'High score',
            status: 'accepted',
            target_id: 3,
            matched_name: 'High',
            confidence: 1,
          },
          {
            local_key_value: 'unknown',
            site_name: 'Unknown score',
            status: 'accepted',
            target_id: 4,
            matched_name: 'Unknown',
            confidence: null,
          },
          { local_key_value: 'no-candidate', site_name: 'No candidates', status: 'proposed', candidates: [] },
          { site_name: 'Missing business key', status: null, candidates: [] },
          { local_key_value: 'error', site_name: 'Invalid row', status: 'accepted', errors: ['Invalid target value'] },
        ],
      },
      global: { plugins: [vuetify], stubs },
    })

    const rows = wrapper.findAll('tbody tr')
    expect(rows[0]?.text()).toContain('0%')
    expect(rows[1]?.text()).toContain('82%')
    expect(rows[2]?.text()).toContain('100%')
    expect(rows[3]?.text()).toContain('—')
    expect(rows[4]?.find('[aria-label="Unresolved"]').exists()).toBe(true)
    expect(rows[5]?.find('[aria-label="Unreviewable"]').exists()).toBe(true)
    expect(rows[6]?.find('[aria-label="Needs attention"]').exists()).toBe(true)
    expect(rows[6]?.text()).toContain('Invalid target value')
    expect(wrapper.find('[aria-label="Unresolved: 2"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Errors: 1"]').exists()).toBe(true)
  })

  it('uses compact rows while keeping row virtualization enabled', () => {
    const { wrapper } = mountGrid()

    const grid = wrapper.get('[data-testid="grid-stub"]')
    // autoHeight would disable virtualization and render every row at once.
    expect(grid.attributes('domlayout')).toBe('normal')
    expect(wrapper.get('[data-testid="grid-row-height"]').text()).toBe('32')
  })

  it('assigns a row class name instead of a per-render style object', () => {
    const previewData = [
      { local_key_value: 'A', site_name: 'Same', status: 'accepted' as const, candidates: [] },
      { local_key_value: 'B', site_name: 'Same', status: 'rejected' as const, candidates: [] },
      { local_key_value: 'C', site_name: 'Same', status: 'proposed' as const, errors: ['Bad value'], candidates: [] },
      { local_key_value: 'D', site_name: 'New row', status: 'local-only' as const, candidates: [] },
      { local_key_value: 'E', site_name: 'Unresolved row', status: 'proposed' as const, candidates: [] },
      makeRow('F'),
    ]
    const wrapper = mount(ReconciliationGrid, {
      props: {
        entitySpec: {
          source: null,
          property_mappings: {},
          remote: { service_type: 'site' },
          auto_accept_threshold: 0.95,
          review_threshold: 0.7,
          mapping: [],
        },
        previewData,
        mappingData: null,
        projectName: 'project',
        entityName: 'site',
        targetField: 'site_name',
        submitDecision: vi.fn().mockResolvedValue(undefined),
      },
      global: { plugins: [vuetify], stubs },
    })

    const rows = wrapper.findAll('[data-testid="grid-row"]')
    const classes = rows.map((row) => row.find('[data-testid="row-class"]').text())
    expect(classes).toContain('row-accepted')
    expect(classes).toContain('row-rejected')
    expect(classes).toContain('row-local-only')
    expect(classes).toContain('row-proposed')
    expect(classes).toContain('row-unresolved')
    // An error takes precedence over the decision status.
    expect(classes).toContain('row-needs-attention')
  })

  it('shows an accessible state icon and matching row color in the preview dialog', () => {
    const wrapper = mount(PreviewMatchedDataDialog, {
      props: {
        modelValue: true,
        previewData: [{ ...makeRow('A'), status: 'rejected' }],
        entitySpec: null,
      },
      global: { plugins: [vuetify], stubs },
    })

    const status = wrapper.get('[aria-label="Rejected"]')
    expect(status.attributes('title')).toBe('Rejected')
    expect(status.get('[icon="mdi-close-circle-outline"]').attributes('aria-hidden')).toBe('true')
    expect(wrapper.get('tbody tr').classes()).toContain('bg-grey-lighten-5')
  })
})
