import { beforeEach, describe, expect, it, vi } from 'vitest'

const whatsNewApiMocks = vi.hoisted(() => ({
  getManifest: vi.fn(),
  getNote: vi.fn(),
  getPendingContent: vi.fn(),
}))

vi.mock('@/api/whats-new', () => ({
  whatsNewApi: whatsNewApiMocks,
}))

import { useWhatsNew } from '../useWhatsNew'

describe('useWhatsNew', () => {
  beforeEach(() => {
    whatsNewApiMocks.getManifest.mockReset().mockResolvedValue({
      latest_version: '2.5.0',
      items: [
        { version: '2.5.0', title: "What's New in v2.5.0", date: '2026-10-27', path: '/docs/whats-new/v2.5.0.md' },
      ],
      pending_available: true,
    })
    whatsNewApiMocks.getNote.mockReset().mockResolvedValue("# What's New in v2.5.0\n\n## Changes\n\n- Shipped change.")
    whatsNewApiMocks.getPendingContent
      .mockReset()
      .mockResolvedValue('# Pending Release\n\n- Pending change.\n\n<script>not executable</script>')
  })

  it('loads and safely renders pending notes when available', async () => {
    const state = useWhatsNew()

    await state.loadAllNotes()

    expect(state.pendingNote.value?.html).toContain('Pending change.')
    expect(state.pendingNote.value?.html).toContain('&lt;script&gt;not executable&lt;/script&gt;')
    expect(whatsNewApiMocks.getPendingContent).toHaveBeenCalledOnce()
  })
})
