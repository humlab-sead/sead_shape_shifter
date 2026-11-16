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
          VIcon: { template: '<span><slot /></span>' },
        },
      },
    })

    expect(wrapper.text()).toContain('Reconcile & Review')
    expect(wrapper.text()).toContain('Find Candidates proposes matches')
    expect(wrapper.text()).toContain('The search label finds candidates')
    expect(wrapper.text()).toContain('Export to Mapping')
  })
})
