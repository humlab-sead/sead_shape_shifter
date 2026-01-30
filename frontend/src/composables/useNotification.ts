/**
 * Simple notification composable using Vuetify's snackbar
 * Provides toast-like functionality for user feedback
 */

import { ref } from 'vue'

interface SnackbarState {
  show: boolean
  message: string
  color: string
  timeout: number
}

const snackbar = ref<SnackbarState>({
  show: false,
  message: '',
  color: 'success',
  timeout: 3000,
})

export function useNotification() {
  const showSnackbar = (message: string, color: string = 'success', timeout: number = 3000) => {
    snackbar.value = {
      show: true,
      message,
      color,
      timeout,
    }
  }

  const success = (message: string) => {
    showSnackbar(message, 'success')
  }

  const error = (message: string) => {
    showSnackbar(message, 'error', 5000)
  }

  const warning = (message: string) => {
    showSnackbar(message, 'warning', 4000)
  }

  const info = (message: string) => {
    showSnackbar(message, 'info')
  }

  return {
    snackbar,
    success,
    error,
    warning,
    info,
  }
}
