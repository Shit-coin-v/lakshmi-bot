import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// Конфиг vitest вынесен отдельно, чтобы не примешивать test-окружение
// к продакшен-сборке Vite (vite.config.js остаётся чистым под build/dev).
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.js'],
    include: ['tests/**/*.test.{js,jsx}'],
    css: false,
  },
});
