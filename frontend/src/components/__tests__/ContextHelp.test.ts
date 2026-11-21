import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ContextHelp from '../ContextHelp.vue'
import { activateReviewWorkspaceHelp, setReviewWorkspaceHelpMode } from '@/composables/useReviewWorkspaceHelp'

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'project-detail', query: { tab: 'reconciliation' } }),
}))

const slotStub = { template: '<div><slot /></div>' }

function mountHelp() {
  return mount(ContextHelp, {
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
}

describe('ContextHelp', () => {
  it('shows reconciliation tips on the project reconciliation tab', () => {
    const wrapper = mountHelp()

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

  it('shows search workspace help while the workspace is open in search mode', () => {
    const release = activateReviewWorkspaceHelp('search')
    try {
      const wrapper = mountHelp()
      const text = wrapper.text()

      expect(text).toContain('Review workspace')
      expect(text).toContain('Enter searches immediately')
      expect(text).toContain('Ranked results are limited suggestions')
      expect(text).toContain('Saving a decision stores the choice')
      expect(text).toContain('Alt+Enter')
      expect(text).toContain('Stage New for the current row')
      expect(text).not.toContain('Find Candidates proposes matches')
      expect(text).not.toContain('Row action icons')
    } finally {
      release()
    }
  })

  it('switches to browse help when the workspace mode changes', () => {
    const release = activateReviewWorkspaceHelp('search')
    try {
      setReviewWorkspaceHelpMode('browse')
      const wrapper = mountHelp()
      const text = wrapper.text()

      expect(text).toContain('Review workspace')
      expect(text).toContain('Browse loads the complete target list')
      expect(text).toContain('use Search instead')
      expect(text).not.toContain('Enter searches immediately')
    } finally {
      release()
    }
  })

  it('returns to the review-table help after the workspace closes', () => {
    const release = activateReviewWorkspaceHelp('search')
    release()

    const wrapper = mountHelp()
    expect(wrapper.text()).toContain('Find Candidates proposes matches')
    expect(wrapper.text()).not.toContain('Review workspace')
  })
})

describe('ContextHelp expansion', () => {
  const panelsStub = {
    props: ['modelValue'],
    template: '<div data-testid="panels" :data-model="JSON.stringify(modelValue)"><slot /></div>',
  }

  function mountExpansion() {
    return mount(ContextHelp, {
      global: {
        stubs: {
          VExpansionPanels: panelsStub,
          VExpansionPanel: slotStub,
          VExpansionPanelTitle: { template: '<button data-testid="panel-title"><slot /></button>' },
          VExpansionPanelText: slotStub,
          VIcon: { template: '<span><slot /></span>' },
        },
      },
    })
  }

  function panelState(wrapper: ReturnType<typeof mountExpansion>): string | undefined {
    return wrapper.get('[data-testid="panels"]').attributes('data-model')
  }

  let storage: Map<string, string>

  beforeEach(() => {
    storage = new Map()
    vi.stubGlobal('localStorage', {
      get length() {
        return storage.size
      },
      clear: () => storage.clear(),
      getItem: (key: string) => (storage.has(key) ? (storage.get(key) as string) : null),
      key: (index: number) => Array.from(storage.keys())[index] ?? null,
      removeItem: (key: string) => void storage.delete(key),
      setItem: (key: string, value: string) => void storage.set(key, String(value)),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('starts expanded when the browser has no stored preference', () => {
    expect(panelState(mountExpansion())).toBe('[0]')
  })

  it('restores a collapsed preference from browser storage', () => {
    storage.set('shapeshifter.contextHelp.expanded', 'false')
    expect(panelState(mountExpansion())).toBe('[]')
  })

  it('remembers the collapsed state after the reviewer closes the panel', async () => {
    const wrapper = mountExpansion()
    await wrapper.get('[data-testid="panel-title"]').trigger('click')

    expect(panelState(wrapper)).toBe('[]')
    expect(storage.get('shapeshifter.contextHelp.expanded')).toBe('false')
  })

  it('expands when the review workspace opens without overwriting the stored preference', async () => {
    storage.set('shapeshifter.contextHelp.expanded', 'false')
    const wrapper = mountExpansion()
    expect(panelState(wrapper)).toBe('[]')

    const release = activateReviewWorkspaceHelp('search')
    try {
      await nextTick()
      expect(panelState(wrapper)).toBe('[0]')
      expect(storage.get('shapeshifter.contextHelp.expanded')).toBe('false')
    } finally {
      release()
    }
  })
})
