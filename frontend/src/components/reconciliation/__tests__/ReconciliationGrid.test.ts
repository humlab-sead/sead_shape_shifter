import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import type { MappingEntityResponse, ReconciliationCandidate, ReconciliationPreviewRow } from '@/types'

vi.mock('ag-grid-vue3', () => ({
  AgGridVue: {
    props: ['rowData'],
    template: `
      <div data-testid="grid-stub">
        <div v-for="row in rowData.slice().reverse()" :key="row.local_key_value">
          <span data-testid="row-status">{{ row.status_display }}</span>
          <span data-testid="row-confidence">{{ row.confidence_percent == null ? 'Unknown' : Math.round(row.confidence_percent) + '%' }}</span>
          <span data-testid="row-errors">{{ row.errors_display || '—' }}</span>
          <span data-testid="effective-id-status">{{ row.effective_id_status }}</span>
          <button :data-local-key="row.local_key_value" data-action="reject">Reject</button>
          <button :data-local-key="row.local_key_value" data-action="review">Review</button>
          <button :data-local-key="row.local_key_value" data-action="search">Search</button>
          <button :data-local-key="row.local_key_value" data-action="local-only">Local-only</button>
        </div>
      </div>
    `,
  },
}))

import ReconciliationGrid from '../ReconciliationGrid.vue'
import AlternativeSearchDialog from '../AlternativeSearchDialog.vue'
import PreviewMatchedDataDialog from '../PreviewMatchedDataDialog.vue'

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
  it('submits reject and local-only actions with the row key and no target ID', async () => {
    const { wrapper, submitDecision } = mountGrid()

    await wrapper.get('button[data-action="reject"]').trigger('click')
    await flushPromises()
    expect(submitDecision).toHaveBeenLastCalledWith({ local_key_value: 'A', status: 'rejected' })

    await wrapper.get('button[data-action="local-only"]').trigger('click')
    await wrapper.get('[data-testid="confirm-local-only"]').trigger('click')
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

  it('shows legacy accepted decisions that need candidate re-acceptance and sidecar link status', () => {
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
    const legacy = { ...makeRow('D'), status: 'accepted' as const }
    const rows = [makeRow('A'), makeRow('B'), makeRow('C'), legacy]
    const { wrapper } = mountGrid(vi.fn(), rows, mappingData)

    expect(wrapper.text()).toContain('Accepted · re-accept candidate')
    expect(wrapper.text()).toContain('reconciliation · verified 2026-10-30T00:01:00Z')
    expect(wrapper.text()).toContain('reconciliation · unverified')
    expect(wrapper.text()).toContain('Trusted manual · not checked')
  })

  it('displays unresolved rows and row-specific errors separately', () => {
    const keylessRow = { site_name: 'Missing key', status: null, errors: ['Missing business key'], candidates: [] }
    const rows = [rowWithoutCandidates('A'), keylessRow, { ...makeRow('B'), errors: ['Invalid target value'] }]
    const { wrapper } = mountGrid(vi.fn(), rows)

    expect(wrapper.text()).toContain('Unresolved (2)')
    expect(wrapper.text()).toContain('Errors (2)')
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
    expect(rows[4]?.text()).toContain('Unresolved')
    expect(rows[5]?.text()).toContain('Unreviewable')
    expect(rows[6]?.text()).toContain('Needs attention')
    expect(rows[6]?.text()).toContain('Invalid target value')
    expect(wrapper.text()).toContain('2 unresolved · 1 errors')
  })
})
