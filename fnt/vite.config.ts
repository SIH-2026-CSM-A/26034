import basicSsl from '@vitejs/plugin-basic-ssl'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        // The two libraries every surface shares, cached once across deploys; the
        // surfaces themselves split at the route trees in App.tsx.
        manualChunks(id: string) {
          if (id.includes('node_modules/framer-motion')) return 'motion'
          if (/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler)\//.test(id)) return 'react'
          return undefined
        },
      },
    },
  },
  server: {
    host: true,
    // The backend sends no CORS headers, and the dev server is HTTPS on a
    // different port, so a direct browser call to :8000 is refused before it
    // is sent. Proxying keeps every API call same-origin. Point
    // VITE_API_BASE_URL at /api to use it — see .env.example.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  plugins: [
    react(),
    basicSsl(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      // The default glob omits woff2, which would leave the self-hosted
      // faces out of the precache — the one thing they exist to survive.
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
      },
      manifest: {
        name: 'Maapdand — packaged commodity compliance for Legal Metrology',
        short_name: 'Maapdand',
        description: 'Compliance decision-support for packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011.',
        theme_color: '#F3F4F1',
        background_color: '#F3F4F1',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: '/favicon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any',
          },
        ],
      },
    }),
  ],
})
