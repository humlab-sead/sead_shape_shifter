import { describe, expect, it } from 'vitest'
import { HELP_TOPICS, reconciliationWorkspaceTopic, resolveHelpTopic, type HelpContext } from '../helpRegistry'

function context(overrides: Partial<HelpContext> = {}): HelpContext {
  return {
    routeName: 'home',
    tab: null,
    workspaceActive: false,
    workspaceMode: 'search',
    ...overrides,
  }
}

describe('resolveHelpTopic', () => {
  it('returns the topic for a standalone route', () => {
    expect(resolveHelpTopic(context({ routeName: 'schema-explorer' }))?.title).toBe('Schema Explorer')
  })

  it('returns the topic for a project-detail tab', () => {
    const topic = resolveHelpTopic(context({ routeName: 'project-detail', tab: 'validation' }))
    expect(topic?.title).toBe('Validation')
  })

  it('returns the review table help for the reconciliation tab when no workspace is open', () => {
    const topic = resolveHelpTopic(context({ routeName: 'project-detail', tab: 'reconciliation' }))
    expect(topic?.title).toBe('Reconcile & Review')
    expect(topic?.rowActions?.length).toBeGreaterThan(0)
  })

  it('prefers the workspace topic while the workspace is open', () => {
    const topic = resolveHelpTopic(
      context({ routeName: 'project-detail', tab: 'reconciliation', workspaceActive: true })
    )
    expect(topic?.title).toBe('Review workspace')
    expect(topic?.rowActions).toBeUndefined()
  })

  it('returns the workspace topic for the current mode', () => {
    const browse = resolveHelpTopic(
      context({ routeName: 'project-detail', tab: 'reconciliation', workspaceActive: true, workspaceMode: 'browse' })
    )
    expect(browse?.groups?.[0]?.title).toBe('Browse')
    expect(browse?.groups?.[0]?.tips.join(' ')).toContain('complete target list')
  })

  it('returns null for an unknown route or tab', () => {
    expect(resolveHelpTopic(context({ routeName: 'unknown-route' }))).toBeNull()
    expect(resolveHelpTopic(context({ routeName: 'project-detail', tab: 'unknown-tab' }))).toBeNull()
  })

  it('ignores the project-detail tab when no tab is active', () => {
    expect(resolveHelpTopic(context({ routeName: 'project-detail', tab: null }))).toBeNull()
  })
})

describe('reconciliationWorkspaceTopic', () => {
  it('keeps the saving rules and shortcuts in every mode', () => {
    const search = reconciliationWorkspaceTopic('search')
    const browse = reconciliationWorkspaceTopic('browse')

    expect(search.groups?.[1]?.title).toBe('Saving and export')
    expect(browse.groups?.[1]?.title).toBe('Saving and export')
    expect(search.shortcuts).toEqual(browse.shortcuts)
    expect(search.shortcuts?.length).toBeGreaterThan(0)
  })
})

describe('HELP_TOPICS', () => {
  it('gives every topic a title', () => {
    for (const [key, topic] of Object.entries(HELP_TOPICS)) {
      expect(topic.title, `topic ${key} needs a title`).toBeTruthy()
    }
  })
})
