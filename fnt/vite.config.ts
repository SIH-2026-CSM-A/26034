import basicSsl from '@vitejs/plugin-basic-ssl'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
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
        name: 'PCCS — Packaged Commodity Compliance System',
        short_name: 'PCCS',
        description: 'Compliance decision-support for packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011.',
        theme_color: '#DCDFDB',
        background_color: '#DCDFDB',
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
