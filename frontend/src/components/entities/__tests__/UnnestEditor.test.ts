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
    template:
      '<div class="combobox-stub"><slot v-for="(item, index) in modelValue" name="chip" :item="{ raw: item, title: item }" :props="{ closable: true }" :key="index" /></div>',
  },
  ValueReferenceChip: {
    name: 'ValueReferenceChip',
    props: ['value', 'chipProps', 'entities'],
    template: '<span data-testid="value-reference-chip">{{ value }}</span>',
  },
  VChip: {
    props: ['closable'],
    template: '<span><slot /></span>',
  },
}

describe('UnnestEditor', () => {
  it('uses separate ID and value candidates and accepts a value outside the suggestions', async () => {
    const wrapper = mount(UnnestEditor, {
      props: {
        modelValue: {
          id_vars: ['@value: entities.site.keys'],
          value_vars: ['saved_value', '@value: entities.site.columns'],
          var_name: 'variable',
          value_name: 'value',
        },
        idVarColumns: ['id_candidate'],
        valueVarColumns: ['value_candidate'],
        referenceEntities: [],
        referenceSuggestions: ['@value: entities.site.keys', '@value: entities.site.columns'],
      },
      global: { stubs },
    })
    const comboboxes = wrapper.findAllComponents({ name: 'VCombobox' })

    expect(comboboxes[0]?.props('items')).toEqual([
      'id_candidate',
      '@value: entities.site.keys',
      '@value: entities.site.columns',
    ])
    expect(comboboxes[1]?.props('items')).toEqual([
      'value_candidate',
      '@value: entities.site.keys',
      '@value: entities.site.columns',
    ])
    expect(wrapper.findAllComponents({ name: 'ValueReferenceChip' })).toHaveLength(2)

    comboboxes[1]?.vm.$emit('update:modelValue', ['saved_value', 'manual_value'])
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toMatchObject({
      id_vars: ['@value: entities.site.keys'],
      value_vars: ['saved_value', 'manual_value'],
    })
  })
})
