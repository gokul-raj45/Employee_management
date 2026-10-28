import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  test: {
    environment: 'jsdom',
    environmentOptions: { jsdom: { url: 'http://localhost:5173' } }, // real origin so the backend's CORS rules are exercised
    setupFiles: './src/test-setup.js',
    globals: true,
    testTimeout: 30000,
  },
})
