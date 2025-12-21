/**
 * Application settings composable with localStorage persistence
 */
import { ref, watch } from 'vue'
import { useDisplay } from 'vuetify'

export interface AppSettings {
  compactMode: boolean
  animationsEnabled: boolean
  railNavigation: boolean
}

const STORAGE_KEY = 'shape-shifter-settings'

// Default settings
const DEFAULT_SETTINGS: AppSettings = {
  compactMode: false,
  animationsEnabled: true,
  railNavigation: false,
}

// Load saved settings
function loadSettings(): AppSettings {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) }
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
  return { ...DEFAULT_SETTINGS }
}

// Save settings
function saveSettings(settings: AppSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch (error) {
    console.error('Failed to save settings:', error)
  }
}

// Shared state
const settings = ref<AppSettings>(loadSettings())

export function useSettings() {
  const display = useDisplay()

  // Watch for changes and persist
  watch(
    settings,
    (newSettings) => {
      saveSettings(newSettings)
      applySettings(newSettings)
    },
    { deep: true }
  )

  // Apply settings to the DOM/styles
  function applySettings(s: AppSettings) {
    const root = document.documentElement

    // Apply compact mode
    if (s.compactMode) {
      root.classList.add('compact-mode')
      root.style.setProperty('--v-spacing-base', '12px')
      root.style.setProperty('--v-card-padding', '12px')
    } else {
      root.classList.remove('compact-mode')
      root.style.setProperty('--v-spacing-base', '16px')
      root.style.setProperty('--v-card-padding', '16px')
    }

    // Apply animations
    if (!s.animationsEnabled) {
      root.classList.add('no-animations')
    } else {
      root.classList.remove('no-animations')
    }
  }

  // Apply settings on initialization
  applySettings(settings.value)

  // Computed getters for individual settings
  const compactMode = {
    get value() {
      return settings.value.compactMode
    },
    set value(val: boolean) {
      settings.value.compactMode = val
    },
  }

  const animationsEnabled = {
    get value() {
      return settings.value.animationsEnabled
    },
    set value(val: boolean) {
      settings.value.animationsEnabled = val
    },
  }

  const railNavigation = {
    get value() {
      return settings.value.railNavigation
    },
    set value(val: boolean) {
      settings.value.railNavigation = val
    },
  }

  // Get density based on compact mode
  const density = {
    get value(): 'default' | 'comfortable' | 'compact' {
      return settings.value.compactMode ? 'compact' : 'comfortable'
    },
  }

  // Methods
  function resetToDefaults() {
    settings.value = { ...DEFAULT_SETTINGS }
  }

  function exportSettings(): string {
    return JSON.stringify(settings.value, null, 2)
  }

  function importSettings(jsonString: string): boolean {
    try {
      const imported = JSON.parse(jsonString)
      settings.value = { ...DEFAULT_SETTINGS, ...imported }
      return true
    } catch (error) {
      console.error('Failed to import settings:', error)
      return false
    }
  }

  return {
    // Settings
    settings,
    compactMode,
    animationsEnabled,
    railNavigation,
    density,

    // Methods
    resetToDefaults,
    exportSettings,
    importSettings,

    // Display info
    isMobile: display.mobile,
    isTablet: display.smAndDown,
  }
}
