/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, API calls are proxied to the FastAPI server so the browser sees a single origin.
const API = 'http://127.0.0.1:8000'
const apiPaths = ['/users', '/tools', '/ask', '/approvals', '/audit', '/info']

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: Object.fromEntries(apiPaths.map((p) => [p, API])) },
  test: { environment: 'jsdom', setupFiles: './src/test-setup.ts', globals: true },
})
