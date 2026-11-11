import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const whatsNewState = vi.hoisted(() => ({
  latestNote: null as {
    version: string
    title: string
    date: string
    highlights: string[]
    sections: { title: string; items: string[] }[]
  } | null,
  pendingNote: null as { html: string } | null,
  notes: [] as {
    version: string
    title: string
    date: string
    highlights: string[]
    sections: { title: string; items: string[] }[]
  }[],
  loadAllNotes: vi.fn(async () => []),
}))

vi.mock('@/composables/useWhatsNew', async () => {
  const { ref } = await import('vue')

  return {
    useWhatsNew: () => ({
      latestNote: ref(whatsNewState.latestNote),
      pendingNote: ref(whatsNewState.pendingNote),
      notes: ref(whatsNewState.notes),
      loading: ref(false),
      error: ref(null),
      loadAllNotes: whatsNewState.loadAllNotes,
    }),
  }
})

import WhatsNewView from '../WhatsNewView.vue'

const vuetify = createVuetify({ components, directives })

describe('WhatsNewView', () => {
  beforeEach(() => {
    const latestNote = {
      version: '2.5.0',
      title: "What's New in v2.5.0",
      date: '2026-10-27',
      highlights: [],
      sections: [],
    }
    whatsNewState.latestNote = latestNote
    whatsNewState.pendingNote = { html: '<h1>Pending Release</h1><p>Unreleased change.</p>' }
    whatsNewState.notes = [latestNote]
    whatsNewState.loadAllNotes.mockClear()
  })

  it('shows pending changes above the versioned release', async () => {
    const wrapper = mount(WhatsNewView, { global: { plugins: [vuetify] } })
    await flushPromises()

    const pending = wrapper.find('.pending-release-card')
    const latest = wrapper.find('.latest-note-card')

    expect(pending.exists()).toBe(true)
    expect(latest.exists()).toBe(true)
    expect(pending.element.compareDocumentPosition(latest.element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(pending.text()).toContain('Unreleased change.')

    wrapper.unmount()
  })

  it('shows pending changes when no versioned notes are available', async () => {
    whatsNewState.latestNote = null
    whatsNewState.notes = []

    const wrapper = mount(WhatsNewView, { global: { plugins: [vuetify] } })
    await flushPromises()

    expect(wrapper.find('.pending-release-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('Unreleased change.')
    expect(wrapper.text()).not.toContain('No release notes available')

    wrapper.unmount()
  })
})
