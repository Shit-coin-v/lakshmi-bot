import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// Конфигурация Vite для Lakshmi Photo Studio.
// PWA подключается через vite-plugin-pwa с автоматическим обновлением SW.
// Runtime caching: каталог через NetworkFirst (свежие данные приоритетнее),
// дерево категорий через StaleWhileRevalidate, медиа товаров через CacheFirst.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icons/icon-192.png', 'icons/icon-512.png'],
      manifest: {
        name: 'Lakshmi Photo Studio',
        short_name: 'Lakshmi Photo',
        description: 'Массовая съёмка товаров для каталога Lakshmi Market',
        theme_color: '#4CAF50',
        background_color: '#F9F9F9',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/products/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-products',
              networkTimeoutSeconds: 5,
              expiration: { maxAgeSeconds: 60 * 60 * 12 },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/catalog/'),
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'api-catalog' },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/media/products/'),
            handler: 'CacheFirst',
            options: {
              cacheName: 'product-images',
              expiration: { maxAgeSeconds: 60 * 60 * 24 * 7 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    host: true,
  },
});
