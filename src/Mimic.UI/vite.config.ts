import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    host: true,
    // Configurable so the dev server can move aside when 5173 is taken.
    port: Number(process.env.PORT ?? process.env.VITE_PORT ?? 5173),
    // Polling is needed for file watching to work across a Docker bind mount.
    watch: { usePolling: true },

    // Proxy the API so the browser only ever talks to one origin. This keeps
    // CORS out of development entirely, and mirrors the production setup
    // where the UI and API are served together.
    proxy: {
      '^/api/': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:5000',
        changeOrigin: true,
      },
      // Anchored regex, not a bare prefix. A plain '/mock' rule would also
      // swallow the UI's own '/mocks' route and proxy it to the API.
      '^/mock/': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },

  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        // Split the editor out of the main bundle: it is large and only
        // needed once a request body is opened.
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
          editor: [
            'codemirror',
            '@codemirror/lang-json',
            '@codemirror/lang-xml',
            '@codemirror/view',
            '@codemirror/state',
          ],
        },
      },
    },
  },
})
