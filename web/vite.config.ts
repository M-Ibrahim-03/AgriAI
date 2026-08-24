import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: [
        'risk.geojson',
        'risk_d3.geojson',
        'risk_d7.geojson',
        'audio/index.json',
        'audio/*.mp3',
      ],
      manifest: {
        name: 'PRAHARI',
        short_name: 'PRAHARI',
        description: 'Crop disease early-warning system',
        theme_color: '#111827',
        background_color: '#111827',
        display: 'standalone',
        icons: [
          {
            src: 'icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /\/risk.*\.geojson$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'risk-geojson',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24, // 24h
              },
            },
          },
          {
            urlPattern: /\/audio\/.*\.mp3$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'audio-clips',
              expiration: {
                maxEntries: 30,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
              },
            },
          },
          {
            urlPattern: /\/audio\/index\.json$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'audio-index',
              expiration: {
                maxEntries: 1,
                maxAgeSeconds: 60 * 60 * 24,
              },
            },
          },
        ],
      },
    }),
  ],
})
