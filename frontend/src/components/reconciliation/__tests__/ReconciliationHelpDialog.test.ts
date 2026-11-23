import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ReconciliationHelpDialog from '../ReconciliationHelpDialog.vue'

const slotStub = { template: '<div><slot /></div>' }

describe('ReconciliationHelpDialog', () => {
  it('explains the workflow, grid columns, controls, and row actions', () => {
    const wrapper = mount(ReconciliationHelpDialog, {
      props: { modelValue: true },
      global: {
        stubs: {
          VDialog: {
            props: ['modelValue'],
            template: '<div v-if="modelValue"><slot /></div>',
          },
          VExpansionPanels: slotStub,
          VExpansionPanel: slotStub,
          VExpansionPanelTitle: slotStub,
          VExpansionPanelText: slotStub,
          VCard: slotStub,
          VCardTitle: slotStub,
          VCardText: slotStub,
          VCardActions: slotStub,
          VAlert: slotStub,
          VDivider: { template: '<hr />' },
          VSpacer: { template: '<span />' },
          VIcon: { template: '<span><slot /></span>' },
          VBtn: {
            inheritAttrs: false,
            template: '<button type="button" v-bind="$attrs"><slot /></button>',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Find Candidates')
    expect(text).toContain('Business key')
    expect(text).toContain('Current ID')
    expect(text).not.toContain('Saved row ID')
    expect(text).not.toContain('Effective ID')
    expect(text).toContain('Score')
    expect(text).toContain('Review (n)')
    expect(text).toContain('New')
    expect(text).not.toContain('Local-only')
    expect(text).toContain('Manual link')
    expect(text).toContain('Export to Mapping')
    expect(wrapper.get('[data-testid="reconciliation-help-guide"]').attributes('href')).toBe(
      '/help?doc=USER_GUIDE#reconciliation-workflow'
    )
  })

  it('adds the workspace topic for the current mode when a mode is supplied', () => {
    const wrapper = mount(ReconciliationHelpDialog, {
      props: { modelValue: true, workspaceMode: 'browse' },
      global: {
        stubs: {
          VDialog: {
            props: ['modelValue'],
            template: '<div v-if="modelValue"><slot /></div>',
          },
          VExpansionPanels: slotStub,
          VExpansionPanel: slotStub,
          VExpansionPanelTitle: slotStub,
          VExpansionPanelText: slotStub,
          VCard: slotStub,
          VCardTitle: slotStub,
          VCardText: slotStub,
          VCardActions: slotStub,
          VAlert: slotStub,
          VDivider: { template: '<hr />' },
          VSpacer: { template: '<span />' },
          VIcon: { template: '<span><slot /></span>' },
          VBtn: {
            inheritAttrs: false,
            template: '<button type="button" v-bind="$attrs"><slot /></button>',
          },
        },
      },
    })

    const workspace = wrapper.get('[data-testid="reconciliation-help-workspace"]').text()
    expect(workspace).toContain('Review workspace')
    expect(workspace).toContain('Browse')
    expect(workspace).toContain('complete target list')
    expect(workspace).toContain('Saving and export')
    expect(workspace).toContain('Alt+Enter')
  })

  it('omits the workspace topic when no mode is supplied', () => {
    const wrapper = mount(ReconciliationHelpDialog, {
      props: { modelValue: true },
      global: {
        stubs: {
          VDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' },
          VExpansionPanels: slotStub,
          VExpansionPanel: slotStub,
          VExpansionPanelTitle: slotStub,
          VExpansionPanelText: slotStub,
          VCard: slotStub,
          VCardTitle: slotStub,
          VCardText: slotStub,
          VCardActions: slotStub,
          VAlert: slotStub,
          VDivider: { template: '<hr />' },
          VSpacer: { template: '<span />' },
          VIcon: { template: '<span><slot /></span>' },
          VBtn: { inheritAttrs: false, template: '<button type="button" v-bind="$attrs"><slot /></button>' },
        },
      },
    })

    expect(wrapper.find('[data-testid="reconciliation-help-workspace"]').exists()).toBe(false)
  })
})
