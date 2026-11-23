import { describe, expect, it } from 'vitest'
import vuetify from '../vuetify'

/**
 * Semantic theme colours are painted as icon, text, and chip colours, so each
 * one must stay readable on its own theme's surface. A colour copied from the
 * light theme into the dark theme silently breaks this: the light secondary
 * #424242 reaches only about 1.9:1 on a near-black surface and makes secondary
 * buttons look disabled.
 *
 * WCAG treats 3:1 as the minimum for non-text interface components and large
 * text, which is the relevant bar for icon buttons and chips.
 */
const MINIMUM_CONTRAST = 3

/** Colours that are used directly as foreground colours by components. */
const FOREGROUND_KEYS = ['primary', 'secondary', 'info', 'error'] as const

interface ThemeColors {
  background?: string
  surface?: string
  primary?: string
  secondary?: string
  info?: string
  error?: string
}

/** Convert one sRGB channel in the 0-1 range to linear light. */
function linearize(channel: number): number {
  return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
}

/** WCAG relative luminance of a `#rrggbb` colour. */
function relativeLuminance(hex: string): number {
  const match = /^#([0-9a-f]{6})$/i.exec(hex.trim())
  if (!match) throw new Error(`Expected a #rrggbb colour, received "${hex}"`)
  const value = Number.parseInt(match[1] as string, 16)
  const red = linearize(((value >> 16) & 0xff) / 255)
  const green = linearize(((value >> 8) & 0xff) / 255)
  const blue = linearize((value & 0xff) / 255)
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue
}

/** WCAG contrast ratio between two `#rrggbb` colours. */
function contrastRatio(foreground: string, background: string): number {
  const first = relativeLuminance(foreground)
  const second = relativeLuminance(background)
  const lighter = Math.max(first, second)
  const darker = Math.min(first, second)
  return (lighter + 0.05) / (darker + 0.05)
}

interface ThemeSnapshot {
  name: string
  surface: string
  colors: ThemeColors
}

/** Read every registered theme with the surface its colours are painted on. */
function themeSnapshots(): ThemeSnapshot[] {
  const themes = vuetify.theme.themes.value as Record<string, { dark: boolean; colors: ThemeColors }>
  return Object.entries(themes).map(([name, theme]) => ({
    name,
    // Vuetify defaults to #121212 page and #212121 elevated surface in dark mode.
    surface: theme.colors.surface ?? theme.colors.background ?? (theme.dark ? '#121212' : '#FFFFFF'),
    colors: theme.colors,
  }))
}

describe('Vuetify theme contrast', () => {
  const snapshots = themeSnapshots()

  it('registers the expected themes', () => {
    expect(snapshots.map((theme) => theme.name).sort()).toEqual(['dark', 'forest', 'light', 'ocean', 'sunset'])
  })

  it.each(FOREGROUND_KEYS)('keeps %s readable on every theme surface', (key) => {
    const failures = snapshots.flatMap((theme) => {
      const color = theme.colors[key]
      if (!color) return []
      const ratio = contrastRatio(color, theme.surface)
      return ratio < MINIMUM_CONTRAST ? [`${theme.name}: ${color} on ${theme.surface} is ${ratio.toFixed(2)}:1`] : []
    })

    expect(failures).toEqual([])
  })

  it('does not reuse the light secondary colour in dark mode', () => {
    const byName = Object.fromEntries(snapshots.map((theme) => [theme.name, theme.colors]))
    expect(byName.dark?.secondary).not.toBe(byName.light?.secondary)
  })
})
