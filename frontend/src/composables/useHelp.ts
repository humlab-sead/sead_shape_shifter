import { ref } from 'vue'
import MarkdownIt from 'markdown-it'

const REPO_BLOB_BASE = 'https://github.com/humlab-sead/sead_shape_shifter/blob/main/'
const ABSOLUTE_LINK_PATTERN = /^(https?:|mailto:|tel:)/i
const HELP_ROUTE_BASE = '/help'

function ensureMarkdownPath(docPath: string): string {
  return docPath.endsWith('.md') ? docPath : `${docPath}.md`
}

function slugifyHeading(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[!"#$%&'()*+,./:;<=>?@[\\\]^`{|}~]/g, '')
    .replace(/\s/g, '-')
    .replace(/^-+|-+$/g, '')
}

function isInternalHelpHref(href: string): boolean {
  return href === HELP_ROUTE_BASE || href.startsWith(`${HELP_ROUTE_BASE}?`) || href.startsWith(`${HELP_ROUTE_BASE}#`)
}

export function resolveHelpHref(href: string, docPath: string): string {
  if (!href || href.startsWith('#') || ABSOLUTE_LINK_PATTERN.test(href) || isInternalHelpHref(href)) {
    return href
  }

  if (href.startsWith('/')) {
    return href
  }

  const resolved = new URL(href, `https://repo.local/docs/${ensureMarkdownPath(docPath)}`)
  const resolvedPath = resolved.pathname.replace(/^\//, '')

  if (resolvedPath.startsWith('docs/') && resolvedPath.endsWith('.md')) {
    const internalDocPath = resolvedPath.slice('docs/'.length, -'.md'.length)
    return `${HELP_ROUTE_BASE}?doc=${encodeURIComponent(internalDocPath)}${resolved.hash}`
  }

  if (resolvedPath.startsWith('docs/')) {
    return `/${resolvedPath}${resolved.hash}`
  }

  return `${REPO_BLOB_BASE}${resolvedPath}${resolved.hash}`
}

export function renderHelpMarkdown(markdown: string, docPath: string): string {
  const md = new MarkdownIt({
    html: true,
    linkify: false,
    typographer: true,
    breaks: false,
  })

  const defaultHeadingRenderer = md.renderer.rules.heading_open || ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

  const defaultLinkRenderer = md.renderer.rules.link_open || ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

  md.renderer.rules.heading_open = (tokens, idx, options, env, self) => {
    const token = tokens[idx]
    const inlineToken = tokens[idx + 1]

    if (!token) {
      return ''
    }

    if (inlineToken?.type === 'inline' && inlineToken.content) {
      token.attrSet('id', slugifyHeading(inlineToken.content))
    }

    return defaultHeadingRenderer(tokens, idx, options, env, self)
  }

  md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    const token = tokens[idx]

    if (!token) {
      return ''
    }

    const hrefIndex = token.attrIndex('href')

    if (hrefIndex >= 0) {
      const normalizedHref = resolveHelpHref(token.attrs?.[hrefIndex]?.[1] ?? '', docPath)
      token.attrSet('href', normalizedHref)

      if (ABSOLUTE_LINK_PATTERN.test(normalizedHref)) {
        token.attrSet('target', '_blank')
        token.attrSet('rel', 'noopener noreferrer')
      }
    }

    return defaultLinkRenderer(tokens, idx, options, env, self)
  }

  return md.render(markdown)
}

/**
 * Composable for loading and rendering help documentation
 */
export function useHelp() {
  const renderedContent = ref('')
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Load and render a markdown help document
   * @param docPath - Path of the document relative to docs/ (without .md extension)
   */
  async function loadHelp(docPath: string = 'USER_GUIDE') {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`/api/v1/help-docs/${encodeURI(docPath)}`)
      
      if (!response.ok) {
        throw new Error(`Failed to load ${docPath}.md: ${response.statusText}`)
      }

      const markdown = await response.text()
      if (markdown.startsWith('<!DOCTYPE html>')) {
        throw new Error(`Received HTML instead of markdown for ${docPath}.md`)
      }

      renderedContent.value = renderHelpMarkdown(markdown, docPath)
    } catch (err: any) {
      error.value = err.message || 'Failed to load help documentation'
      console.error('Error loading help documentation:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Load and render a specific section of help
   * @param docPath - Document path
   * @param sectionId - Section heading ID to scroll to
   */
  async function loadHelpSection(docPath: string, sectionId: string) {
    await loadHelp(docPath)
    
    // Wait for next tick to ensure DOM is updated
    setTimeout(() => {
      const element = document.getElementById(sectionId)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }, 100)
  }

  /**
   * Clear loaded content and reset state
   */
  function clearHelp() {
    renderedContent.value = ''
    error.value = null
  }

  return {
    renderedContent,
    loading,
    error,
    loadHelp,
    loadHelpSection,
    clearHelp,
  }
}

/**
 * Get help tooltip text for a specific feature
 * @param feature - Feature name
 * @returns Tooltip text
 */
export function getHelpTooltip(feature: string): string {
  const tooltips: Record<string, string> = {
    validate: 'Run validation checks on the entire project',
    'validate-entity': 'Run validation checks on the selected entity only',
    execute: 'Execute the full workflow and export data',
    'auto-fix': 'Automatically apply suggested fixes to validation errors',
    'test-run': 'Preview transformation results for selected entities',
    save: 'Save changes to the project configuration',
    backups: 'View and restore previous versions of this project',
  }

  return tooltips[feature] || 'Click for more information'
}

/**
 * Get link to specific help section
 * @param section - Section ID from USER_GUIDE.md
 * @returns URL path to help view with section
 */
export function getHelpLink(section: string): string {
  return `/help#${section}`
}
