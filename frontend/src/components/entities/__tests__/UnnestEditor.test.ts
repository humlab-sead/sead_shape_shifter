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
    emits: ['update:modelValue'],
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

  it('normalizes scalar references to chips, clones props, and emits ordered arrays', async () => {
    const initial = {
      id_vars: '@value: entities.site.keys',
      value_vars: ['manual_value', '@value: entities.site.columns'],
      var_name: 'variable',
      value_name: 'value',
      keep_empty: true,
    }
    const wrapper = mount(UnnestEditor, {
      props: { modelValue: initial as any },
      global: { stubs },
    })

    const comboboxes = wrapper.findAllComponents({ name: 'VCombobox' })
    expect(comboboxes[0]?.props('modelValue')).toEqual(['@value: entities.site.keys'])
    expect(comboboxes[1]?.props('modelValue')).toEqual(['manual_value', '@value: entities.site.columns'])
    expect(initial.id_vars).toBe('@value: entities.site.keys')

    comboboxes[1]?.vm.$emit('update:modelValue', ['manual_value', 'entered_value'])
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toMatchObject({
      id_vars: ['@value: entities.site.keys'],
      value_vars: ['manual_value', 'entered_value'],
      keep_empty: true,
    })

    await wrapper.setProps({
      modelValue: {
        id_vars: ['updated_id'],
        value_vars: '@value: entities.site.updated_columns',
        var_name: 'updated_variable',
        value_name: 'updated_value',
      } as any,
    })
    expect(comboboxes[0]?.props('modelValue')).toEqual(['updated_id'])
    expect(comboboxes[1]?.props('modelValue')).toEqual(['@value: entities.site.updated_columns'])
  })
})
