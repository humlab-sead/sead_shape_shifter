import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { shallowMount } from '@vue/test-utils'

import FixedValuesGrid from '../FixedValuesGrid.vue'

const AgGridVueStub = {
  name: 'AgGridVue',
  props: ['columnDefs'],
  template: '<div class="ag-grid-vue-stub" />',
}

describe('FixedValuesGrid', () => {
  it('emits normalized rows when incoming modelValue contains coercible _id strings', async () => {
    const wrapper = shallowMount(FixedValuesGrid, {
      props: {
        modelValue: [[1, '53', 'Sampling']],
        columns: ['system_id', 'method_id', 'name'],
        columnTypes: {},
        publicId: 'method_id',
      },
      global: {
        stubs: {
          AgGridVue: AgGridVueStub,
        },
      },
    })

    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toEqual([
      [[[1, 53, 'Sampling']]],
    ])
    expect(wrapper.emitted('validation-errors')).toBeUndefined()
  })

  it('surfaces validation errors instead of emitting invalid loaded ids', async () => {
    const wrapper = shallowMount(FixedValuesGrid, {
      props: {
        modelValue: [[1, '53abc', 'Sampling']],
        columns: ['system_id', 'method_id', 'name'],
        columnTypes: {},
        publicId: 'method_id',
      },
      global: {
        stubs: {
          AgGridVue: AgGridVueStub,
        },
      },
    })

    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(wrapper.emitted('validation-errors')).toEqual([
      [['Column method_id: 1 invalid value (row 1)']],
    ])
  })

  it('uses declared int column types for non-_id columns', async () => {
    const wrapper = shallowMount(FixedValuesGrid, {
      props: {
        modelValue: [[1, '7', 'Sampling']],
        columns: ['system_id', 'rank', 'name'],
        columnTypes: { rank: 'int' },
        publicId: 'name',
      },
      global: {
        stubs: {
          AgGridVue: AgGridVueStub,
        },
      },
    })

    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toEqual([
      [[[1, 7, 'Sampling']]],
    ])
  })

  it('uses declared float column types for non-_id columns', async () => {
    const wrapper = shallowMount(FixedValuesGrid, {
      props: {
        modelValue: [[1, '7.25', 'Sampling']],
        columns: ['system_id', 'measurement', 'name'],
        columnTypes: { measurement: 'float' },
        publicId: 'name',
      },
      global: {
        stubs: {
          AgGridVue: AgGridVueStub,
        },
      },
    })

    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toEqual([
      [[[1, 7.25, 'Sampling']]],
    ])
  })

  it('does not coerce unsupported declared types on load', async () => {
    const wrapper = shallowMount(FixedValuesGrid, {
      props: {
        modelValue: [[1, true]],
        columns: ['system_id', 'is_active'],
        columnTypes: { is_active: 'bool' },
      },
      global: {
        stubs: {
          AgGridVue: AgGridVueStub,
        },
      },
    })

    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(wrapper.emitted('validation-errors')).toBeUndefined()
  })

  it('wires compact header components for editable columns and removes detached controls', async () => {
    const wrapper = shallowMount(FixedValuesGrid, {
      props: {
        modelValue: [[1, 53, 'Sampling']],
        columns: ['system_id', 'method_id', 'name'],
        columnTypes: {},
        publicId: 'method_id',
      },
      global: {
        stubs: {
          AgGridVue: AgGridVueStub,
        },
      },
    })

    await nextTick()

    expect(wrapper.find('.column-type-controls').exists()).toBe(false)

    expect(wrapper.html()).not.toContain('column-type-controls')
    expect(wrapper.html()).toContain('headerheight="48"')
  })

  it('offers float as a first-class editable column type option', async () => {
    const wrapper = shallowMount(FixedValuesGrid, {
      props: {
        modelValue: [[1, 53, 'Sampling']],
        columns: ['system_id', 'measurement', 'name'],
        columnTypes: {},
        publicId: 'name',
      },
      global: {
        stubs: {
          AgGridVue: AgGridVueStub,
        },
      },
    })

    await nextTick()

    const columnDefs = (wrapper.vm as any).columnDefs as Array<Record<string, any>>
    const measurementColumn = columnDefs.find((column) => column.headerName === 'measurement')
    const options = measurementColumn?.headerComponentParams?.getOptions('measurement')

    expect(options).toEqual([
      { value: 'auto', label: 'Auto (string)' },
      { value: 'int', label: 'Integer' },
      { value: 'float', label: 'Float' },
      { value: 'string', label: 'String' },
    ])
  })
})
