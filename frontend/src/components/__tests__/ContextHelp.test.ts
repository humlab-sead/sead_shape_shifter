import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ContextHelp from '../ContextHelp.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'project-detail', query: { tab: 'reconciliation' } }),
}))

const slotStub = { template: '<div><slot /></div>' }

describe('ContextHelp', () => {
  it('shows reconciliation tips on the project reconciliation tab', () => {
    const wrapper = mount(ContextHelp, {
      global: {
        stubs: {
          VExpansionPanels: slotStub,
          VExpansionPanel: slotStub,
          VExpansionPanelTitle: slotStub,
          VExpansionPanelText: slotStub,
          VIcon: {
            props: ['icon'],
            template: '<span :data-icon="icon"><slot /></span>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Reconcile & Review')
    expect(wrapper.text()).toContain('Find Candidates proposes matches')
    expect(wrapper.text()).toContain('The search label finds candidates')
    expect(wrapper.text()).toContain('Export to Mapping')
    expect(wrapper.text()).toContain('Row action icons')

    const actions = wrapper.findAll('.row-action-item')
    expect(actions.map((action) => action.find('.font-weight-medium').text())).toEqual([
      'Search',
      'Reject',
      'New',
      'Manual link',
    ])
    expect(wrapper.findAll('.row-action-icon').map((icon) => icon.attributes('data-icon'))).toEqual([
      'mdi-magnify',
      'mdi-close-circle-outline',
      'mdi-plus-circle-outline',
      'mdi-link-variant',
    ])
  })
})
