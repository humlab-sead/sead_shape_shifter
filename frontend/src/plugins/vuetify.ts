import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FB8C00',
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: '#2196F3',
          secondary: '#424242',
          accent: '#FF4081',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FB8C00',
        },
      },
      ocean: {
        dark: false,
        colors: {
          primary: '#006994',
          secondary: '#004D6D',
          accent: '#00BCD4',
          error: '#D32F2F',
          info: '#0288D1',
          success: '#00897B',
          warning: '#F57C00',
          background: '#E0F7FA',
          surface: '#FFFFFF',
        },
      },
      forest: {
        dark: false,
        colors: {
          primary: '#2E7D32',
          secondary: '#558B2F',
          accent: '#66BB6A',
          error: '#C62828',
          info: '#1976D2',
          success: '#388E3C',
          warning: '#F57F17',
          background: '#F1F8E9',
          surface: '#FFFFFF',
        },
      },
      sunset: {
        dark: false,
        colors: {
          primary: '#D84315',
          secondary: '#BF360C',
          accent: '#FF6F00',
          error: '#C62828',
          info: '#1976D2',
          success: '#388E3C',
          warning: '#F9A825',
          background: '#FFF3E0',
          surface: '#FFFFFF',
        },
      },
    },
  },
  defaults: {
    VBtn: {
      variant: 'flat',
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable',
    },
    VSelect: {
      variant: 'outlined',
      density: 'comfortable',
    },
  },
})
