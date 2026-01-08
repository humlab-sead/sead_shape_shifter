import { ref } from 'vue'
import MarkdownIt from 'markdown-it'

// Initialize markdown-it with enhanced configuration
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: false,
})

/**
 * Composable for loading and rendering help documentation
 */
export function useHelp() {
  const renderedContent = ref('')
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Load and render a markdown help document
   * @param docName - Name of the document (without .md extension)
   */
  async function loadHelp(docName: string = 'USER_GUIDE') {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`/docs/${docName}.md`)
      
      if (!response.ok) {
        throw new Error(`Failed to load ${docName}.md: ${response.statusText}`)
      }

      const markdown = await response.text()
      renderedContent.value = md.render(markdown)
    } catch (err: any) {
      error.value = err.message || 'Failed to load help documentation'
      console.error('Error loading help documentation:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Load and render a specific section of help
   * @param docName - Document name
   * @param sectionId - Section heading ID to scroll to
   */
  async function loadHelpSection(docName: string, sectionId: string) {
    await loadHelp(docName)
    
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
