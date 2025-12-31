/**
 * Theme management composable with localStorage persistence
 */
import { ref, computed, watch } from 'vue'
import { useTheme as useVuetifyTheme } from 'vuetify'

export interface ThemePreset {
  name: string
  displayName: string
  description: string
  isDark: boolean
  icon: string
}

export interface CustomThemeColors {
  primary?: string
  secondary?: string
  accent?: string
  error?: string
  info?: string
  success?: string
  warning?: string
}

const STORAGE_KEY_THEME = 'shape-shifter-theme'
const STORAGE_KEY_CUSTOM_COLORS = 'shape-shifter-custom-colors'

// Available theme presets
export const THEME_PRESETS: ThemePreset[] = [
  {
    name: 'light',
    displayName: 'Light',
    description: 'Clean and bright interface',
    isDark: false,
    icon: 'mdi-white-balance-sunny',
  },
  {
    name: 'dark',
    displayName: 'Dark',
    description: 'Easy on the eyes',
    isDark: true,
    icon: 'mdi-moon-waning-crescent',
  },
  {
    name: 'ocean',
    displayName: 'Ocean',
    description: 'Calming blue tones',
    isDark: false,
    icon: 'mdi-waves',
  },
  {
    name: 'forest',
    displayName: 'Forest',
    description: 'Natural green palette',
    isDark: false,
    icon: 'mdi-tree',
  },
  {
    name: 'sunset',
    displayName: 'Sunset',
    description: 'Warm orange hues',
    isDark: false,
    icon: 'mdi-weather-sunset',
  },
]

export function useTheme() {
  const vuetifyTheme = useVuetifyTheme()

  // Load saved theme from localStorage
  const savedTheme = localStorage.getItem(STORAGE_KEY_THEME)
  const savedCustomColors = localStorage.getItem(STORAGE_KEY_CUSTOM_COLORS)

  // Current theme name
  const currentThemeName = ref<string>(savedTheme || 'light')

  // Custom colors overlay
  const customColors = ref<CustomThemeColors>(savedCustomColors ? JSON.parse(savedCustomColors) : {})

  // Apply theme on load
  if (savedTheme) {
    vuetifyTheme.change(savedTheme)
  }

  // Apply custom colors if any
  if (savedCustomColors) {
    const colors = JSON.parse(savedCustomColors)
    Object.assign(vuetifyTheme.current.value.colors, colors)
  }

  // Computed properties
  const currentPreset = computed(() => {
    return THEME_PRESETS.find((p) => p.name === currentThemeName.value) || THEME_PRESETS[0]
  })

  const isDark = computed(() => {
    return currentPreset.value.isDark
  })

  const hasCustomColors = computed(() => {
    return Object.keys(customColors.value).length > 0
  })

  // Methods
  function setTheme(themeName: string) {
    currentThemeName.value = themeName
    vuetifyTheme.change(themeName)
    localStorage.setItem(STORAGE_KEY_THEME, themeName)

    // Reapply custom colors to new theme
    if (hasCustomColors.value) {
      applyCustomColors(customColors.value)
    }
  }

  function toggleDarkMode() {
    const newTheme = isDark.value ? 'light' : 'dark'
    setTheme(newTheme)
  }

  function applyCustomColors(colors: CustomThemeColors) {
    customColors.value = { ...colors }

    // Apply to current theme
    Object.entries(colors).forEach(([key, value]) => {
      if (value) {
        vuetifyTheme.current.value.colors[key] = value
      }
    })

    // Save to localStorage
    localStorage.setItem(STORAGE_KEY_CUSTOM_COLORS, JSON.stringify(colors))
  }

  function resetCustomColors() {
    customColors.value = {}
    localStorage.removeItem(STORAGE_KEY_CUSTOM_COLORS)

    // Reset to theme defaults by reloading the theme
    const currentTheme = currentThemeName.value
    vuetifyTheme.change('light') // temp switch
    setTimeout(() => {
      vuetifyTheme.change(currentTheme)
    }, 10)
  }

  function resetToDefault() {
    setTheme('light')
    resetCustomColors()
  }

  function exportThemeConfig() {
    return {
      theme: currentThemeName.value,
      customColors: customColors.value,
    }
  }

  function importThemeConfig(config: { theme: string; customColors: CustomThemeColors }) {
    if (config.theme) {
      setTheme(config.theme)
    }
    if (config.customColors) {
      applyCustomColors(config.customColors)
    }
  }

  // Watch for manual theme changes (e.g., from devtools)
  watch(
    () => vuetifyTheme.global.name.value,
    (newTheme) => {
      if (newTheme !== currentThemeName.value) {
        currentThemeName.value = newTheme
        localStorage.setItem(STORAGE_KEY_THEME, newTheme)
      }
    }
  )

  return {
    // State
    currentThemeName,
    customColors,
    currentPreset,
    isDark,
    hasCustomColors,
    presets: THEME_PRESETS,

    // Methods
    setTheme,
    toggleDarkMode,
    applyCustomColors,
    resetCustomColors,
    resetToDefault,
    exportThemeConfig,
    importThemeConfig,

    // Vuetify theme instance
    vuetifyTheme,
  }
}
