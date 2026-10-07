/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,json}'],
        // Phase 17 low-bandwidth: serve cached GET responses so a returning
        // family on a poor connection still sees their last outcomes/roadmap.
        runtimeCaching: [
          {
            urlPattern: /\/outcomes(\?.*)?$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'api-outcomes',
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 7 },
            },
          },
          {
            urlPattern: /\/roadmap(\?.*)?$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'api-roadmap',
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 7 },
            },
          },
          {
            urlPattern: /\/quick-replies\.json$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'quick-replies',
              expiration: { maxEntries: 5, maxAgeSeconds: 60 * 60 * 24 * 30 },
            },
          },
        ],
      },
      manifest: {
        name: 'KaushalPath',
        short_name: 'KaushalPath',
        description: 'Vocational Career Counselling',
        theme_color: '#1D4ED8',
        background_color: '#F3F4F6',
        display: 'standalone',
        icons: [
          {
            src: 'favicon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any'
          },
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'pwa-maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable'
          }
        ]
      }
    })
  ],
  server: { port: 5173 },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    exclude: ['**/node_modules/**', '**/e2e/**'],
  },
});
