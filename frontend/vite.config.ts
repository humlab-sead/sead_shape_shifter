import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import Components from 'unplugin-vue-components/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vuetify({
      autoImport: true,
      styles: {
        configFile: 'src/styles/settings.scss',
      },
    }),
    Components({
      dirs: ['src/components'],
      dts: 'src/components.d.ts',
    }),
  ],
  css: {
    preprocessorOptions: {
      scss: {
        silenceDeprecations: ['if-function', 'legacy-js-api'],
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: true, // Listen on all addresses for remote access
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8012',
        changeOrigin: true,
        secure: false, // Allow self-signed certificates in dev
        ws: true, // WebSocket support
      },
    },
  },
})
