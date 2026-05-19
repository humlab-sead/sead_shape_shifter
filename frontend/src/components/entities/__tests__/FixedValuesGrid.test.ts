import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { shallowMount } from '@vue/test-utils'

import FixedValuesGrid from '../FixedValuesGrid.vue'

const AgGridVueStub = {
  name: 'AgGridVue',
  template: '<div class="ag-grid-vue-stub" />',
}

describe('FixedValuesGrid', () => {
  it('emits normalized rows when incoming modelValue contains coercible _id strings', async () => {
    const wrapper = shallowMount(FixedValuesGrid, {
      props: {
        modelValue: [[1, '53', 'Sampling']],
        columns: ['system_id', 'method_id', 'name'],
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
      [['Row 1, column method_id: Expected integer ID']],
    ])
  })
})
