import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      injectRegister: false,
      manifest: {
        name: 'PCCS — Packaged Commodity Compliance System',
        short_name: 'PCCS',
        description: 'Compliance decision-support for packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011.',
        theme_color: '#0F172A',
        background_color: '#F8FAFC',
        display: 'standalone',
        icons: [],
      },
    }),
  ],
})
