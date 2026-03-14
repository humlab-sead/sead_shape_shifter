import { describe, expect, it } from 'vitest'

import { getCytoscapeStyles } from '@/config/cytoscapeStyles'

describe('cytoscape task styles', () => {
  it('contains selectors for task status classes', () => {
    const styles = getCytoscapeStyles(false)
    const selectors = new Set(styles.map((s) => s.selector))

    expect(selectors.has('node.task-done')).toBe(true)
    expect(selectors.has('node.task-ignored')).toBe(true)
    expect(selectors.has('node.task-blocked')).toBe(true)
    expect(selectors.has('node.task-critical')).toBe(true)
    expect(selectors.has('node.task-ready')).toBe(true)
    expect(selectors.has('node.task-ongoing')).toBe(true)
    expect(selectors.has('node.task-flagged')).toBe(true)
  })
})
