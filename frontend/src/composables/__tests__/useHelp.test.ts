import { describe, expect, it } from 'vitest'

import { renderHelpMarkdown, resolveHelpHref } from '../useHelp'

describe('useHelp markdown rendering', () => {
  it('does not auto-linkify plain filename text', () => {
    const html = renderHelpMarkdown('Generates CHANGELOG.md', 'DEVELOPER_GUIDE')

    expect(html).toContain('CHANGELOG.md')
    expect(html).not.toContain('href="https://changelog.md/')
    expect(html).not.toContain('<a href=')
  })

  it('rewrites relative top-level docs links to internal help routes', () => {
    expect(resolveHelpHref('CONFIGURATION_GUIDE.md', 'USER_GUIDE')).toBe(
      '/help?doc=CONFIGURATION_GUIDE'
    )
  })

  it('rewrites nested docs links to internal help routes', () => {
    expect(resolveHelpHref('other/USER_GUIDE_APPENDIX.md', 'USER_GUIDE')).toBe(
      '/help?doc=other%2FUSER_GUIDE_APPENDIX'
    )
  })

  it('rewrites parent-relative root doc links correctly', () => {
    expect(resolveHelpHref('../TODO.md', 'DEVELOPER_GUIDE')).toBe(
      'https://github.com/humlab-sead/sead_shape_shifter/blob/main/TODO.md'
    )
  })

  it('keeps in-document anchors unchanged', () => {
    expect(resolveHelpHref('#10-contributing', 'DEVELOPER_GUIDE')).toBe('#10-contributing')
  })

  it('adds heading ids so quick links can scroll to sections', () => {
    const html = renderHelpMarkdown('## 2. Getting Started', 'USER_GUIDE')

    expect(html).toContain('<h2 id="2-getting-started">2. Getting Started</h2>')
  })
})