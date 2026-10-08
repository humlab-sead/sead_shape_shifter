import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import UnnestEditor from '../UnnestEditor.vue'

const stubs = {
  VSwitch: true,
  VAlert: true,
  VTextField: {
    name: 'VTextField',
    props: ['modelValue', 'label', 'prefix'],
    template: '<div class="text-field-stub" />',
  },
  VCombobox: {
    name: 'VCombobox',
    props: ['modelValue', 'items', 'label'],
    template: '<div class="combobox-stub" />',
  },
}

describe('UnnestEditor', () => {
  it('uses separate ID and value candidates and accepts a value outside the suggestions', async () => {
    const wrapper = mount(UnnestEditor, {
      props: {
        modelValue: {
          id_vars: ['saved_id'],
          value_vars: ['saved_value'],
          var_name: 'variable',
          value_name: 'value',
        },
        idVarColumns: ['id_candidate'],
        valueVarColumns: ['value_candidate'],
      },
      global: { stubs },
    })
    const comboboxes = wrapper.findAllComponents({ name: 'VCombobox' })

    expect(comboboxes[0]?.props('items')).toEqual(['id_candidate'])
    expect(comboboxes[1]?.props('items')).toEqual(['value_candidate'])

    comboboxes[1]?.vm.$emit('update:modelValue', ['saved_value', 'manual_value'])
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toMatchObject({
      id_vars: ['saved_id'],
      value_vars: ['saved_value', 'manual_value'],
    })
  })
})
