import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { defineComponent, h, nextTick } from 'vue'
import { useTheme } from 'vuetify'
import type { SelectionDisplayField, SelectionRecord } from '@/types/reconciliation'

vi.mock('ag-grid-vue3', () => ({
  AgGridVue: {
    name: 'AgGridVue',
    props: ['rowData', 'columnDefs', 'getRowId', 'rowSelection'],
    emits: ['grid-ready', 'row-clicked'],
    template: '<div data-testid="browse-grid-stub" />',
  },
}))

import SelectionBrowseGrid from '../SelectionBrowseGrid.vue'

const columns: SelectionDisplayField[] = [
  { name: 'name', source: 'record', label: 'Name', value_type: 'string', display: true },
  { name: 'target_id', source: 'record', label: 'ID', value_type: 'integer', display: true },
]

function record(targetId: number, name: string): SelectionRecord {
  return {
    id: `https://w3id.org/sead/id/feature_type/${targetId}`,
    target_id: targetId,
    type: 'feature_type',
    name,
    fields: {},
    score: null,
  }
}

/** Mount the grid inside a host so the test can drive the Vuetify theme. */
async function mountThemed() {
  const vuetify = createVuetify({ components, directives })
  let theme: ReturnType<typeof useTheme>

  const Host = defineComponent({
    setup() {
      theme = useTheme()
      return () =>
        h(SelectionBrowseGrid, {
          items: [record(1, 'Bronze Age')],
          columns,
          selectedId: null,
        })
    },
  })

  const wrapper = mount(Host, { global: { plugins: [vuetify] } })
  await nextTick()
  return { wrapper, theme: theme! }
}

describe('SelectionBrowseGrid theme', () => {
  it('uses the light material theme while the application is light', async () => {
    const { wrapper } = await mountThemed()
    const grid = wrapper.find('[data-testid="browse-grid-stub"]')

    expect(grid.classes()).toContain('ag-theme-material')
    expect(grid.classes()).not.toContain('ag-theme-material-dark')
  })

  it('switches to the dark material theme when the application turns dark', async () => {
    const { wrapper, theme } = await mountThemed()

    theme.change('dark')
    await nextTick()

    const grid = wrapper.find('[data-testid="browse-grid-stub"]')
    expect(grid.classes()).toContain('ag-theme-material-dark')
    expect(grid.classes()).not.toContain('ag-theme-material')
  })

  it('returns to the light material theme when dark mode is turned off', async () => {
    const { wrapper, theme } = await mountThemed()

    theme.change('dark')
    await nextTick()
    theme.change('light')
    await nextTick()

    expect(wrapper.find('[data-testid="browse-grid-stub"]').classes()).toContain('ag-theme-material')
  })
})

describe('SelectionBrowseGrid row selection', () => {
  it('selects a whole row on a single click without checkboxes', async () => {
    const { wrapper } = await mountThemed()
    const grid = wrapper.findComponent({ name: 'AgGridVue' })

    expect(grid.props('rowSelection')).toEqual({
      mode: 'singleRow',
      enableClickSelection: 'enableSelection',
      checkboxes: false,
    })
  })

  it('reports the clicked record so the reviewer can stage it', async () => {
    const { wrapper } = await mountThemed()
    const record = wrapper.findComponent({ name: 'AgGridVue' }).props('rowData')[0]

    wrapper.findComponent({ name: 'AgGridVue' }).vm.$emit('row-clicked', { data: record })
    await nextTick()

    expect(wrapper.findComponent(SelectionBrowseGrid).emitted('select')).toEqual([[record]])
  })
})
