import { describe, expect, it } from 'vitest'
import { shallowMount } from '@vue/test-utils'

import ForeignKeyEditor from '../ForeignKeyEditor.vue'

const ForeignKeyTesterStub = {
  name: 'ForeignKeyTester',
  props: ['disabled'],
  template: '<div data-testid="foreign-key-tester" :data-disabled="String(disabled)" />',
}

const ControlStub = {
  inheritAttrs: false,
  props: ['modelValue'],
  template: '<div><slot /></div>',
}

describe('ForeignKeyEditor', () => {
  it('disables foreign key testing while entity changes are unsaved', async () => {
    const wrapper = shallowMount(ForeignKeyEditor, {
      props: {
        modelValue: [
          {
            entity: 'site',
            local_keys: ['site_id'],
            remote_keys: ['site_id'],
            how: 'inner',
          },
        ],
        projectName: 'demo',
        entityName: 'sample',
        isEntitySaved: true,
        hasUnsavedChanges: true,
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: {
          ForeignKeyTester: ForeignKeyTesterStub,
          VAutocomplete: ControlStub,
          VSelect: ControlStub,
          VCombobox: ControlStub,
        },
      },
    })

    const tester = wrapper.find('[data-testid="foreign-key-tester"]')
    expect(tester.attributes('data-disabled')).toBe('true')
    expect(wrapper.text()).toContain('Save the entity before testing this foreign key.')

    await wrapper.setProps({ hasUnsavedChanges: false })

    expect(tester.attributes('data-disabled')).toBe('false')
  })
})
