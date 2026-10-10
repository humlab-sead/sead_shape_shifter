import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import FiltersEditor from '../FiltersEditor.vue'

const querySchema = vi.hoisted(() => ({
  key: 'query',
  display_name: 'Query',
  description: 'Filter rows with a query',
  fields: [
    {
      name: 'column',
      type: 'column',
      required: false,
      description: 'Column',
      placeholder: 'Column name',
    },
  ],
}))

vi.mock('@/composables/useFilterSchema', () => ({
  useFilterSchema: () => ({
    loadFilterSchemas: vi.fn(async () => undefined),
    getFilterSchema: (key: string) => (key === querySchema.key ? querySchema : undefined),
    getFilterTypes: () => [{ title: querySchema.display_name, value: querySchema.key }],
  }),
}))

const stubs = {
  VList: { template: '<div><slot /></div>' },
  VListItem: { template: '<div><slot /></div>' },
  VCard: { template: '<div><slot /></div>' },
  VCardText: { template: '<div><slot /></div>' },
  VBtn: { template: '<button><slot /></button>' },
  VAlert: { template: '<div><slot /></div>' },
  VRow: { template: '<div><slot /></div>' },
  VCol: { template: '<div><slot /></div>' },
  VCheckbox: { template: '<div />' },
  VSelect: { template: '<div />' },
  VTextField: {
    name: 'VTextField',
    props: ['modelValue', 'label'],
    template: '<div class="text-field-stub" />',
  },
  VCombobox: {
    name: 'VCombobox',
    props: ['modelValue', 'label'],
    template: '<div class="combobox-stub" />',
  },
}

describe('FiltersEditor', () => {
  it('keeps column filter fields as text inputs', async () => {
    const wrapper = mount(FiltersEditor, {
      props: { modelValue: [{ type: 'query', column: 'sample_name' }] },
      global: { stubs },
    })
    await flushPromises()

    expect(wrapper.findAllComponents({ name: 'VTextField' })).toHaveLength(1)
    expect(wrapper.findAllComponents({ name: 'VTextField' })[0]?.props('label')).toBe('Column')
    expect(wrapper.findAllComponents({ name: 'VCombobox' })).toHaveLength(0)
  })
})
